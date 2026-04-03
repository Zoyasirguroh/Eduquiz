import os
import json
import uuid
from flask import Flask, render_template, request, jsonify, send_file, session
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

# In-memory store keyed by session id
_results_store: dict[str, list] = {}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    """Main generation endpoint — accepts PDF upload or raw text."""
    subject = request.form.get("subject", "General").strip()
    grade = request.form.get("grade", "Undergraduate").strip()
    num_questions = int(request.form.get("num_questions", 5))
    num_questions = max(1, min(num_questions, 20))

    # --- Acquire source text ---
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
        return jsonify({"error": "Text is too short to generate meaningful questions. Please provide more content."}), 400

    try:
        questions = generate_mcqs(text, subject, grade, num_questions)
    except Exception as exc:
        return jsonify({"error": f"Generation failed: {str(exc)}"}), 500

    # Store results for export
    result_id = str(uuid.uuid4())
    _results_store[result_id] = questions

    return jsonify({"result_id": result_id, "questions": questions})


@app.route("/export/docx/<result_id>")
def export_as_docx(result_id: str):
    questions = _results_store.get(result_id)
    if not questions:
        return "Result not found or expired.", 404
    path = export_docx(questions, result_id)
    return send_file(path, as_attachment=True, download_name="EduQuiz_Questions.docx",
                     mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@app.route("/export/xml/<result_id>")
def export_as_xml(result_id: str):
    questions = _results_store.get(result_id)
    if not questions:
        return "Result not found or expired.", 404
    path = export_moodle_xml(questions, result_id)
    return send_file(path, as_attachment=True, download_name="EduQuiz_Moodle.xml",
                     mimetype="application/xml")


if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
