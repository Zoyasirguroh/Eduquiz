"""Ollama LLM client for local Gemma-7B-IT inference."""

import json
import re
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma:7b-instruct"  # Ollama model tag for Gemma-7B-IT


def _call_ollama(prompt: str, temperature: float = 0.7) -> str:
    """Send a prompt to the Ollama API and return the full response text."""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 2048,
        },
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Cannot connect to Ollama. Make sure Ollama is running: `ollama serve`"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("Ollama request timed out. The model may be loading — try again.")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Ollama HTTP error: {e}")


def generate_raw(prompt: str, temperature: float = 0.7) -> str:
    """Public wrapper used by mcq_generator and critique_loop."""
    return _call_ollama(prompt, temperature)


def extract_json_block(text: str) -> list | dict:
    """Extract the first JSON array or object from a raw LLM response."""
    # Try to find a ```json ... ``` block first
    match = re.search(r"```json\s*([\s\S]+?)\s*```", text)
    if match:
        return json.loads(match.group(1))

    # Fall back: find first [ or { and parse from there
    start = min(
        (text.find("[") if "[" in text else len(text)),
        (text.find("{") if "{" in text else len(text)),
    )
    if start < len(text):
        return json.loads(text[start:])

    raise ValueError("No JSON found in LLM response")
