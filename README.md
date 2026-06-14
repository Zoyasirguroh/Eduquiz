# EduQuiz Forge

An AI-powered multiple-choice question (MCQ) generator for educators. Upload a PDF or paste text from any subject, and EduQuiz Forge automatically creates curriculum-aligned questions categorised by Bloom's Taxonomy — all running locally on your computer, no internet or API keys required.

---

## What It Does

- **Generates MCQs from any educational content** — paste text or upload a PDF
- **Aligns questions to Bloom's Taxonomy** across three cognitive levels:
  - *Remember* — recall facts and definitions
  - *Apply* — solve problems using knowledge
  - *Analyse* — draw inferences and break down information
- **Optional self-critique loop** — automatically evaluates and improves distractor (wrong answer) quality
- **Exports results** to a styled Word document (`.docx`) or Moodle-compatible XML
- **Streams progress in real time** so you can watch questions being generated live
- **Completely local** — powered by [Ollama](https://ollama.ai), your data never leaves your machine

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask |
| AI / LLM | Ollama (local) with `llama3.2:latest` |
| PDF parsing | PyMuPDF |
| Word export | python-docx |
| Frontend | HTML, CSS, Vanilla JavaScript |

---

## Prerequisites

Before you begin, make sure you have the following installed:

1. **Python 3.8 or newer** — [Download Python](https://www.python.org/downloads/)
2. **pip** — comes bundled with Python
3. **Ollama** — [Download Ollama](https://ollama.ai/download)

> **New to this?** Ollama is a free tool that lets you run AI language models on your own computer. Think of it like having a private ChatGPT that runs offline.

---

## Step-by-Step Setup Guide

### Step 1 — Download the project

If you have Git installed:

```bash
git clone https://github.com/your-username/Eduquiz.git
cd Eduquiz
```

Or download the ZIP from GitHub, extract it, and open the folder in your terminal.

---

### Step 2 — Create a virtual environment (recommended)

A virtual environment keeps this project's dependencies isolated from the rest of your system.

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` appear at the start of your terminal prompt. This means the virtual environment is active.

---

### Step 3 — Install Python dependencies

```bash
pip install -r requirements.txt
```

This installs Flask, PyMuPDF, python-docx, and the other libraries the project needs. It may take a minute.

---

### Step 4 — Install and start Ollama

1. Download and install Ollama from [https://ollama.ai/download](https://ollama.ai/download).

2. Open a **new terminal window** and start the Ollama service:

```bash
ollama serve
```

Leave this terminal running in the background. Ollama needs to be running whenever you use EduQuiz Forge.

---

### Step 5 — Pull the AI model

In another terminal window, download the language model (this only needs to be done once):

```bash
ollama pull llama3.2:latest
```

The model is about 2 GB. Download time depends on your internet speed.

To confirm it downloaded correctly:
```bash
ollama list
```

You should see `llama3.2:latest` in the output.

---

### Step 6 — Run the app

Go back to your project terminal (with the virtual environment active) and run:

```bash
python app.py
```

You should see output like:

```
 * Running on http://127.0.0.1:5000
```

---

### Step 7 — Open in your browser

Open your web browser and go to:

```
http://localhost:5000
```

EduQuiz Forge is now running. You can start generating questions.

---

## How to Use

1. **Choose your input method** — switch between the *Text* tab (paste content) or the *PDF* tab (upload a file, max 16 MB).
2. **Fill in the details** — enter the subject name, grade level, and how many questions you want (1–20).
3. **Enable self-critique** (optional) — tick the checkbox to have the AI review and improve its own distractor quality before showing results.
4. **Click Generate** — a progress bar will show the generation status in real time.
5. **Review your questions** — click an answer option to select it, then click *Show Answer* to reveal the correct answer and explanation.
6. **Export** — download as a Word document or Moodle XML using the buttons at the bottom.

---

## Project Structure

```
Eduquiz/
├── app.py                  # Flask application and API routes
├── requirements.txt        # Python package dependencies
├── modules/
│   ├── pdf_parser.py       # Extracts text from uploaded PDFs
│   ├── mcq_generator.py    # Core MCQ generation pipeline
│   ├── llm_client.py       # Communicates with the Ollama API
│   ├── critique_loop.py    # Self-critique quality assurance
│   └── exporter.py         # Generates .docx and Moodle XML files
├── templates/
│   └── index.html          # Main web UI
├── static/
│   ├── css/style.css       # Styles
│   └── js/script.js        # Frontend logic and SSE progress updates
├── uploads/                # Temporary file storage (auto-cleaned)
└── pdfs/                   # Sample curriculum PDFs for testing
```

---

## Troubleshooting

**The page loads but question generation fails or hangs**

Make sure Ollama is running (`ollama serve`) and the model is downloaded (`ollama list`). The app connects to Ollama at `http://localhost:11434` — if that address is unreachable, generation will time out after 120 seconds.

**`ModuleNotFoundError` when running `app.py`**

Your virtual environment may not be active. Run the activation command from Step 2 again, then retry.

**PDF upload fails with "file too large"**

The maximum upload size is 16 MB. Try a shorter document or paste the text directly using the Text tab.

**Generated questions look incorrect or repetitive**

The quality of output depends on the amount and clarity of the input text. Aim for at least a few paragraphs of focused educational content. Enabling the self-critique option can also improve distractor quality.

**Ollama is slow**

LLM inference speed depends on your hardware. On a machine without a GPU, generating 10 questions may take 2–5 minutes. This is normal.

---

## Sample PDFs

The `pdfs/` folder includes ready-to-use curriculum content for testing:

- Biology Grade 11 — Cell: The Unit of Life
- Chemistry Grade 11 — Structure of the Atom
- Computer Science (UG) — Data Structures
- History Grade 10 — The Industrial Revolution
- Physics Grade 11 — Laws of Motion

---

## Requirements

```
flask>=3.0.0
PyMuPDF>=1.24.0
python-docx>=1.1.0
requests>=2.31.0
werkzeug>=3.0.0
```

---

## License

This project was developed as an academic project at The Oxford College of Science (2025–26).
