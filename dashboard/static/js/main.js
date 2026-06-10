/**
 * main.js — AttendAI Dashboard JavaScript
 *
 * Responsibilities:
 *  1. Live clock in topbar
 *  2. Sidebar toggle on mobile
 *  3. initRegistrationCamera() — webcam capture for student registration
 *  4. initAttendanceCamera()  — live feed + face capture for attendance marking
 */

"use strict";

/* ════════════════════════════════════════════════════════════════════════════
   1. TOPBAR CLOCK
   ════════════════════════════════════════════════════════════════════════════ */
(function initClock() {
  const dateEl = document.getElementById("topbarDate");
  const timeEl = document.getElementById("topbarTime");
  if (!dateEl || !timeEl) return;

  function tick() {
    const now = new Date();
    dateEl.textContent = now.toLocaleDateString("en-IN", {
      weekday: "short",
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
    timeEl.textContent = now.toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    });
  }
  tick();
  setInterval(tick, 1000);
})();

/* ════════════════════════════════════════════════════════════════════════════
   2. SIDEBAR TOGGLE (MOBILE)
   ════════════════════════════════════════════════════════════════════════════ */
(function initSidebar() {
  const toggle = document.getElementById("sidebarToggle");
  const sidebar = document.getElementById("sidebar");
  if (!toggle || !sidebar) return;

  // Create overlay element
  const overlay = document.createElement("div");
  overlay.className = "sidebar-overlay";
  document.body.appendChild(overlay);

  function openSidebar() {
    sidebar.classList.add("open");
    overlay.classList.add("visible");
    document.body.style.overflow = "hidden";
  }

  function closeSidebar() {
    sidebar.classList.remove("open");
    overlay.classList.remove("visible");
    document.body.style.overflow = "";
  }

  toggle.addEventListener("click", () =>
    sidebar.classList.contains("open") ? closeSidebar() : openSidebar()
  );
  overlay.addEventListener("click", closeSidebar);
})();

/* ════════════════════════════════════════════════════════════════════════════
   3. REGISTRATION CAMERA
   ════════════════════════════════════════════════════════════════════════════ */
/**
 * @param {Object} cfg - element IDs and config
 */
function initRegistrationCamera(cfg) {
  const video         = document.getElementById(cfg.videoEl);
  const canvas        = document.getElementById(cfg.canvasEl);
  const startBtn      = document.getElementById(cfg.startBtn);
  const captureBtn    = document.getElementById(cfg.captureBtn);
  const retakeBtn     = document.getElementById(cfg.retakeBtn);
  const previewContainer = document.getElementById(cfg.previewContainer);
  const previewImg    = document.getElementById(cfg.previewImg);
  const hiddenFile    = document.getElementById(cfg.hiddenFileInput);
  const uploadInput   = document.getElementById(cfg.uploadInput);
  const webcamOverlay = document.getElementById(cfg.webcamOverlay);
  const faceGuide     = document.getElementById(cfg.faceGuide);
  const form          = document.getElementById(cfg.form);
  const submitBtn     = document.getElementById(cfg.submitBtn);
  const webcamContainer = video ? video.closest(".webcam-container") : null;

  let stream = null;

  if (!video) return;

  /* ── Start camera ──────────────────────────────────────────────────────── */
  startBtn.addEventListener("click", async () => {
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      video.srcObject = stream;
      await video.play();

      webcamOverlay.classList.add("hidden");
      faceGuide.classList.add("visible");
      webcamContainer && webcamContainer.classList.add("streaming");

      startBtn.classList.add("d-none");
      captureBtn.classList.remove("d-none");
    } catch (err) {
      alert("Could not access camera: " + err.message);
    }
  });

  /* ── Capture photo ─────────────────────────────────────────────────────── */
  captureBtn.addEventListener("click", () => {
    if (!stream) return;

    canvas.width  = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);

    canvas.toBlob((blob) => {
      // Show preview
      previewImg.src = canvas.toDataURL("image/jpeg");
      previewContainer.classList.remove("d-none");

      // Stop camera
      stream.getTracks().forEach(t => t.stop());
      video.srcObject = null;
      stream = null;
      faceGuide.classList.remove("visible");
      webcamContainer && webcamContainer.classList.remove("streaming");

      // Set hidden file input
      const file = new File([blob], "capture.jpg", { type: "image/jpeg" });
      const dt   = new DataTransfer();
      dt.items.add(file);
      hiddenFile.files = dt.files;

      captureBtn.classList.add("d-none");
      retakeBtn.classList.remove("d-none");
    }, "image/jpeg", 0.92);
  });

  /* ── Retake ────────────────────────────────────────────────────────────── */
  retakeBtn.addEventListener("click", async () => {
    previewContainer.classList.add("d-none");
    previewImg.src = "";
    hiddenFile.value = "";

    retakeBtn.classList.add("d-none");
    startBtn.classList.remove("d-none");
    webcamOverlay.classList.remove("hidden");
  });

  /* ── Upload from file ──────────────────────────────────────────────────── */
  uploadInput.addEventListener("change", () => {
    const file = uploadInput.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      previewImg.src = e.target.result;
      previewContainer.classList.remove("d-none");
    };
    reader.readAsDataURL(file);

    const dt = new DataTransfer();
    dt.items.add(file);
    hiddenFile.files = dt.files;

    // Stop camera if running
    if (stream) {
      stream.getTracks().forEach(t => t.stop());
      stream = null;
      webcamContainer && webcamContainer.classList.remove("streaming");
    }
    webcamOverlay.classList.remove("hidden");
    faceGuide.classList.remove("visible");
    startBtn.classList.remove("d-none");
    captureBtn.classList.add("d-none");
    retakeBtn.classList.add("d-none");
  });

  /* ── Form submission — show spinner ────────────────────────────────────── */
  form && form.addEventListener("submit", (e) => {
    if (!form.checkValidity()) {
      e.preventDefault();
      form.classList.add("was-validated");
      return;
    }
    if (!hiddenFile.files || !hiddenFile.files.length) {
      e.preventDefault();
      alert("Please capture or upload a photo first.");
      return;
    }
    // Show spinner
    submitBtn.querySelector(".btn-text").classList.add("d-none");
    submitBtn.querySelector(".btn-spinner").classList.remove("d-none");
    submitBtn.disabled = true;
  });
}

