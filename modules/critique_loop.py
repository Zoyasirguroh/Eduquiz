"""LLM self-critique loop for distractor quality evaluation and regeneration."""

import json
from modules.llm_client import generate_raw, extract_json_block

CRITIQUE_PROMPT = """You are an expert educational assessment reviewer.

Given the following MCQ, evaluate the quality of the DISTRACTORS (the wrong answer choices).

A good distractor must:
1. Be clearly wrong but plausible (not obviously incorrect)
2. Be similar in length and grammatical form to the correct answer
3. Represent a common misconception or related concept
4. NOT be a trick question or trivially false statement

Question: {question}
Correct Answer: {correct}
Distractors: {distractors}

Respond with ONLY a JSON object in this exact format:
{{
  "pass": true or false,
  "reason": "brief explanation",
  "improved_distractors": ["distractor1", "distractor2", "distractor3"]
}}

If distractors pass the quality check, set "pass": true and repeat the original distractors in improved_distractors.
If they fail, set "pass": false and provide better replacements in improved_distractors."""


def critique_and_improve(question: dict) -> dict:
    """
    Run the self-critique loop on a single MCQ.
    Returns the question dict (potentially with improved distractors).
    """
    correct_answer = question["options"][question["answer_index"]]
    distractors = [
        opt for i, opt in enumerate(question["options"])
        if i != question["answer_index"]
    ]

    prompt = CRITIQUE_PROMPT.format(
        question=question["question"],
        correct=correct_answer,
        distractors=json.dumps(distractors),
    )

    try:
        raw = generate_raw(prompt, temperature=0.3)
        result = extract_json_block(raw)

        if not result.get("pass", True):
            # Replace distractors with improved ones
            improved = result.get("improved_distractors", distractors)
            if len(improved) == 3:
                # Re-insert correct answer at original index
                idx = question["answer_index"]
                new_options = improved[:idx] + [correct_answer] + improved[idx:]
                question["options"] = new_options
                question["critique_note"] = result.get("reason", "Distractors regenerated")
            else:
                question["critique_note"] = "Critique skipped: unexpected format"
        else:
            question["critique_note"] = "Distractors passed quality check"

    except Exception as e:
        # Non-fatal: keep original question if critique fails
        question["critique_note"] = f"Critique unavailable: {str(e)}"

    return question
