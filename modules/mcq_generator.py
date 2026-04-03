"""MCQ generation pipeline with Bloom's Taxonomy alignment and self-critique."""

import json
import textwrap
from modules.llm_client import generate_raw, extract_json_block
from modules.critique_loop import critique_and_improve

BLOOM_LEVELS = {
    "Remember": "recall facts, definitions, and basic concepts",
    "Apply": "use knowledge to solve problems or interpret scenarios",
    "Analyse": "break down information, find relationships, and draw inferences",
}

MCQ_PROMPT = """You are an expert educational content creator specializing in Bloom's Taxonomy-aligned assessments.

Subject: {subject}
Grade Level: {grade}
Bloom's Taxonomy Level: {bloom_level} — {bloom_desc}
Number of questions to generate: {count}

Source Content:
\"\"\"
{text}
\"\"\"

Generate exactly {count} high-quality multiple-choice questions at the '{bloom_level}' cognitive level.

Rules:
- Each question must be directly answerable from the source content
- Each question must have exactly 4 options (A, B, C, D)
- Exactly one option must be correct
- Distractors must be plausible but clearly wrong
- Include a brief concept explanation (1-2 sentences) for the correct answer

Respond with ONLY a JSON array in this exact format (no markdown, no extra text):
[
  {{
    "question": "Question text here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "answer_index": 0,
    "explanation": "Brief explanation of why the correct answer is right.",
    "bloom_level": "{bloom_level}"
  }}
]

answer_index is the 0-based index of the correct option in the options array."""


def _chunk_text(text: str, max_chars: int = 3000) -> str:
    """Return a representative chunk of text suitable for the prompt."""
    if len(text) <= max_chars:
        return text
    # Take beginning + middle to capture more content
    half = max_chars // 2
    return text[:half] + "\n...\n" + text[-(max_chars - half):]


def _generate_for_level(text: str, subject: str, grade: str,
                        bloom_level: str, count: int) -> list[dict]:
    """Generate MCQs for one Bloom's level."""
    chunk = _chunk_text(text)
    prompt = MCQ_PROMPT.format(
        subject=subject,
        grade=grade,
        bloom_level=bloom_level,
        bloom_desc=BLOOM_LEVELS[bloom_level],
        count=count,
        text=chunk,
    )

    raw = generate_raw(prompt, temperature=0.7)
    questions = extract_json_block(raw)

    if not isinstance(questions, list):
        questions = [questions]

    # Validate and normalise each question
    validated = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        if not all(k in q for k in ("question", "options", "answer_index", "explanation")):
            continue
        if not isinstance(q["options"], list) or len(q["options"]) != 4:
            continue
        if not isinstance(q["answer_index"], int) or not (0 <= q["answer_index"] <= 3):
            continue
        q["bloom_level"] = bloom_level
        q.setdefault("critique_note", "")
        validated.append(q)

    return validated


def generate_mcqs(text: str, subject: str, grade: str, total: int,
                  progress_cb=None) -> list[dict]:
    """
    Generate total MCQs distributed across three Bloom's levels,
    then run the self-critique distractor loop on each question.
    progress_cb(message: str) is called at each major step if provided.
    """
    def notify(msg):
        if progress_cb:
            progress_cb(msg)

    per_level, remainder = divmod(total, 3)
    distribution = {
        "Remember": per_level + remainder,
        "Apply": per_level,
        "Analyse": per_level,
    }

    all_questions = []
    for level, count in distribution.items():
        if count == 0:
            continue
        try:
            notify(f"Generating {count} '{level}' level question(s)…")
            questions = _generate_for_level(text, subject, grade, level, count)
            notify(f"Running self-critique on '{level}' distractors…")
            critiqued = [critique_and_improve(q) for q in questions]
            all_questions.extend(critiqued)
            notify(f"'{level}' level done — {len(critiqued)} question(s) ready.")
        except Exception as e:
            notify(f"'{level}' level failed: {e}")
            all_questions.append({
                "question": f"[Generation failed for {level} level]",
                "options": ["N/A", "N/A", "N/A", "N/A"],
                "answer_index": 0,
                "explanation": str(e),
                "bloom_level": level,
                "critique_note": "error",
            })

    for i, q in enumerate(all_questions, 1):
        q["number"] = i

    return all_questions