/* ════════════════════════════════════════════════════════════════════════════
   4. ATTENDANCE CAMERA
   ════════════════════════════════════════════════════════════════════════════ */
/**
 * @param {Object} cfg
 */
function initAttendanceCamera(cfg) {
  const video             = document.getElementById(cfg.videoEl);
  const canvas            = document.getElementById(cfg.canvasEl);
  const startBtn          = document.getElementById(cfg.startBtn);
  const captureBtn        = document.getElementById(cfg.captureBtn);
  const stopBtn           = document.getElementById(cfg.stopBtn);
  const camOverlay        = document.getElementById(cfg.camOverlay);
  const processingOverlay = document.getElementById(cfg.processingOverlay);
  const liveIndicator     = document.getElementById(cfg.liveIndicator);
  const faceGuide         = document.getElementById(cfg.faceGuide);
  const subjectInput      = document.getElementById(cfg.subjectInput);

  // Result elements
  const resultIdle        = document.getElementById(cfg.resultIdle);
  const resultSuccess     = document.getElementById(cfg.resultSuccess);
  const resultError       = document.getElementById(cfg.resultError);
  const resultDuplicate   = document.getElementById(cfg.resultDuplicate);
  const resName           = document.getElementById(cfg.resName);
  const resRoll           = document.getElementById(cfg.resRoll);
  const resSubject        = document.getElementById(cfg.resSubject);
  const resTime           = document.getElementById(cfg.resTime);
  const resDistance       = document.getElementById(cfg.resDistance);
  const resErrorMsg       = document.getElementById(cfg.resErrorMsg);
  const resDupMsg         = document.getElementById(cfg.resDupMsg);

  // Session table
  const sessionBody       = document.getElementById(cfg.sessionTableBody);
  const sessionEmptyRow   = document.getElementById(cfg.sessionEmptyRow);
  const sessionCount      = document.getElementById(cfg.sessionCount);

  const webcamContainer   = video ? video.closest(".webcam-container") : null;

  let stream = null;
  let sessionRows = 0;

  if (!video) return;

  /* ── Start ─────────────────────────────────────────────────────────────── */
  startBtn.addEventListener("click", async () => {
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 1920 }, height: { ideal: 1080 } },
      });
      video.srcObject = stream;
      await video.play();

      camOverlay.classList.add("hidden");
      faceGuide.classList.add("visible");
      webcamContainer && webcamContainer.classList.add("streaming");
      liveIndicator.classList.add("active");

      startBtn.classList.add("d-none");
      captureBtn.classList.remove("d-none");
      stopBtn.classList.remove("d-none");
    } catch (err) {
      alert("Camera access denied: " + err.message);
    }
  });

  /* ── Stop ──────────────────────────────────────────────────────────────── */
  stopBtn.addEventListener("click", stopCamera);

  function stopCamera() {
    if (stream) {
      stream.getTracks().forEach(t => t.stop());
      stream = null;
    }
    video.srcObject = null;
    camOverlay.classList.remove("hidden");
    faceGuide.classList.remove("visible");
    webcamContainer && webcamContainer.classList.remove("streaming");
    liveIndicator.classList.remove("active");

    startBtn.classList.remove("d-none");
    captureBtn.classList.add("d-none");
    stopBtn.classList.add("d-none");
  }

  /* ── Capture & Identify ────────────────────────────────────────────────── */
  captureBtn.addEventListener("click", async () => {
    const subject = subjectInput.value.trim();
    if (!subject) {
      subjectInput.focus();
      subjectInput.classList.add("border", "border-danger");
      setTimeout(() => subjectInput.classList.remove("border", "border-danger"), 2000);
      return;
    }

    if (!stream) return;

    // Capture frame
    canvas.width  = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    const imageB64 = canvas.toDataURL("image/jpeg", 0.92).split(",")[1];

    // Show processing overlay
    processingOverlay.classList.remove("d-none");
    captureBtn.disabled = true;
    stopBtn.disabled = true;

    // Hide all result states
    [resultIdle, resultSuccess, resultError, resultDuplicate].forEach(el => el.classList.add("d-none"));

    try {
      const resp = await fetch(cfg.markUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_b64: imageB64, subject }),
      });

      const data = await resp.json();

      if (resp.ok && data.success) {
        const d = data.data || {};
        resName.textContent     = d.student_name || "—";
        resRoll.textContent     = d.roll_number   || "—";
        resSubject.textContent  = d.subject        || subject;
        resTime.textContent     = d.time           || new Date().toLocaleTimeString();
        resDistance.textContent = d.distance
          ? `${Math.round((1 - d.distance) * 100)}% match`
          : "—";
        resultSuccess.classList.remove("d-none");

        // Add to session table
        addSessionRow(d, subject);
      } else if (resp.status === 409) {
        resDupMsg.textContent = data.message || "Already marked.";
        resultDuplicate.classList.remove("d-none");
      } else {
        resErrorMsg.textContent = data.message || "Face not recognised.";
        resultError.classList.remove("d-none");
      }
    } catch (err) {
      resErrorMsg.textContent = "Network error: " + err.message;
      resultError.classList.remove("d-none");
    } finally {
      processingOverlay.classList.add("d-none");
      captureBtn.disabled = false;
      stopBtn.disabled = false;
    }
  });

  /* ── Session table ─────────────────────────────────────────────────────── */
  function addSessionRow(d, subject) {
    if (sessionEmptyRow) sessionEmptyRow.style.display = "none";
    sessionRows++;
    sessionCount.textContent = sessionRows;

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${sessionRows}</td>
      <td><strong>${escHtml(d.student_name || "—")}</strong></td>
      <td><span class="badge bg-secondary">${escHtml(d.roll_number || "—")}</span></td>
      <td>${escHtml(d.subject || subject)}</td>
      <td>${escHtml(d.time ? d.time.slice(0, 8) : new Date().toLocaleTimeString())}</td>
      <td><span class="status-badge status-present">Present</span></td>
    `;
    tr.style.animation = "fadeInUp 0.3s ease both";
    sessionBody.prepend(tr);
  }
}

/* ════════════════════════════════════════════════════════════════════════════
   UTILITIES
   ════════════════════════════════════════════════════════════════════════════ */
function escHtml(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

/* ════════════════════════════════════════════════════════════════════════════
   DELETE CONFIRMATION (students list)
   ════════════════════════════════════════════════════════════════════════════ */
(function initDeleteConfirm() {
  document.addEventListener("submit", (e) => {
    const form = e.target;
    if (!form.classList.contains("delete-form")) return;
    const btn  = form.querySelector("[data-name]");
    const name = btn ? btn.dataset.name : "this student";
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) {
      e.preventDefault();
    }
  });
})();
