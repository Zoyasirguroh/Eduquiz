"use strict";

// ── Tab switching ──────────────────────────────────────────────────────────
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
  });
});

// ── PDF drop-zone ──────────────────────────────────────────────────────────
const dropZone = document.getElementById("drop-zone");
const pdfInput = document.getElementById("pdf_file");
const fileNameDisplay = document.getElementById("file-name-display");

dropZone.addEventListener("click", e => {
  if (e.target.closest("label")) return;
  pdfInput.click();
});
dropZone.addEventListener("dragover", e => { e.preventDefault(); dropZone.classList.add("dragover"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  const file = e.dataTransfer.files[0];
  if (file && file.type === "application/pdf") setFile(file);
});
pdfInput.addEventListener("change", () => {
  if (pdfInput.files[0]) setFile(pdfInput.files[0]);
});

function setFile(file) {
  const dt = new DataTransfer();
  dt.items.add(file);
  pdfInput.files = dt.files;
  fileNameDisplay.textContent = `Selected: ${file.name}`;
}

// ── Form submission ────────────────────────────────────────────────────────
const form             = document.getElementById("gen-form");
const genBtn           = document.getElementById("gen-btn");
const btnText          = document.getElementById("btn-text");
const btnSpinner       = document.getElementById("btn-spinner");
const errorMsg         = document.getElementById("error-msg");
const resultsSection   = document.getElementById("results-section");
const questionsContainer = document.getElementById("questions-container");
const progressBox      = document.getElementById("progress-box");
const progressLog      = document.getElementById("progress-log");

let currentJobId = null;
let activeSource = null;

form.addEventListener("submit", async e => {
  e.preventDefault();
  setLoading(true);
  hideError();
  clearProgress();
  resultsSection.classList.add("hidden");

  const formData = new FormData(form);
  const activeTab = document.querySelector(".tab-btn.active").dataset.tab;
  if (activeTab === "text") formData.delete("pdf_file");
  else formData.delete("topic_text");

  // Step 1: POST to start job
  let jobId;
  try {
    const res = await fetch("/generate", { method: "POST", body: formData });
    let data;
    try { data = await res.json(); } catch {
      showError(`Server error (HTTP ${res.status}).`);
      setLoading(false);
      return;
    }
    if (!res.ok || data.error) { showError(data.error || "Unexpected error."); setLoading(false); return; }
    jobId = data.job_id;
    currentJobId = jobId;
  } catch {
    showError("Network error — make sure Flask is running.");
    setLoading(false);
    return;
  }

  // Step 2: Open SSE stream for progress
  showProgress();
  if (activeSource) activeSource.close();
  const source = new EventSource(`/progress/${jobId}`);
  activeSource = source;

  source.addEventListener("progress", ev => {
    const { message } = JSON.parse(ev.data);
    addProgressStep(message);
  });

  source.addEventListener("done", ev => {
    source.close();
    const { questions } = JSON.parse(ev.data);
    addProgressStep("All done! Rendering questions…", true);
    setTimeout(() => {
      hideProgress();
      renderQuestions(questions);
      resultsSection.classList.remove("hidden");
      resultsSection.scrollIntoView({ behavior: "smooth" });
      setLoading(false);
    }, 600);
  });

  source.addEventListener("error", ev => {
    source.close();
    try {
      const { error } = JSON.parse(ev.data);
      showError(error);
    } catch {
      showError("Generation failed. Check the Flask console for details.");
    }
    hideProgress();
    setLoading(false);
  });

  source.onerror = () => {
    source.close();
    showError("Lost connection to server.");
    hideProgress();
    setLoading(false);
  };
});

// ── Progress box ───────────────────────────────────────────────────────────
function showProgress() { progressBox.classList.remove("hidden"); }
function hideProgress() { progressBox.classList.add("hidden"); }
function clearProgress() { progressLog.innerHTML = ""; }
function addProgressStep(msg, success = false) {
  const li = document.createElement("li");
  li.className = "progress-step" + (success ? " success" : "");
  li.innerHTML = `<span class="step-icon">${success ? "✓" : "…"}</span> ${escapeHtml(msg)}`;
  progressLog.appendChild(li);
  progressLog.scrollTop = progressLog.scrollHeight;
}

// ── Render questions ───────────────────────────────────────────────────────
const BLOOM_COLORS = { Remember: "#16A34A", Apply: "#2563EB", Analyse: "#7C3AED" };
const OPTION_LABELS = ["A", "B", "C", "D"];

function renderQuestions(questions) {
  questionsContainer.innerHTML = "";
  let currentLevel = null;

  questions.forEach(q => {
    if (q.bloom_level !== currentLevel) {
      currentLevel = q.bloom_level;
      const color = BLOOM_COLORS[currentLevel] || "#374151";
      const hdr = document.createElement("div");
      hdr.className = "bloom-section-header";
      hdr.innerHTML = `<span class="badge" style="background:${color}">${currentLevel}</span>
                       <h3>${currentLevel} Level Questions</h3>`;
      questionsContainer.appendChild(hdr);
    }

    const card = document.createElement("div");
    card.className = "q-card";
    card.innerHTML = `
      <div class="q-card-header">
        <span class="q-number">Q${q.number}.</span>
        <span class="q-text">${escapeHtml(q.question)}</span>
      </div>
      <div class="options-grid">
        ${q.options.map((opt, i) => `
          <div class="option" data-index="${i}" data-correct="${i === q.answer_index}">
            <span class="option-label">${OPTION_LABELS[i]}</span>
            <span>${escapeHtml(opt)}</span>
          </div>`).join("")}
      </div>
      <button class="btn-reveal" data-answer="${q.answer_index}" data-explanation="${escapeHtml(q.explanation)}">
        Show Answer
      </button>
      <div class="q-explanation hidden">
        <strong>Explanation:</strong> ${escapeHtml(q.explanation)}
      </div>
      ${q.critique_note ? `<span class="critique-tag hidden">🔍 ${escapeHtml(q.critique_note)}</span>` : ""}`;

    // Option click — let user pick before revealing
    card.querySelectorAll(".option").forEach(opt => {
      opt.addEventListener("click", () => {
        if (card.dataset.revealed) return; // locked after reveal
        card.querySelectorAll(".option").forEach(o => o.classList.remove("selected"));
        opt.classList.add("selected");
      });
    });

    // Reveal answer button
    card.querySelector(".btn-reveal").addEventListener("click", function () {
      card.dataset.revealed = "1";
      const answerIdx = parseInt(this.dataset.answer);
      card.querySelectorAll(".option").forEach((opt, i) => {
        if (i === answerIdx) opt.classList.add("correct");
        else if (opt.classList.contains("selected")) opt.classList.add("wrong");
      });
      card.querySelector(".q-explanation").classList.remove("hidden");
      const tag = card.querySelector(".critique-tag");
      if (tag) tag.classList.remove("hidden");
      this.classList.add("hidden");
    });

    questionsContainer.appendChild(card);
  });
}

// ── Export buttons ─────────────────────────────────────────────────────────
document.getElementById("export-docx-btn").addEventListener("click", () => {
  if (currentJobId) window.location.href = `/export/docx/${currentJobId}`;
});
document.getElementById("export-xml-btn").addEventListener("click", () => {
  if (currentJobId) window.location.href = `/export/xml/${currentJobId}`;
});

// ── Helpers ────────────────────────────────────────────────────────────────
function setLoading(on) {
  genBtn.disabled = on;
  btnText.textContent = on ? "Generating…" : "Generate Questions";
  btnSpinner.classList.toggle("hidden", !on);
}
function showError(msg) { errorMsg.textContent = msg; errorMsg.classList.remove("hidden"); }
function hideError()    { errorMsg.classList.add("hidden"); errorMsg.textContent = ""; }
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
