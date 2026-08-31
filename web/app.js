// CarePilot Case Intake - vanilla JS, no framework, no build step.
//
// Three intake paths, three real backend endpoints:
//   - typed text          -> POST /case-intake            (JSON)
//   - voice recording      -> POST /case-intake/voice       (multipart: audio file)
//   - photo/document       -> POST /case-intake/document    (multipart: symptom_text + document file)
// All three return the same ClinicalHistorySummary shape and are
// rendered through the same renderResult() function below.
//
// UI strings come from web/i18n.js (loaded before this file) via
// window.CarePilotI18n - see that file for the English/Hindi/Telugu
// tables. This file never hardcodes patient-facing English text; every
// label/message goes through t(key).

(function () {
  "use strict";

  var i18n = window.CarePilotI18n;

  function t(key) {
    return i18n.t(key);
  }

  // ---- DOM references -------------------------------------------------

  var form = document.getElementById("intake-form");
  var submitBtn = document.getElementById("submit-btn");
  var statusArea = document.getElementById("status-area");
  var resultsArea = document.getElementById("results-area");
  var resultsList = document.getElementById("results-list");
  var priorityBanner = document.getElementById("priority-banner");
  var reviewNote = document.getElementById("review-note");

  var symptomTextEl = document.getElementById("symptom_text");
  var ageEl = document.getElementById("age");
  var durationEl = document.getElementById("duration_days");

  var micBtn = document.getElementById("mic-btn");
  var micBtnLabel = document.getElementById("mic-btn-label");
  var recordingIndicator = document.getElementById("recording-indicator");
  var recordingTimeEl = document.getElementById("recording-time");

  var documentInput = document.getElementById("document-input");
  var documentLabelText = document.getElementById("document-label-text");
  var documentPreviewWrap = document.getElementById("document-preview-wrap");
  var documentPreviewImg = document.getElementById("document-preview");
  var documentFilenameEl = document.getElementById("document-filename");
  var documentRemoveBtn = document.getElementById("document-remove-btn");

  var langButtons = document.querySelectorAll(".lang-btn");

  // Maps ClinicalHistorySummary field names (app/schemas.py) to the
  // i18n keys behind their plain-language labels.
  var FIELD_LABELS = [
    ["chief_complaint", "field_chief_complaint"],
    ["history_of_present_illness", "field_hpi"],
    ["past_medical_surgical_history", "field_past_history"],
    ["drug_allergy_history", "field_drug_allergy"],
    ["family_history", "field_family_history"],
    ["personal_history", "field_personal_history"],
    ["review_of_systems", "field_ros"],
    ["prior_investigations_summary", "field_investigations"]
  ];

  // TriageLevel values (app/schemas.py) - order matches the priority
  // banner's visual/severity order, not that it matters for lookup.
  var PRIORITY_KEYS = ["emergency", "urgent", "clinic_visit", "self_care"];

  var MAX_DOCUMENT_BYTES = 15 * 1024 * 1024; // 15 MB - generous client-side guard, not a server limit
  var MIN_RECORDING_BYTES = 800; // guards against an instant click producing an empty/near-empty clip

  // ---- State -------------------------------------------------------
  //
  // lastResultData: the last ClinicalHistorySummary rendered, kept so a
  // language switch can redraw the visible result in the new language
  // without a new network call.
  var lastResultData = null;

  // Document/photo upload state.
  var selectedDocumentFile = null;
  var currentPreviewUrl = null;

  // Voice recording state machine: "idle" -> "recording" -> "processing" -> "idle".
  var recorderState = "idle";
  var mediaRecorder = null;
  var mediaStream = null;
  var audioChunks = [];
  var recordingStartTime = null;
  var recordingTimerHandle = null;

  // ---- Wiring --------------------------------------------------------

  form.addEventListener("submit", handleSubmit);
  micBtn.addEventListener("click", handleMicButtonClick);
  documentInput.addEventListener("change", handleDocumentInputChange);
  documentRemoveBtn.addEventListener("click", clearSelectedDocument);

  for (var li = 0; li < langButtons.length; li++) {
    langButtons[li].addEventListener("click", handleLangButtonClick);
  }

  applyLanguage(); // paint the page in the stored/default language on load

  // ---- Submit routing: text vs. document -----------------------------

  function handleSubmit(event) {
    event.preventDefault();

    if (selectedDocumentFile) {
      submitDocumentCase();
    } else {
      submitTextCase();
    }
  }

  function submitTextCase() {
    var symptomText = symptomTextEl.value.trim();
    var ageRaw = ageEl.value;
    var durationRaw = durationEl.value;

    clearStatus();
    hideResults();

    if (symptomText.length < 3) {
      showError(t("error_symptom_too_short"));
      return;
    }

    var payload = { symptom_text: symptomText };
    payload.age = ageRaw === "" ? null : parseInt(ageRaw, 10);
    payload.duration_days = durationRaw === "" ? null : parseInt(durationRaw, 10);

    setLoading(true);
    showLoadingMessage();

    fetch("/case-intake", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then(parseJsonResponse)
      .then(function (result) {
        setLoading(false);
        if (result.ok) {
          clearStatus();
          renderResult(result.body);
        } else {
          showError(friendlyErrorMessage(result.status, result.body));
        }
      })
      .catch(function () {
        setLoading(false);
        showError(t("error_network"));
      });
  }

  function submitDocumentCase() {
    var symptomText = symptomTextEl.value.trim();
    var ageRaw = ageEl.value;
    var durationRaw = durationEl.value;

    clearStatus();
    hideResults();

    if (symptomText.length < 3) {
      showError(t("error_symptom_too_short"));
      return;
    }

    var formData = new FormData();
    formData.append("symptom_text", symptomText);
    if (ageRaw !== "") {
      formData.append("age", ageRaw);
    }
    if (durationRaw !== "") {
      formData.append("duration_days", durationRaw);
    }
    formData.append("document", selectedDocumentFile, selectedDocumentFile.name || "document.jpg");

    setLoading(true, "submit_loading_document");
    showLoadingMessage("submit_loading_document");

    fetch("/case-intake/document", {
      method: "POST",
      body: formData
    })
      .then(parseJsonResponse)
      .then(function (result) {
        setLoading(false);
        if (result.ok) {
          clearStatus();
          renderResult(result.body);
        } else {
          showError(friendlyErrorMessage(result.status, result.body));
        }
      })
      .catch(function () {
        setLoading(false);
        showError(t("error_network"));
      });
  }

  // FastAPI response bodies are JSON on both success and error - shared
  // by all three submit paths (text/document/voice) so this parsing
  // quirk (and the "body wasn't valid JSON at all" fallback) is only
  // written once.
  function parseJsonResponse(response) {
    return response.json().then(
      function (body) {
        return { ok: response.ok, status: response.status, body: body };
      },
      function () {
        return { ok: response.ok, status: response.status, body: null };
      }
    );
  }

  function friendlyErrorMessage(status, body) {
    var detail = extractDetail(body);

    if (status === 503) {
      return t("error_backend_unavailable");
    }

    if (status === 422) {
      // /case-intake/document's OCR-failure branch (app/main.py) returns
      // `f"Could not read the uploaded document: {exc}"`, where {exc} is
      // OcrError's own message - for an undecodable image that includes
      // a raw Pillow exception repr (e.g. a bare Python object address).
      // Never show that to a patient - swap in a clean, actionable
      // message instead of prefixing the generic 422 text onto it.
      if (detail.indexOf("Could not read the uploaded document") !== -1) {
        return t("error_document_unreadable");
      }

      // /case-intake/voice's own 422 branch, for a transcription that
      // came back empty or under PatientInput's min_length=3.
      if (detail.indexOf("Transcribed audio did not produce usable symptom text") !== -1) {
        return t("error_recording_too_short");
      }

      return t("error_422_prefix") + (detail || t("error_422_fallback"));
    }

    if (status >= 500) {
      return t("error_server_generic");
    }

    return detail || t("error_generic_prefix") + status + t("error_generic_suffix");
  }

  // FastAPI error bodies are usually {"detail": "..."} but validation
  // errors can carry {"detail": [{"msg": "...", ...}, ...]} instead -
  // handle both rather than printing "[object Object]" or "undefined".
  function extractDetail(body) {
    if (!body || typeof body !== "object" || !("detail" in body)) {
      return "";
    }

    var detail = body.detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (Array.isArray(detail)) {
      return detail
        .map(function (item) {
          if (item && typeof item === "object" && typeof item.msg === "string") {
            return item.msg;
          }
          return null;
        })
        .filter(Boolean)
        .join(" ");
    }

    return "";
  }

  // ---- Rendering -------------------------------------------------------

  function renderResult(data) {
    if (!data || typeof data !== "object") {
      showError(t("error_unexpected_response"));
      return;
    }

    lastResultData = data;
    renderResultContent(data);

    resultsArea.hidden = false;
    resultsArea.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // Split out from renderResult() so a language switch can redraw
  // already-visible results in the new language without re-triggering
  // the reveal/scroll behavior meant for a fresh submission.
  function renderResultContent(data) {
    resultsList.innerHTML = "";

    FIELD_LABELS.forEach(function (pair) {
      var key = pair[0];
      var labelKey = pair[1];
      var value = data[key];

      // Skip fields that are missing, null, or empty strings rather
      // than printing "null" or a blank box.
      if (value === null || value === undefined || value === "") {
        return;
      }

      var dt = document.createElement("dt");
      dt.textContent = t(labelKey);

      var dd = document.createElement("dd");
      dd.textContent = value;

      resultsList.appendChild(dt);
      resultsList.appendChild(dd);
    });

    renderPriorityBanner(data.priority_level);

    if (data.is_reviewed_by_physician) {
      reviewNote.textContent = t("review_note_reviewed");
    } else {
      reviewNote.textContent = t("review_note_unreviewed");
    }

    renderAudioSummaryControl(data);
  }

  // Rebuilt fresh on every render (including a language switch, via
  // renderResultContent), same "clear and repopulate" pattern as
  // resultsList/priorityBanner above - so a listen click always targets
  // the currently-selected language, not whatever language was active
  // when the button was first created.
  function renderAudioSummaryControl(data) {
    var existing = document.getElementById("audio-summary-control");
    if (existing) {
      existing.parentNode.removeChild(existing);
    }

    // data.case_id is only absent if ClinicalHistorySummary was somehow
    // rendered without ever going through a real /case-intake* endpoint
    // (every real API response has it, once persisted) - defensive, not
    // an expected path through the real UI.
    if (!data.case_id) {
      return;
    }

    var wrap = document.createElement("div");
    wrap.id = "audio-summary-control";
    wrap.className = "audio-summary-control";

    var button = document.createElement("button");
    button.type = "button";
    button.className = "listen-btn";
    button.textContent = t("listen_button_label");

    var audio = document.createElement("audio");
    audio.hidden = true;
    audio.controls = true;

    button.addEventListener("click", function () {
      button.disabled = true;
      var label = t("listen_button_label");
      button.textContent = t("listen_loading");

      fetch(
        "/cases/" + encodeURIComponent(data.case_id) + "/audio-summary?language=" + encodeURIComponent(i18n.getLang())
      )
        .then(function (response) {
          if (!response.ok) {
            throw new Error("audio-summary request failed: " + response.status);
          }
          return response.blob();
        })
        .then(function (blob) {
          audio.src = URL.createObjectURL(blob);
          audio.hidden = false;
          button.disabled = false;
          button.textContent = label;
          // Autoplay can be silently blocked by the browser - the visible
          // <audio controls> element still lets the user press play
          // themselves either way, so a rejected play() isn't an error.
          audio.play().catch(function () {});
        })
        .catch(function () {
          button.disabled = false;
          button.textContent = label;
          showError(t("listen_error"));
        });
    });

    wrap.appendChild(button);
    wrap.appendChild(audio);
    reviewNote.parentNode.insertBefore(wrap, reviewNote.nextSibling);
  }

  function renderPriorityBanner(priority) {
    priorityBanner.className = "priority-banner";
    priorityBanner.innerHTML = "";

    var textSpan = document.createElement("span");
    textSpan.className = "priority-banner-text";

    if (priority && PRIORITY_KEYS.indexOf(priority) !== -1) {
      priorityBanner.classList.add("priority-" + priority);
      textSpan.textContent = t("priority_" + priority);

      var template = document.getElementById("icon-" + priority);
      if (template && "content" in template) {
        priorityBanner.appendChild(template.content.cloneNode(true));
      }
    } else {
      textSpan.textContent = t("priority_unknown_prefix") + (priority || "unknown");
    }

    priorityBanner.appendChild(textSpan);
  }

  function hideResults() {
    resultsArea.hidden = true;
    resultsList.innerHTML = "";
    priorityBanner.innerHTML = "";
    priorityBanner.className = "priority-banner";
    reviewNote.textContent = "";
    lastResultData = null;
  }

  function setLoading(isLoading, loadingKey) {
    submitBtn.disabled = isLoading;
    micBtn.disabled = isLoading;
    submitBtn.textContent = isLoading ? t(loadingKey || "submit_loading") : t("submit_label");
  }

  function showLoadingMessage(key) {
    statusArea.innerHTML = '<p class="loading"></p>';
    statusArea.querySelector(".loading").textContent = t(key || "status_sending");
  }

  function showError(message) {
    statusArea.innerHTML = '<div class="error-box"></div>';
    statusArea.querySelector(".error-box").textContent = message;
  }

  function clearStatus() {
    statusArea.innerHTML = "";
  }

  // ---- Language toggle -------------------------------------------------

  function handleLangButtonClick(event) {
    var code = event.currentTarget.getAttribute("data-lang");
    i18n.setLang(code);
    applyLanguage();
  }

  function applyLanguage() {
    var lang = i18n.getLang();
    document.documentElement.setAttribute("lang", lang);
    applyStaticTranslations();
    updateLangButtonsUI(lang);
    refreshMicLabel();
    refreshDocumentLabel();

    // Re-render an already-visible result in the new language, without
    // re-triggering the scroll-into-view a fresh submission gets.
    if (lastResultData) {
      renderResultContent(lastResultData);
    }
  }

  function applyStaticTranslations() {
    var textNodes = document.querySelectorAll("[data-i18n]");
    for (var i = 0; i < textNodes.length; i++) {
      textNodes[i].textContent = t(textNodes[i].getAttribute("data-i18n"));
    }

    var placeholderNodes = document.querySelectorAll("[data-i18n-placeholder]");
    for (var j = 0; j < placeholderNodes.length; j++) {
      placeholderNodes[j].setAttribute("placeholder", t(placeholderNodes[j].getAttribute("data-i18n-placeholder")));
    }

    var ariaNodes = document.querySelectorAll("[data-i18n-aria-label]");
    for (var k = 0; k < ariaNodes.length; k++) {
      ariaNodes[k].setAttribute("aria-label", t(ariaNodes[k].getAttribute("data-i18n-aria-label")));
    }
  }

  function updateLangButtonsUI(lang) {
    for (var i = 0; i < langButtons.length; i++) {
      var btn = langButtons[i];
      var isActive = btn.getAttribute("data-lang") === lang;
      btn.setAttribute("aria-pressed", isActive ? "true" : "false");
      btn.classList.toggle("is-active", isActive);
    }
  }

  // Sets a dynamic label's i18n key AND repaints it immediately (rather
  // than waiting for the next full applyStaticTranslations() pass), so
  // e.g. the mic button's label updates the instant recording starts,
  // not only on the next language switch.
  function setI18nKey(el, key) {
    el.setAttribute("data-i18n", key);
    el.textContent = t(key);
  }

  function refreshMicLabel() {
    setI18nKey(micBtnLabel, recorderState === "recording" ? "mic_button_recording" : "mic_button_idle");
  }

  function refreshDocumentLabel() {
    setI18nKey(documentLabelText, selectedDocumentFile ? "document_change_label" : "document_button_label");
  }

  // ---- Document / photo upload -----------------------------------------

  function handleDocumentInputChange() {
    var file = documentInput.files && documentInput.files[0];
    if (!file) {
      return;
    }

    if (file.type.indexOf("image/") !== 0) {
      showError(t("error_document_invalid_type"));
      documentInput.value = "";
      return;
    }

    if (file.size > MAX_DOCUMENT_BYTES) {
      showError(t("error_document_too_large"));
      documentInput.value = "";
      return;
    }

    clearStatus();
    setSelectedDocument(file);
  }

  function setSelectedDocument(file) {
    selectedDocumentFile = file;

    if (currentPreviewUrl) {
      URL.revokeObjectURL(currentPreviewUrl);
    }
    currentPreviewUrl = URL.createObjectURL(file);

    documentPreviewImg.src = currentPreviewUrl;
    documentFilenameEl.textContent = t("document_filename_prefix") + file.name;
    documentPreviewWrap.hidden = false;
    refreshDocumentLabel();
  }

  function clearSelectedDocument() {
    selectedDocumentFile = null;

    if (currentPreviewUrl) {
      URL.revokeObjectURL(currentPreviewUrl);
      currentPreviewUrl = null;
    }

    documentInput.value = "";
    documentPreviewImg.removeAttribute("src");
    documentFilenameEl.textContent = "";
    documentPreviewWrap.hidden = true;
    refreshDocumentLabel();
  }

  // ---- Voice recording ---------------------------------------------------

  function handleMicButtonClick() {
    if (recorderState === "idle") {
      startRecording();
    } else if (recorderState === "recording") {
      stopRecording();
    }
    // "processing": mic-btn is disabled, so clicks shouldn't reach here.
  }

  function startRecording() {
    if (
      !navigator.mediaDevices ||
      typeof navigator.mediaDevices.getUserMedia !== "function" ||
      typeof window.MediaRecorder === "undefined"
    ) {
      showError(t("error_mic_unsupported"));
      return;
    }

    clearStatus();

    navigator.mediaDevices
      .getUserMedia({ audio: true })
      .then(beginRecordingWithStream)
      .catch(handleMicError);
  }

  function beginRecordingWithStream(stream) {
    mediaStream = stream;
    audioChunks = [];

    try {
      mediaRecorder = new MediaRecorder(stream);
    } catch (err) {
      stopMediaStreamTracks();
      showError(t("error_mic_generic"));
      return;
    }

    mediaRecorder.addEventListener("dataavailable", function (event) {
      if (event.data && event.data.size > 0) {
        audioChunks.push(event.data);
      }
    });
    mediaRecorder.addEventListener("stop", onRecordingStopped);

    recorderState = "recording";
    recordingStartTime = Date.now();
    updateRecordingTimeDisplay();
    recordingTimerHandle = setInterval(updateRecordingTimeDisplay, 250);

    micBtn.classList.add("is-recording");
    micBtn.setAttribute("aria-pressed", "true");
    setI18nKey(micBtnLabel, "mic_button_recording");
    recordingIndicator.hidden = false;
    submitBtn.disabled = true;

    mediaRecorder.start();
  }

  function handleMicError(err) {
    var name = err && err.name;
    if (name === "NotAllowedError" || name === "PermissionDeniedError" || name === "SecurityError") {
      showError(t("error_mic_permission_denied"));
    } else if (name === "NotFoundError" || name === "DevicesNotFoundError") {
      showError(t("error_mic_not_found"));
    } else {
      showError(t("error_mic_generic"));
    }
    resetMicToIdle();
  }

  function stopRecording() {
    if (recorderState !== "recording" || !mediaRecorder) {
      return;
    }

    clearInterval(recordingTimerHandle);
    recordingTimerHandle = null;

    recorderState = "processing";
    micBtn.disabled = true;
    micBtn.classList.remove("is-recording");
    micBtn.classList.add("is-processing");
    setI18nKey(micBtnLabel, "recording_processing");
    recordingIndicator.hidden = true;
    showLoadingMessage("recording_processing");

    mediaRecorder.stop();
  }

  function onRecordingStopped() {
    stopMediaStreamTracks();

    var mimeType = (mediaRecorder && mediaRecorder.mimeType) || "audio/webm";
    var blob = new Blob(audioChunks, { type: mimeType });
    audioChunks = [];

    if (blob.size < MIN_RECORDING_BYTES) {
      showError(t("error_recording_too_short"));
      resetMicToIdle();
      return;
    }

    submitVoiceBlob(blob, mimeType);
  }

  function stopMediaStreamTracks() {
    if (mediaStream) {
      mediaStream.getTracks().forEach(function (track) {
        track.stop();
      });
      mediaStream = null;
    }
  }

  function submitVoiceBlob(blob, mimeType) {
    clearStatus();
    hideResults();

    var filename = "recording." + extensionForMime(mimeType);
    var ageRaw = ageEl.value;
    var durationRaw = durationEl.value;

    var formData = new FormData();
    formData.append("audio", blob, filename);
    if (ageRaw !== "") {
      formData.append("age", ageRaw);
    }
    if (durationRaw !== "") {
      formData.append("duration_days", durationRaw);
    }

    showLoadingMessage("recording_processing");

    fetch("/case-intake/voice", {
      method: "POST",
      body: formData
    })
      .then(parseJsonResponse)
      .then(function (result) {
        if (result.ok) {
          clearStatus();
          renderResult(result.body);
        } else {
          showError(friendlyErrorMessage(result.status, result.body));
        }
      })
      .catch(function () {
        showError(t("error_network"));
      })
      .finally(resetMicToIdle);
  }

  function resetMicToIdle() {
    recorderState = "idle";
    clearInterval(recordingTimerHandle);
    recordingTimerHandle = null;

    micBtn.disabled = false;
    micBtn.classList.remove("is-recording", "is-processing");
    micBtn.setAttribute("aria-pressed", "false");
    setI18nKey(micBtnLabel, "mic_button_idle");
    recordingIndicator.hidden = true;
    submitBtn.disabled = false;
  }

  function updateRecordingTimeDisplay() {
    var elapsedMs = Date.now() - recordingStartTime;
    var totalSeconds = Math.max(0, Math.floor(elapsedMs / 1000));
    var minutes = Math.floor(totalSeconds / 60);
    var seconds = totalSeconds % 60;
    recordingTimeEl.textContent = minutes + ":" + (seconds < 10 ? "0" : "") + seconds;
  }

  function extensionForMime(mimeType) {
    if (!mimeType) {
      return "webm";
    }
    if (mimeType.indexOf("webm") !== -1) {
      return "webm";
    }
    if (mimeType.indexOf("ogg") !== -1) {
      return "ogg";
    }
    if (mimeType.indexOf("mp4") !== -1) {
      return "m4a";
    }
    if (mimeType.indexOf("wav") !== -1) {
      return "wav";
    }
    return "webm";
  }
})();
