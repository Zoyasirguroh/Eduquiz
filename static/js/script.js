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
  if (e.target.closest("label")) return; // label already opens the dialog natively
  pdfInput.click();
});
dropZone.addEventListener("dragover", e => { e.preventDefault(); dropZone.classList.add("dragover"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  const file = e.dataTransfer.files[0];
  if (file && file.type === "application/pdf") {
    setFile(file);
  }
});
pdfInput.addEventListener("change", () => {
  if (pdfInput.files[0]) setFile(pdfInput.files[0]);
});

function setFile(file) {
  // Transfer dropped file to the input via DataTransfer
  const dt = new DataTransfer();
  dt.items.add(file);
  pdfInput.files = dt.files;
  fileNameDisplay.textContent = `Selected: ${file.name}`;
}

// ── Form submission ────────────────────────────────────────────────────────
const form      = document.getElementById("gen-form");
const genBtn    = document.getElementById("gen-btn");
const btnText   = document.getElementById("btn-text");
const btnSpinner = document.getElementById("btn-spinner");
const errorMsg  = document.getElementById("error-msg");
const resultsSection = document.getElementById("results-section");
const questionsContainer = document.getElementById("questions-container");
const exportBtns = document.getElementById("export-btns");

let currentResultId = null;

form.addEventListener("submit", async e => {
  e.preventDefault();
  setLoading(true);
  hideError();

  const formData = new FormData(form);

  // If on text tab, clear any file
  const activeTab = document.querySelector(".tab-btn.active").dataset.tab;
  if (activeTab === "text") {
    formData.delete("pdf_file");
  } else {
    formData.delete("topic_text");
  }

  try {
    const res = await fetch("/generate", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok || data.error) {
      showError(data.error || "An unexpected error occurred.");
      return;
    }

    currentResultId = data.result_id;
    renderQuestions(data.questions);
    resultsSection.classList.remove("hidden");
    resultsSection.scrollIntoView({ behavior: "smooth" });

  } catch (err) {
    showError("Network error — make sure Flask is running.");
  } finally {
    setLoading(false);
  }
});

// ── Render questions ───────────────────────────────────────────────────────
const BLOOM_COLORS = { Remember: "#16A34A", Apply: "#2563EB", Analyse: "#7C3AED" };
const OPTION_LABELS = ["A", "B", "C", "D"];

function renderQuestions(questions) {
  questionsContainer.innerHTML = "";

  let currentLevel = null;

  questions.forEach(q => {
    // Section header per Bloom level
    if (q.bloom_level !== currentLevel) {
      currentLevel = q.bloom_level;
      const hdr = document.createElement("div");
      hdr.className = "bloom-section-header";
      const color = BLOOM_COLORS[currentLevel] || "#374151";
      hdr.innerHTML = `
        <span class="badge" style="background:${color}">${currentLevel}</span>
        <h3>${currentLevel} Level Questions</h3>`;
      questionsContainer.appendChild(hdr);
    }

    // Question card
    const card = document.createElement("div");
    card.className = "q-card";

    // Header
    card.innerHTML = `
      <div class="q-card-header">
        <span class="q-number">Q${q.number}.</span>
        <span class="q-text">${escapeHtml(q.question)}</span>
      </div>
      <div class="options-grid">
        ${q.options.map((opt, i) => `
          <div class="option ${i === q.answer_index ? "correct" : ""}">
            <span class="option-label">${OPTION_LABELS[i]}</span>
            <span>${escapeHtml(opt)}</span>
          </div>`).join("")}
      </div>
      <div class="q-explanation">
        <strong>Explanation:</strong> ${escapeHtml(q.explanation)}
      </div>
      ${q.critique_note ? `<span class="critique-tag">🔍 ${escapeHtml(q.critique_note)}</span>` : ""}
    `;

    questionsContainer.appendChild(card);
  });
}

// ── Export buttons ─────────────────────────────────────────────────────────
document.getElementById("export-docx-btn").addEventListener("click", () => {
  if (currentResultId) window.location.href = `/export/docx/${currentResultId}`;
});
document.getElementById("export-xml-btn").addEventListener("click", () => {
  if (currentResultId) window.location.href = `/export/xml/${currentResultId}`;
});

// ── Helpers ────────────────────────────────────────────────────────────────
function setLoading(on) {
  genBtn.disabled = on;
  btnText.textContent = on ? "Generating…" : "Generate Questions";
  btnSpinner.classList.toggle("hidden", !on);
}

function showError(msg) {
  errorMsg.textContent = msg;
  errorMsg.classList.remove("hidden");
}

function hideError() {
  errorMsg.classList.add("hidden");
  errorMsg.textContent = "";
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
