// CarePilot Case Intake - vanilla JS, no framework, no build step.

(function () {
  "use strict";

  var form = document.getElementById("intake-form");
  var submitBtn = document.getElementById("submit-btn");
  var statusArea = document.getElementById("status-area");
  var resultsArea = document.getElementById("results-area");
  var resultsList = document.getElementById("results-list");
  var priorityBanner = document.getElementById("priority-banner");
  var reviewNote = document.getElementById("review-note");

  // Maps ClinicalHistorySummary field names (app/schemas.py) to
  // plain-language labels a first-time patient can read.
  var FIELD_LABELS = [
    ["chief_complaint", "Chief Complaint"],
    ["history_of_present_illness", "History of Present Illness"],
    ["past_medical_surgical_history", "Past Medical / Surgical History"],
    ["drug_allergy_history", "Drug & Allergy History"],
    ["family_history", "Family History"],
    ["personal_history", "Personal History"],
    ["review_of_systems", "Review of Systems"],
    ["prior_investigations_summary", "Prior Investigations"]
  ];

  var PRIORITY_LABELS = {
    emergency: "EMERGENCY - Seek help immediately",
    urgent: "URGENT - See a doctor very soon",
    clinic_visit: "CLINIC VISIT - Please see a doctor",
    self_care: "SELF-CARE - Manage at home, watch for changes"
  };

  form.addEventListener("submit", handleSubmit);

  function handleSubmit(event) {
    event.preventDefault();

    var symptomText = document.getElementById("symptom_text").value.trim();
    var ageRaw = document.getElementById("age").value;
    var durationRaw = document.getElementById("duration_days").value;

    clearStatus();
    hideResults();

    if (symptomText.length < 3) {
      showError("Please describe your symptoms in at least a few words before submitting.");
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
      .then(function (response) {
        return response.json().then(
          function (body) {
            return { ok: response.ok, status: response.status, body: body };
          },
          function () {
            // Response body wasn't valid JSON at all.
            return { ok: response.ok, status: response.status, body: null };
          }
        );
      })
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
        showError(
          "Could not reach the CarePilot server. Please check your connection and try again."
        );
      });
  }

  function friendlyErrorMessage(status, body) {
    var detail = extractDetail(body);

    if (status === 503) {
      return (
        "The AI assistant isn't available right now, so we can't process your case summary at " +
        "this moment. Please try again in a little while, or speak to hospital staff directly."
      );
    }

    if (status === 422) {
      return (
        "There was a problem with the information entered. " +
        (detail || "Please check your symptom description and try again.")
      );
    }

    if (status >= 500) {
      return "Something went wrong on the server. Please try again, or speak to hospital staff.";
    }

    return detail || "Something went wrong (error " + status + "). Please try again.";
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

  function renderResult(data) {
    if (!data || typeof data !== "object") {
      showError("The server returned an unexpected response. Please try again.");
      return;
    }

    resultsList.innerHTML = "";

    FIELD_LABELS.forEach(function (pair) {
      var key = pair[0];
      var label = pair[1];
      var value = data[key];

      // Skip fields that are missing, null, or empty strings rather
      // than printing "null" or a blank box.
      if (value === null || value === undefined || value === "") {
        return;
      }

      var dt = document.createElement("dt");
      dt.textContent = label;

      var dd = document.createElement("dd");
      dd.textContent = value;

      resultsList.appendChild(dt);
      resultsList.appendChild(dd);
    });

    var priority = data.priority_level;
    priorityBanner.className = "priority-banner";
    if (priority && PRIORITY_LABELS.hasOwnProperty(priority)) {
      priorityBanner.classList.add("priority-" + priority);
      priorityBanner.textContent = PRIORITY_LABELS[priority];
    } else {
      priorityBanner.textContent = "Priority level: " + (priority || "unknown");
    }

    if (data.is_reviewed_by_physician) {
      reviewNote.textContent = "This summary has been reviewed by a physician.";
    } else {
      reviewNote.textContent =
        "This is an AI-drafted summary and has not yet been reviewed by a physician. " +
        "It is meant to help a doctor, not to replace one.";
    }

    resultsArea.hidden = false;
    resultsArea.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function hideResults() {
    resultsArea.hidden = true;
    resultsList.innerHTML = "";
    priorityBanner.textContent = "";
    priorityBanner.className = "priority-banner";
    reviewNote.textContent = "";
  }

  function setLoading(isLoading) {
    submitBtn.disabled = isLoading;
    submitBtn.textContent = isLoading ? "Submitting..." : "Submit My Symptoms";
  }

  function showLoadingMessage() {
    statusArea.innerHTML = '<p class="loading">Sending your information, please wait...</p>';
  }

  function showError(message) {
    statusArea.innerHTML = '<div class="error-box"></div>';
    statusArea.querySelector(".error-box").textContent = message;
  }

  function clearStatus() {
    statusArea.innerHTML = "";
  }
})();
