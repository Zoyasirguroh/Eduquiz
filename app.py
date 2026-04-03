import os
import json
import uuid
import queue
import threading
from flask import Flask, render_template, request, jsonify, send_file, Response, stream_with_context
from werkzeug.utils import secure_filename

from modules.pdf_parser import extract_text_from_pdf
from modules.mcq_generator import generate_mcqs
from modules.exporter import export_docx, export_moodle_xml

app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXTENSIONS = {"pdf"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

# job_id -> {"questions": [...], "error": str, "done": bool, "queue": Queue}
_jobs: dict[str, dict] = {}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    """Accepts input, starts background generation, returns job_id immediately."""
    subject = request.form.get("subject", "General").strip()
    grade = request.form.get("grade", "Undergraduate").strip()
    num_questions = int(request.form.get("num_questions", 5))
    num_questions = max(1, min(num_questions, 20))
    run_critique = request.form.get("run_critique") == "1"

    text = ""
    file = request.files.get("pdf_file")
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        try:
            text = extract_text_from_pdf(filepath)
        finally:
            os.remove(filepath)
    else:
        text = request.form.get("topic_text", "").strip()

    if not text:
        return jsonify({"error": "Please provide a PDF file or paste topic text."}), 400
    if len(text) < 100:
        return jsonify({"error": "Text is too short. Please provide more content."}), 400

    job_id = str(uuid.uuid4())
    q = queue.Queue()
    _jobs[job_id] = {"questions": None, "error": None, "done": False, "queue": q}

    def run():
        try:
            q.put(("progress", "Chunking and preparing content…"))
            questions = generate_mcqs(
                text, subject, grade, num_questions,
                progress_cb=lambda msg: q.put(("progress", msg)),
                run_critique=run_critique,
            )
            _jobs[job_id]["questions"] = questions
            q.put(("done", questions))
        except Exception as e:
            _jobs[job_id]["error"] = str(e)
            q.put(("error", str(e)))
        finally:
            _jobs[job_id]["done"] = True

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/progress/<job_id>")
def progress(job_id: str):
    """SSE endpoint — streams progress messages then final result."""
    job = _jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found."}), 404

    def event_stream():
        q = job["queue"]
        while True:
            try:
                kind, payload = q.get(timeout=120)
            except queue.Empty:
                yield "event: error\ndata: {\"error\": \"Timed out waiting for LLM.\"}\n\n"
                break

            if kind == "progress":
                yield f"event: progress\ndata: {json.dumps({'message': payload})}\n\n"
            elif kind == "done":
                yield f"event: done\ndata: {json.dumps({'questions': payload})}\n\n"
                break
            elif kind == "error":
                yield f"event: error\ndata: {json.dumps({'error': payload})}\n\n"
                break

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.route("/result/<job_id>")
def get_result(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found."}), 404
    if not job["done"]:
        return jsonify({"error": "Job still running."}), 202
    if job["error"]:
        return jsonify({"error": job["error"]}), 500
    return jsonify({"questions": job["questions"]})


@app.route("/export/docx/<job_id>")
def export_as_docx(job_id: str):
    job = _jobs.get(job_id)
    if not job or not job.get("questions"):
        return "Result not found or expired.", 404
    path = export_docx(job["questions"], job_id)
    return send_file(path, as_attachment=True, download_name="EduQuiz_Questions.docx",
                     mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@app.route("/export/xml/<job_id>")
def export_as_xml(job_id: str):
    job = _jobs.get(job_id)
    if not job or not job.get("questions"):
        return "Result not found or expired.", 404
    path = export_moodle_xml(job["questions"], job_id)
    return send_file(path, as_attachment=True, download_name="EduQuiz_Moodle.xml",
                     mimetype="application/xml")


@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large. Maximum allowed size is 16 MB."}), 413


if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
