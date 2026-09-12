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

  var viewButtons = document.querySelectorAll(".view-btn");
  var patientViewEl = document.getElementById("patient-view");
  var physicianViewEl = document.getElementById("physician-view");
  var physicianAyushFilter = document.getElementById("physician-ayush-filter");
  var physicianCaseListEl = document.getElementById("physician-case-list");
  var physicianCaseListEmpty = document.getElementById("physician-case-list-empty");
  var physicianCaseListError = document.getElementById("physician-case-list-error");
  var physicianCaseDetailEl = document.getElementById("physician-case-detail");

  // Step wizard - one <form>, four <fieldset>s shown one at a time by
  // toggling `hidden` (see web/styles.css, "Step wizard"). Every field
  // above keeps the exact id app.js already reads/writes; the wizard
  // only ever changes which fieldset is visible.
  var stepIndicator = document.getElementById("step-indicator");
  var stepDots = document.querySelectorAll(".step-dot");
  var wizardSteps = document.querySelectorAll(".wizard-step");
  var stepNextButtons = document.querySelectorAll(".step-next-btn");
  var stepBackButtons = document.querySelectorAll(".step-back-btn");
  var reviewRecap = document.getElementById("review-recap");

  var redflagHint = document.getElementById("redflag-hint");
  var socratesQuestionsEl = document.getElementById("socrates-questions");

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

  // Step wizard: which fieldset is showing right now. Not persisted -
  // every fresh page load (or reload) starts back at step 1.
  var currentStep = 1;

  // Live red-flag hint state. redFlagTerms stays null until GET
  // /red-flag-terms resolves (or fails - the hint is a nice-to-have, so
  // a failed fetch just means no hint ever shows, not a broken page).
  // redflagDebounceHandle debounces the check off the textarea's own
  // "input" event so it runs once per pause in typing, not once per
  // keystroke.
  var redFlagTerms = null;
  var redflagDebounceHandle = null;
  var REDFLAG_DEBOUNCE_MS = 300;

  // SOCRATES follow-up questions (POST /socrates-questions) are
  // deterministic - the same eight questions come back for any real
  // complaint (see app/agents/socrates_intake.py's own docstring for
  // why) - so this only ever needs fetching once per page load, not
  // re-fetched on every keystroke the way the red-flag hint's own
  // check is. socratesQuestionsRequested guards against firing a
  // second, redundant request while the first is still in flight or
  // has already succeeded.
  var socratesQuestionsRequested = false;

  // ---- Physician console state -----------------------------------------
  //
  // currentView: which of #patient-view/#physician-view is showing -
  // both stay in the DOM at all times (toggled via `hidden`), so
  // switching views never loses in-progress patient-wizard state.
  // physicianLastCaseDetail: the last case detail fetched, kept the same
  // way lastResultData is above, so a language switch can redraw the
  // open case's labels without a redundant GET /cases/{id}.
  var currentView = "patient";
  var physicianLastCaseDetail = null;

  // ---- Wiring --------------------------------------------------------

  form.addEventListener("submit", handleSubmit);
  micBtn.addEventListener("click", handleMicButtonClick);
  documentInput.addEventListener("change", handleDocumentInputChange);
  documentRemoveBtn.addEventListener("click", clearSelectedDocument);
  symptomTextEl.addEventListener("input", handleSymptomTextInput);

  for (var li = 0; li < langButtons.length; li++) {
    langButtons[li].addEventListener("click", handleLangButtonClick);
  }

  for (var vi = 0; vi < viewButtons.length; vi++) {
    viewButtons[vi].addEventListener("click", handleViewButtonClick);
  }

  physicianAyushFilter.addEventListener("change", loadPhysicianCases);

  for (var ni = 0; ni < stepNextButtons.length; ni++) {
    stepNextButtons[ni].addEventListener("click", handleStepNextClick);
  }

  for (var bi = 0; bi < stepBackButtons.length; bi++) {
    stepBackButtons[bi].addEventListener("click", handleStepBackClick);
  }

  applyLanguage(); // paint the page in the stored/default language on load
  loadRedFlagTerms();

  // No goToStep(1) call here on purpose: the static markup (web/index.html)
  // already renders step 1 as the visible/current step by default
  // (fieldsets 2-4 carry `hidden`, step-dot 1 alone carries
  // `is-current`/`aria-current`). goToStep() itself moves focus to the
  // shown step's legend, which scrolls it into view - correct behavior
  // for a real Next/Back click, but calling it here at page load would
  // scroll a first-time visitor straight past the hero before they ever
  // saw it. currentStep's initial value (declared above) already
  // matches this default state, so nothing needs re-syncing.

  // ---- Step wizard -----------------------------------------------------

  function handleStepNextClick(event) {
    var fromStep = parseInt(event.currentTarget.closest(".wizard-step").getAttribute("data-step"), 10);

    // Step 1 -> 2 is the only transition with a real gate: the same
    // min-length-3 rule the server enforces (app/schemas.py's
    // PatientInput.symptom_text), checked here so a patient finds out
    // before reaching the review step, not after a failed submit.
    if (fromStep === 1 && symptomTextEl.value.trim().length < 3) {
      showError(t("error_symptom_too_short"));
      symptomTextEl.focus();
      return;
    }

    clearStatus();
    goToStep(fromStep + 1);
  }

  function handleStepBackClick(event) {
    var fromStep = parseInt(event.currentTarget.closest(".wizard-step").getAttribute("data-step"), 10);
    clearStatus();
    goToStep(fromStep - 1);
  }

  function goToStep(step) {
    currentStep = step;

    for (var si = 0; si < wizardSteps.length; si++) {
      var fieldset = wizardSteps[si];
      fieldset.hidden = parseInt(fieldset.getAttribute("data-step"), 10) !== step;
    }

    for (var di = 0; di < stepDots.length; di++) {
      var dot = stepDots[di];
      var dotStep = parseInt(dot.getAttribute("data-step"), 10);
      dot.classList.toggle("is-current", dotStep === step);
      dot.classList.toggle("is-done", dotStep < step);
      if (dotStep === step) {
        dot.setAttribute("aria-current", "step");
      } else {
        dot.removeAttribute("aria-current");
      }
    }

    if (step === 4) {
      renderReviewRecap();
    }

    // Move focus to the newly-shown step's heading-equivalent (its
    // legend) rather than leaving it on a now-hidden Next/Back button -
    // hidden elements can't hold focus, and a sighted user's eye also
    // needs to land back at the top of the new step, not stay wherever
    // the click happened to be.
    var activeFieldset = document.getElementById("wizard-step-" + step);
    if (activeFieldset) {
      var legend = activeFieldset.querySelector("legend");
      if (legend) {
        legend.setAttribute("tabindex", "-1");
        legend.focus();
      }
    }
  }

  // Read-only recap built from the exact DOM values the real submit
  // already reads (symptomTextEl.value, ageEl.value, ..., the file
  // object app.js already tracks) - not a second, separately-updated
  // copy of the form's state that could show something different from
  // what actually gets submitted.
  function renderReviewRecap() {
    reviewRecap.innerHTML = "";

    var symptomText = symptomTextEl.value.trim();
    appendRecapRow(t("review_recap_symptoms"), symptomText, false);

    var ageValue = ageEl.value.trim();
    appendRecapRow(t("review_recap_age"), ageValue === "" ? t("review_recap_not_provided") : ageValue, ageValue === "");

    var durationValue = durationEl.value.trim();
    appendRecapRow(
      t("review_recap_duration"),
      durationValue === "" ? t("review_recap_not_provided") : durationValue,
      durationValue === ""
    );

    var documentLabel = selectedDocumentFile
      ? t("document_filename_prefix") + selectedDocumentFile.name
      : t("review_recap_no_document");
    appendRecapRow(t("review_recap_document"), documentLabel, !selectedDocumentFile);
  }

  // `value` is always the exact text to render - `isMuted` only toggles
  // the softer, italic styling (see web/styles.css, .review-recap
  // dd.is-empty) for a row with nothing meaningful entered. It must NOT
  // also decide which text to show, or every "muted" row collapses onto
  // the same generic "Not provided" string regardless of what its
  // caller actually wanted displayed - exactly the bug this shape had
  // until a real end-to-end run caught the photo row showing "Not
  // provided" instead of "No photo added".
  function appendRecapRow(label, value, isMuted) {
    var dt = document.createElement("dt");
    dt.textContent = label;

    var dd = document.createElement("dd");
    dd.textContent = value;
    if (isMuted) {
      dd.classList.add("is-empty");
    }

    reviewRecap.appendChild(dt);
    reviewRecap.appendChild(dd);
  }

  // ---- Live red-flag hint -----------------------------------------------
  //
  // Checks typed text against the REAL term list app/agents/intake.py's
  // scan_red_flags() matches on (fetched once from GET /red-flag-terms,
  // not a second hand-copied list that could drift from it). This is a
  // preview only - the authoritative decision is still made server-side
  // on submit, same as always; a fetch failure here just means the hint
  // never shows, not a broken page.

  function loadRedFlagTerms() {
    fetch("/red-flag-terms")
      .then(function (response) {
        if (!response.ok) {
          throw new Error("red-flag-terms request failed: " + response.status);
        }
        return response.json();
      })
      .then(function (body) {
        if (body && Array.isArray(body.terms)) {
          redFlagTerms = body.terms.map(function (term) {
            return term.toLowerCase();
          });
        }
      })
      .catch(function () {
        redFlagTerms = null;
      });
  }

  // Mirrors the normalization app/agents/intake.py's scan_red_flags()
  // applies before matching (docs/INTERVIEW_NOTES.md, Days 14 and 16):
  // lowercase, then collapse any run of whitespace OR Unicode category
  // "Cf" (zero-width/format) characters to a single space, so a term
  // split by a double space or a zero-width character between its words
  // still matches here the same way it does server-side. \p{Cf} is a
  // native regex Unicode property escape (ES2018+) - no hand-maintained
  // character list to fall out of sync with unicodedata.category().
  function normalizeForRedFlagPreview(text) {
    return text
      .toLowerCase()
      .replace(/[\s\p{Cf}]+/gu, " ")
      .trim();
  }

  function handleSymptomTextInput() {
    clearTimeout(redflagDebounceHandle);
    redflagDebounceHandle = setTimeout(checkRedFlagHint, REDFLAG_DEBOUNCE_MS);
    maybeLoadSocratesQuestions();
  }

  // Fires once the complaint reaches the same min-length-3 the server
  // itself enforces (app/schemas.py's PatientInput.symptom_text) - no
  // separate debounce timer needed, since socratesQuestionsRequested
  // already prevents more than one real request regardless of how many
  // keystrokes land before or after that length is reached.
  function maybeLoadSocratesQuestions() {
    if (socratesQuestionsRequested || symptomTextEl.value.trim().length < 3) {
      return;
    }
    socratesQuestionsRequested = true;

    fetch("/socrates-questions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chief_complaint: symptomTextEl.value.trim() })
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("socrates-questions request failed: " + response.status);
        }
        return response.json();
      })
      .then(renderSocratesQuestions)
      .catch(function () {
        // A live typing hint is a nice-to-have, not the safety-critical
        // path - same standing rule loadRedFlagTerms() already follows
        // below: a failed fetch just means the hint never appears, not
        // a broken page. Allow a future retry rather than latching a
        // permanent failure.
        socratesQuestionsRequested = false;
      });
  }

  // Real, load-bearing distinction from a generic "helpful tips" box:
  // every category and question rendered here comes verbatim from the
  // live backend response, not a hardcoded copy in this file that could
  // silently drift from app/agents/socrates_intake.py's own real
  // question set - the same "single source of truth" discipline
  // loadRedFlagTerms()/checkRedFlagHint() already hold themselves to.
  function renderSocratesQuestions(data) {
    socratesQuestionsEl.innerHTML = "";

    var questions = (data && data.questions) || [];
    if (!questions.length) {
      return;
    }

    var heading = document.createElement("p");
    heading.className = "socrates-heading";
    heading.textContent = t("socrates_heading");
    socratesQuestionsEl.appendChild(heading);

    var list = document.createElement("ul");
    questions.forEach(function (q) {
      var item = document.createElement("li");
      item.textContent = q.question;
      list.appendChild(item);
    });
    socratesQuestionsEl.appendChild(list);

    socratesQuestionsEl.hidden = false;
  }

  function checkRedFlagHint() {
    if (!redFlagTerms) {
      redflagHint.hidden = true;
      return;
    }

    var normalized = normalizeForRedFlagPreview(symptomTextEl.value);
    var matched = redFlagTerms.some(function (term) {
      return normalized.indexOf(term) !== -1;
    });

    refreshRedflagHint(matched);
  }

  function refreshRedflagHint(showHint) {
    if (showHint === undefined) {
      showHint = !redflagHint.hidden;
    }
    redflagHint.textContent = t("redflag_hint");
    redflagHint.hidden = !showHint;
  }

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
    renderAyushControl(data);
    renderAbdmControl(data);
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

  // SIH26047 Module A's AYUSH history mode extension - real, tested
  // backend (GET /ayush/kiosk-questions, POST /cases/{id}/ayush, see
  // app/agents/ayush_mode.py and app/main.py) that had no UI path at
  // all until now. Opt-in per case, matching the PS's own "for
  // Ayurvedic OPDs" framing - never a field every patient answers.
  // English-only for now, a real, named scope limit rather than a full
  // i18n.js integration - this is a self-contained addition, not yet
  // wired through the rest of this file's translation system.
  function renderAyushControl(data) {
    var existing = document.getElementById("ayush-control");
    if (existing) {
      existing.parentNode.removeChild(existing);
    }
    if (!data.case_id) {
      return;
    }

    var anchor = document.getElementById("audio-summary-control") || reviewNote;
    var wrap = document.createElement("div");
    wrap.id = "ayush-control";
    wrap.className = "ayush-control";

    if (data.ayush_assessment) {
      var recorded = document.createElement("p");
      recorded.className = "ayush-recorded-note";
      recorded.textContent = t("ayush_recorded_note");
      wrap.appendChild(recorded);
      anchor.parentNode.insertBefore(wrap, anchor.nextSibling);
      return;
    }

    var toggleBtn = document.createElement("button");
    toggleBtn.type = "button";
    toggleBtn.className = "ayush-toggle-btn";
    toggleBtn.textContent = t("ayush_toggle_label");

    var formHost = document.createElement("div");
    formHost.className = "ayush-form-host panel-enter";
    formHost.hidden = true;

    toggleBtn.addEventListener("click", function () {
      if (!formHost.hidden) {
        formHost.hidden = true;
        return;
      }
      toggleBtn.disabled = true;
      fetch("/ayush/kiosk-questions")
        .then(function (response) {
          if (!response.ok) {
            throw new Error("kiosk-questions request failed: " + response.status);
          }
          return response.json();
        })
        .then(function (questions) {
          buildAyushForm(formHost, questions, data.case_id);
          formHost.hidden = false;
          toggleBtn.disabled = false;
        })
        .catch(function () {
          toggleBtn.disabled = false;
          showError(t("ayush_load_error"));
        });
    });

    wrap.appendChild(toggleBtn);
    wrap.appendChild(formHost);
    anchor.parentNode.insertBefore(wrap, anchor.nextSibling);
  }

  // A real, load-bearing distinction, not a UI nicety: only the seven
  // parameters app/agents/ayush_mode.py's kiosk_askable_parameters()
  // actually returns get a text field here. Sara, Samhanana, and
  // Pramana (physician_only) are rendered as a labeled, explained list
  // instead - this function has no way to accidentally ask a patient
  // to self-rate their own tissue quality, because that data never
  // reaches it in the first place.
  function buildAyushForm(host, questions, caseId) {
    host.innerHTML = "";

    var fieldByName = {
      Prakriti: "prakriti",
      Vikriti: "vikriti",
      Satmya: "satmya",
      Sattva: "sattva",
      "Ahara Shakti": "ahara_shakti",
      "Vyayama Shakti": "vyayama_shakti",
      Vaya: "vaya"
    };

    var intro = document.createElement("p");
    intro.className = "ayush-intro";
    intro.textContent = t("ayush_intro");
    host.appendChild(intro);

    var inputsByField = {};
    (questions.kiosk_askable || []).forEach(function (question) {
      var field = fieldByName[question.name];
      if (!field) {
        return;
      }

      var label = document.createElement("label");
      label.className = "ayush-field-label";
      label.textContent = question.name + " — " + question.gloss;

      var input = document.createElement("input");
      input.type = "text";
      input.className = "ayush-field-input";
      label.appendChild(input);

      host.appendChild(label);
      inputsByField[field] = input;
    });

    if (questions.physician_only && questions.physician_only.length) {
      var deferredNote = document.createElement("div");
      deferredNote.className = "ayush-deferred-note";

      var heading = document.createElement("strong");
      heading.textContent = t("ayush_deferred_heading");
      deferredNote.appendChild(heading);

      var list = document.createElement("ul");
      questions.physician_only.forEach(function (question) {
        var item = document.createElement("li");
        item.textContent = question.name + " — " + question.reason;
        list.appendChild(item);
      });
      deferredNote.appendChild(list);
      host.appendChild(deferredNote);
    }

    var submitBtn = document.createElement("button");
    submitBtn.type = "button";
    submitBtn.className = "ayush-submit-btn";
    submitBtn.textContent = t("ayush_submit_label");
    submitBtn.addEventListener("click", function () {
      var body = {};
      Object.keys(inputsByField).forEach(function (field) {
        var value = inputsByField[field].value.trim();
        if (value) {
          body[field] = value;
        }
      });

      submitBtn.disabled = true;
      fetch("/cases/" + encodeURIComponent(caseId) + "/ayush", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      })
        .then(function (response) {
          if (!response.ok) {
            throw new Error("ayush save failed: " + response.status);
          }
          return response.json();
        })
        .then(function (updated) {
          renderAyushControl(updated);
        })
        .catch(function () {
          submitBtn.disabled = false;
          showError(t("ayush_save_error"));
        });
    });
    host.appendChild(submitBtn);
  }

  // SIH26047 Module D / patient-journey Step 1 ("Identify: Patient...
  // enters/scans ABHA ID or Aadhaar details") - app/adapters/abdm.py's
  // real M1 ABHA-enrollment adapter (RSA-OAEP encryption, 18 backend
  // tests) and its two endpoints (POST /abdm/enroll/request-otp,
  // POST /abdm/enroll/verify-otp) existed with zero UI path until now -
  // the exact same "real backend, invisible to a live demo" gap AYUSH
  // mode and SOCRATES questions both had before this session closed
  // them. English-only for now, same named scope limit as the AYUSH
  // panel above.
  //
  // Honest by design, not just by accident: a 503 here (this
  // environment has no live ABDM_CLIENT_ID/ABDM_CLIENT_SECRET, so every
  // real attempt in this environment WILL 503) is shown as a plain,
  // expected statement of fact, not a scary generic error - the same
  // honesty standard app/adapters/abdm.py's own module docstring holds
  // itself to.
  function renderAbdmControl(data) {
    var existing = document.getElementById("abdm-control");
    if (existing) {
      existing.parentNode.removeChild(existing);
    }
    if (!data.case_id) {
      return;
    }

    var anchor = document.getElementById("ayush-control") || document.getElementById("audio-summary-control") || reviewNote;
    var wrap = document.createElement("div");
    wrap.id = "abdm-control";
    wrap.className = "abdm-control";

    var toggleBtn = document.createElement("button");
    toggleBtn.type = "button";
    toggleBtn.className = "abdm-toggle-btn";
    toggleBtn.textContent = t("abdm_toggle_label");

    var formHost = document.createElement("div");
    formHost.className = "abdm-form-host panel-enter";
    formHost.hidden = true;

    toggleBtn.addEventListener("click", function () {
      formHost.hidden = !formHost.hidden;
      if (!formHost.hidden && !formHost.childNodes.length) {
        buildAbdmRequestOtpForm(formHost);
      }
    });

    wrap.appendChild(toggleBtn);
    wrap.appendChild(formHost);
    anchor.parentNode.insertBefore(wrap, anchor.nextSibling);
  }

  // Step 1 of the real two-step ABHA enrollment flow: Aadhaar/mobile
  // number in, an OTP sent to the patient's phone by the real ABDM
  // sandbox (or a clean, honest 503 in this environment, which has no
  // live credentials).
  function buildAbdmRequestOtpForm(host) {
    host.innerHTML = "";

    var intro = document.createElement("p");
    intro.className = "abdm-intro";
    intro.textContent = t("abdm_request_intro");
    host.appendChild(intro);

    var input = document.createElement("input");
    input.type = "text";
    input.className = "abdm-field-input";
    input.placeholder = t("abdm_identifier_placeholder");
    host.appendChild(input);

    var statusNote = document.createElement("p");
    statusNote.className = "abdm-status-note";
    statusNote.hidden = true;
    host.appendChild(statusNote);

    var submitBtn = document.createElement("button");
    submitBtn.type = "button";
    submitBtn.className = "abdm-submit-btn";
    submitBtn.textContent = t("abdm_send_otp_label");
    submitBtn.addEventListener("click", function () {
      var identifier = input.value.trim();
      if (identifier.length < 3) {
        statusNote.hidden = false;
        statusNote.className = "abdm-status-note abdm-status-error";
        statusNote.textContent = t("abdm_identifier_invalid");
        return;
      }

      submitBtn.disabled = true;
      fetch("/abdm/enroll/request-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifier: identifier })
      })
        .then(function (response) {
          return response.json().then(function (body) {
            return { ok: response.ok, status: response.status, body: body };
          });
        })
        .then(function (result) {
          submitBtn.disabled = false;
          if (!result.ok) {
            statusNote.hidden = false;
            statusNote.className = "abdm-status-note abdm-status-info";
            // A 503 here is the honest, expected state in an environment
            // with no live ABDM sandbox credentials - stated plainly,
            // not disguised as a generic failure.
            statusNote.textContent =
              result.status === 503
                ? t("abdm_not_configured_note")
                : t("abdm_request_otp_error_prefix") + (result.body && result.body.detail ? result.body.detail : "unknown error");
            return;
          }
          buildAbdmVerifyOtpForm(host, result.body.transaction_id);
        })
        .catch(function () {
          submitBtn.disabled = false;
          statusNote.hidden = false;
          statusNote.className = "abdm-status-note abdm-status-error";
          statusNote.textContent = t("abdm_request_unreachable");
        });
    });
    host.appendChild(submitBtn);
  }

  // Step 2: the transaction ID from step 1 (kept only in this closure,
  // never shown to the patient - it's an internal handle, not something
  // meaningful to them) plus the OTP they actually received.
  function buildAbdmVerifyOtpForm(host, transactionId) {
    host.innerHTML = "";
    retriggerEnterAnimation(host);

    var intro = document.createElement("p");
    intro.className = "abdm-intro";
    intro.textContent = t("abdm_verify_intro");
    host.appendChild(intro);

    var input = document.createElement("input");
    input.type = "text";
    input.className = "abdm-field-input";
    input.placeholder = t("abdm_otp_placeholder");
    host.appendChild(input);

    var statusNote = document.createElement("p");
    statusNote.className = "abdm-status-note";
    statusNote.hidden = true;
    host.appendChild(statusNote);

    var submitBtn = document.createElement("button");
    submitBtn.type = "button";
    submitBtn.className = "abdm-submit-btn";
    submitBtn.textContent = t("abdm_verify_otp_label");
    submitBtn.addEventListener("click", function () {
      var otp = input.value.trim();
      if (!otp) {
        statusNote.hidden = false;
        statusNote.className = "abdm-status-note abdm-status-error";
        statusNote.textContent = t("abdm_otp_empty");
        return;
      }

      submitBtn.disabled = true;
      fetch("/abdm/enroll/verify-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transaction_id: transactionId, otp: otp })
      })
        .then(function (response) {
          return response.json().then(function (body) {
            return { ok: response.ok, status: response.status, body: body };
          });
        })
        .then(function (result) {
          submitBtn.disabled = false;
          if (!result.ok) {
            statusNote.hidden = false;
            statusNote.className = "abdm-status-note abdm-status-info";
            statusNote.textContent =
              result.status === 503
                ? t("abdm_not_configured_note")
                : t("abdm_verify_otp_error_prefix") + (result.body && result.body.detail ? result.body.detail : "unknown error");
            return;
          }
          host.innerHTML = "";
          var recorded = document.createElement("p");
          recorded.className = "abdm-recorded-note";
          recorded.textContent = t("abdm_linked_prefix") + result.body.abha_number + ".";
          host.appendChild(recorded);
        })
        .catch(function () {
          submitBtn.disabled = false;
          statusNote.hidden = false;
          statusNote.className = "abdm-status-note abdm-status-error";
          statusNote.textContent = t("abdm_verify_unreachable");
        });
    });
    host.appendChild(submitBtn);
  }

  // ---- Physician console (SIH26047 Module C: "the summary is a draft
  // to accept, amend, or reject... presented on the consultation screen
  // the moment the patient enters the room") -----------------------------
  //
  // Reads/writes the exact same persisted cases the patient view creates,
  // through the real backend (GET /cases, GET /cases/{id},
  // POST /cases/{id}/review) - a second view of one dataset, not a demo
  // fixture of its own.

  function handleViewButtonClick(event) {
    var view = event.currentTarget.getAttribute("data-view");
    showView(view);
  }

  function showView(view) {
    currentView = view;
    patientViewEl.hidden = view !== "patient";
    physicianViewEl.hidden = view !== "physician";

    for (var i = 0; i < viewButtons.length; i++) {
      var isActive = viewButtons[i].getAttribute("data-view") === view;
      viewButtons[i].setAttribute("aria-pressed", isActive ? "true" : "false");
      viewButtons[i].classList.toggle("is-active", isActive);
    }

    if (view === "physician") {
      loadPhysicianCases();
    }
  }

  function buildPriorityBadge(priority) {
    var badge = document.createElement("span");
    badge.className = "priority-badge";
    if (priority && PRIORITY_KEYS.indexOf(priority) !== -1) {
      badge.classList.add("priority-" + priority);
      badge.textContent = t("priority_" + priority);
    } else {
      badge.textContent = t("priority_unknown_prefix") + (priority || "unknown");
    }
    return badge;
  }

  function loadPhysicianCases() {
    physicianCaseListError.hidden = true;
    var ayushOnly = physicianAyushFilter.checked;

    fetch("/cases?ayush_only=" + (ayushOnly ? "true" : "false"))
      .then(function (response) {
        if (!response.ok) {
          throw new Error("cases request failed: " + response.status);
        }
        return response.json();
      })
      .then(renderPhysicianCaseList)
      .catch(function () {
        physicianCaseListEl.innerHTML = "";
        physicianCaseListEmpty.hidden = true;
        physicianCaseListError.hidden = false;
      });
  }

  function renderPhysicianCaseList(cases) {
    physicianCaseListEl.innerHTML = "";
    physicianCaseListEmpty.hidden = cases.length !== 0;

    cases.forEach(function (summary) {
      var item = document.createElement("li");
      item.className = "physician-case-item";
      if (physicianLastCaseDetail && physicianLastCaseDetail.case_id === summary.case_id) {
        item.classList.add("is-selected");
      }

      var button = document.createElement("button");
      button.type = "button";
      button.className = "physician-case-item-btn";
      if (summary.priority_level && PRIORITY_KEYS.indexOf(summary.priority_level) !== -1) {
        button.classList.add("priority-" + summary.priority_level);
      }

      var complaint = document.createElement("span");
      complaint.className = "physician-case-item-complaint";
      complaint.textContent = summary.chief_complaint;
      button.appendChild(complaint);

      var meta = document.createElement("span");
      meta.className = "physician-case-item-meta";
      meta.appendChild(buildPriorityBadge(summary.priority_level));

      var statusBadge = document.createElement("span");
      statusBadge.className = "physician-status-badge " + (summary.is_reviewed_by_physician ? "is-reviewed" : "is-draft");
      statusBadge.textContent = summary.is_reviewed_by_physician ? t("physician_status_reviewed") : t("physician_status_draft");
      meta.appendChild(statusBadge);

      button.appendChild(meta);
      button.addEventListener("click", function () {
        selectPhysicianCase(summary.case_id);
      });

      item.appendChild(button);
      physicianCaseListEl.appendChild(item);
    });
  }

  function selectPhysicianCase(caseId) {
    physicianCaseDetailEl.innerHTML = "";
    var loading = document.createElement("p");
    loading.className = "physician-case-detail-placeholder";
    loading.textContent = t("physician_loading_case");
    physicianCaseDetailEl.appendChild(loading);

    fetch("/cases/" + encodeURIComponent(caseId))
      .then(function (response) {
        if (!response.ok) {
          throw new Error("case fetch failed: " + response.status);
        }
        return response.json();
      })
      .then(function (data) {
        physicianLastCaseDetail = data;
        renderPhysicianCaseDetail(data);
        // Refresh the list purely to move the selection highlight - the
        // list itself hasn't changed just by viewing a case.
        loadPhysicianCases();
      })
      .catch(function () {
        physicianCaseDetailEl.innerHTML = "";
        var error = document.createElement("p");
        error.className = "physician-case-detail-error";
        error.textContent = t("physician_case_load_error");
        physicianCaseDetailEl.appendChild(error);
      });
  }

  function renderPhysicianCaseDetail(data, options) {
    var justConfirmed = Boolean(options && options.justConfirmed);

    physicianCaseDetailEl.innerHTML = "";
    retriggerEnterAnimation(physicianCaseDetailEl);

    var header = document.createElement("div");
    header.className = "physician-case-detail-header";
    header.appendChild(buildPriorityBadge(data.priority_level));
    var statusBadge = document.createElement("span");
    statusBadge.className = "physician-status-badge " + (data.is_reviewed_by_physician ? "is-reviewed" : "is-draft");
    if (justConfirmed) {
      statusBadge.classList.add("just-confirmed");
    }
    statusBadge.textContent = data.is_reviewed_by_physician ? t("physician_status_reviewed") : t("physician_status_draft");
    header.appendChild(statusBadge);
    physicianCaseDetailEl.appendChild(header);

    var reviewFormEl = document.createElement("div");
    reviewFormEl.className = "physician-review-form";

    var fieldInputs = {};
    FIELD_LABELS.forEach(function (pair) {
      var field = pair[0];
      var labelKey = pair[1];

      var label = document.createElement("label");
      label.className = "physician-field-label";
      label.textContent = t(labelKey);

      var textarea = document.createElement("textarea");
      textarea.className = "physician-field-input";
      textarea.rows = field === "chief_complaint" ? 2 : 3;
      textarea.value = data[field] || "";
      label.appendChild(textarea);

      reviewFormEl.appendChild(label);
      fieldInputs[field] = textarea;
    });
    physicianCaseDetailEl.appendChild(reviewFormEl);

    if (data.ayush_assessment) {
      physicianCaseDetailEl.appendChild(buildPhysicianAyushSummary(data.ayush_assessment));
    }

    var physicianReviewNoteEl = document.createElement("p");
    physicianReviewNoteEl.className = "physician-review-note";
    physicianReviewNoteEl.hidden = true;
    physicianCaseDetailEl.appendChild(physicianReviewNoteEl);

    var confirmBtn = document.createElement("button");
    confirmBtn.type = "button";
    confirmBtn.className = "physician-confirm-btn";
    confirmBtn.textContent = data.is_reviewed_by_physician ? t("physician_confirm_amend_label") : t("physician_confirm_label");
    confirmBtn.addEventListener("click", function () {
      var updates = {};
      FIELD_LABELS.forEach(function (pair) {
        var field = pair[0];
        var value = fieldInputs[field].value.trim();
        if (value) {
          updates[field] = value;
        }
      });

      confirmBtn.disabled = true;
      fetch("/cases/" + encodeURIComponent(data.case_id) + "/review", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates)
      })
        .then(function (response) {
          if (!response.ok) {
            throw new Error("review failed: " + response.status);
          }
          return response.json();
        })
        .then(function (updated) {
          physicianLastCaseDetail = updated;
          renderPhysicianCaseDetail(updated, { justConfirmed: true });
          loadPhysicianCases();
        })
        .catch(function () {
          confirmBtn.disabled = false;
          physicianReviewNoteEl.hidden = false;
          physicianReviewNoteEl.className = "physician-review-note physician-review-error";
          physicianReviewNoteEl.textContent = t("physician_review_error");
        });
    });
    physicianCaseDetailEl.appendChild(confirmBtn);
  }

  // Read-only: the same kiosk_askable/physician_only split
  // renderAyushControl's own patient-facing form enforces, mirrored here
  // for the physician's view of an already-recorded assessment - Sara/
  // Samhanana/Pramana are exactly the three fields this consultation
  // screen is the FIRST real chance to record, so they're shown as
  // present-or-still-blank, not silently omitted.
  function buildPhysicianAyushSummary(assessment) {
    var wrap = document.createElement("div");
    wrap.className = "physician-ayush-summary";

    var heading = document.createElement("h3");
    heading.className = "physician-ayush-summary-heading";
    heading.textContent = t("physician_ayush_heading");
    wrap.appendChild(heading);

    var kioskFields = [
      ["prakriti", "Prakriti"],
      ["vikriti", "Vikriti"],
      ["satmya", "Satmya"],
      ["sattva", "Sattva"],
      ["ahara_shakti", "Ahara Shakti"],
      ["vyayama_shakti", "Vyayama Shakti"],
      ["vaya", "Vaya"]
    ];
    var physicianOnlyFields = [
      ["sara", "Sara"],
      ["samhanana", "Samhanana"],
      ["pramana", "Pramana"]
    ];

    var list = document.createElement("dl");
    list.className = "physician-ayush-summary-list";
    kioskFields.concat(physicianOnlyFields).forEach(function (pair) {
      var field = pair[0];
      var name = pair[1];
      var dt = document.createElement("dt");
      dt.textContent = name;
      var dd = document.createElement("dd");
      dd.textContent = assessment[field] || t("physician_ayush_not_recorded");
      list.appendChild(dt);
      list.appendChild(dd);
    });
    wrap.appendChild(list);

    return wrap;
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
    refreshRedflagHint();

    // Re-render an already-visible result in the new language, without
    // re-triggering the scroll-into-view a fresh submission gets.
    if (lastResultData) {
      renderResultContent(lastResultData);
    }

    // Same idea for the review-recap step: its labels come from t(),
    // not data-i18n text nodes (it's built by JS, not static markup), so
    // a language switch while step 4 is showing needs an explicit
    // re-render or its labels would silently stay in the old language.
    if (currentStep === 4) {
      renderReviewRecap();
    }

    // Physician console content is JS-built from fetched data, not
    // static data-i18n markup - same reason as the two blocks above.
    // Re-render from cache rather than a redundant GET.
    if (currentView === "physician") {
      loadPhysicianCases();
      if (physicianLastCaseDetail) {
        renderPhysicianCaseDetail(physicianLastCaseDetail);
      }
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

  // Forces a CSS animation to replay on an element that never actually
  // leaves the DOM/goes through display:none - unlike .panel-enter's
  // main use (an element toggled via `hidden`, which the browser
  // restarts automatically), content replaced in place inside an
  // always-visible host (the ABDM OTP-verify step swapping into the same
  // form host, the physician console's case detail repainting after a
  // save) needs an explicit reflow between removing and re-adding the
  // class, or the browser has no "was removed, now added" transition to
  // detect and the animation silently never plays.
  function retriggerEnterAnimation(el) {
    el.classList.remove("panel-enter");
    void el.offsetWidth;
    el.classList.add("panel-enter");
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
