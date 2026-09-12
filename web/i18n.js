// CarePilot / Inayat UI translations - English, Hindi, Telugu.
//
// This file covers ONLY the visible page chrome (labels, buttons, hero
// copy, status/error messages, the FIELD_LABELS/PRIORITY_LABELS tables
// app.js renders with) - it is completely independent of the Bhashini
// voice pipeline (app/adapters/bhashini.py), which already accepts
// spoken Telugu/Hindi input server-side regardless of which UI language
// is active here. Loaded before app.js; exposes a small API on
// window.CarePilotI18n rather than a framework i18n library, to keep
// this project's own no-build-step/no-framework rule intact.
//
// Translation confidence note (read before trusting hi/te blindly):
// Every string below was translated with real attention to natural,
// correct phrasing, not run through machine translation. Confidence is
// high for the short, fixed-form UI labels (buttons, field labels,
// priority labels) - these map to standard, common terms. Confidence is
// slightly lower for two specific things, called out again in the
// project report: (1) "Review of Systems" (field_ros) has no single
// universally-standardized Hindi/Telugu clinical-teaching term - the
// phrases used here are accurate but a native clinician may prefer a
// different rendering; (2) the longer free-form sentences (hero_body,
// notice, some error strings) are correct Hindi/Telugu but, being
// original prose rather than fixed short labels, would still benefit
// from a native-speaker proofread before this becomes patient-facing in
// a real deployment, not just a hackathon demo.
(function (global) {
  "use strict";

  var STORAGE_KEY = "carepilot.lang";
  var DEFAULT_LANG = "en";
  var SUPPORTED = ["en", "hi", "te"];

  var STRINGS = {

    // ---------------------------------------------------------------
    // English (source of truth for meaning/order; everything below is
    // translated from this).
    // ---------------------------------------------------------------
    en: {
      brand_tagline: "AI-Assisted Case Intake · SIH26047 demo",

      hero_eyebrow: "Built for India’s 2–5 minute OPD consult",
      hero_title: "Your doctor gets minutes. Don’t spend them repeating yourself.",
      hero_body: "Inayat turns what you share before your visit into a clear, organized summary your doctor can read in seconds — instead of asking the same questions again in a room with almost no time to spare. Type, speak, or show us a photo of a prior prescription or report — whatever's easiest for you.",

      live_demo_label: "Watch it catch a real emergency — live, before you click anything",
      live_demo_result_note: "Caught instantly by the same deterministic safety scanner every real submission runs through — no AI call needed, works even offline.",
      live_demo_try_button: "Try it yourself →",

      hero_stat_num_1: "70–80%",
      hero_stat_label_1: "of correct diagnoses come from a good history alone, before any exam or test",
      hero_stat_num_2: "~2 min",
      hero_stat_label_2: "is the average Indian primary-care consultation — among the shortest of 67 countries studied",
      hero_stat_source: "Sources: classical clinical-history teaching; BMJ Open, 2017 (67-country consultation-length study). See docs/sih/ for the full citation.",
      method_type_label: "Type",
      method_speak_label: "Speak",
      method_photo_label: "Photograph",

      emergency_bar_label: "If this is an emergency:",
      emergency_bar_cta: "Call 108 now",
      emergency_bar_note: "Free · 24×7 · National Ambulance",

      notice: "This is a demo of the case-intake step only. It helps write down your symptoms in an organized way for a doctor to review — it does not diagnose you and it is not a substitute for seeing a doctor. If this is an emergency, call 108 or go to the nearest hospital right now.",

      sidebar_title: "How Inayat works",
      sidebar_step1: "Describe your symptoms — by typing, speaking, or a photo",
      sidebar_step2: "Our AI drafts a clear, structured summary",
      sidebar_step3: "Your doctor reviews it before any decision is made",
      sidebar_privacy_note: "Your answers are used only to prepare this summary for your visit.",

      safety_metrics_title: "Measured Safety Performance",
      safety_metrics_recall_label: "emergency recall",
      safety_metrics_accuracy_label: "overall accuracy",
      safety_metrics_na: "N/A",
      safety_metrics_evaluated_prefix: "Evaluated live: ",
      safety_metrics_of_total_mid: " of ",
      safety_metrics_cases_suffix: " test cases. ",
      safety_metrics_skipped_suffix: " could not be evaluated — no live AI key is configured in this demo.",
      safety_metrics_toggle_show: "Show full case-by-case evidence",
      safety_metrics_toggle_hide: "Hide full case-by-case evidence",
      safety_metrics_col_case: "Case",
      safety_metrics_col_expected: "Expected",
      safety_metrics_col_actual: "Actual",
      safety_metrics_col_result: "Result",
      safety_metrics_row_skipped: "Skipped",
      safety_metrics_row_pass: "Pass",
      safety_metrics_row_fail: "Fail",
      safety_metrics_false_negatives_prefix: "⚠ Missed emergency case(s) in this test set: ",
      safety_metrics_honesty_note: "Measured against an 11-case, author-labeled test set — a real computation, not a marketing claim, but not a substitute for clinical validation on real patient data.",

      lang_toggle_aria: "Choose language",

      field_symptom_label: "Describe how you are feeling, in your own words",
      field_symptom_placeholder: "For example: I have had a fever and a bad cough for three days, and my chest hurts when I breathe.",
      field_age_label: "Your age (optional)",
      field_age_placeholder: "e.g. 65",
      field_duration_label: "How many days? (optional)",
      field_duration_placeholder: "e.g. 3",

      mic_button_idle: "Record symptoms",
      mic_button_recording: "Stop recording",
      mic_hint_idle: "Tap to speak instead of typing",
      recording_live_label: "Recording",
      recording_processing: "Processing your recording…",
      voice_shortcut_note: "Recording sends your symptoms right away — you won't need to go through the rest of these steps.",

      consent_checkbox_label: "I agree that this information will be recorded and shared with my treating doctor for this visit, in line with India's Digital Personal Data Protection Act, 2023.",

      redflag_hint: "⚠ This may need urgent attention. Keep going — you'll get a clear answer as soon as you submit, and you can always call 108 now if you're worried.",

      // AYUSH mode, SOCRATES questions, and ABDM enrollment panels
      // (all added 11-12 Sep 2026) - the static UI chrome for all three
      // is covered here. The DYNAMIC content that comes back from the
      // live backend (each Dashavidha Pariksha parameter's gloss/reason
      // text from GET /ayush/kiosk-questions, and every SOCRATES
      // question's text from POST /socrates-questions) stays English-
      // only - a real, named scope limit, not an oversight: those
      // strings are generated server-side in app/agents/ayush_mode.py
      // and app/agents/socrates_intake.py, not this file, so
      // translating them would need the backend itself to serve a
      // language-aware response, which it doesn't yet. web/app.js's own
      // comments on renderAyushControl/renderSocratesQuestions/
      // renderAbdmControl name this same limit.
      socrates_heading: "A doctor would likely also ask:",

      view_toggle_aria: "Switch between patient and physician view",
      view_patient_label: "Patient",
      view_physician_label: "Physician console",
      physician_console_heading: "Physician Console",
      physician_console_intro: "Every case a patient has completed intake for, most recent first. Open one to review the AI-drafted summary before consultation.",
      physician_ayush_filter_label: "Ayurvedic (AYUSH) cases only",
      physician_no_cases: "No cases yet.",
      physician_load_error: "Could not load the case list.",
      physician_select_case_prompt: "Select a case from the list to review it.",
      physician_status_reviewed: "Reviewed",
      physician_status_draft: "Draft",
      physician_loading_case: "Loading case…",
      physician_case_load_error: "Could not load this case.",
      physician_confirm_label: "Accept summary",
      physician_confirm_amend_label: "Save changes",
      physician_review_error: "Could not save your review. Please try again.",
      physician_ayush_heading: "Dashavidha Pariksha (AYUSH history)",
      physician_ayush_not_recorded: "not recorded",
      physician_login_heading: "Physician sign-in",
      physician_login_intro: "This console shows real patient clinical histories — enter the staff passcode to continue.",
      physician_passcode_label: "Staff passcode",
      physician_login_submit_label: "Sign in",
      physician_login_not_configured: "The physician console passcode isn't configured in this environment — this is the real, honest state, not a bug.",
      physician_login_incorrect_passcode: "Incorrect passcode.",
      physician_login_unreachable: "Could not reach the sign-in endpoint.",
      physician_logout_label: "Sign out",

      ayush_toggle_label: "This is an Ayurvedic OPD visit — add AYUSH history",
      ayush_intro: "Dashavidha Pariksha — answer what you can; each question is something only you know.",
      ayush_deferred_heading: "Assessed by the physician at consultation, not asked here:",
      ayush_submit_label: "Save Ayurvedic history",
      ayush_recorded_note: "Ayurvedic (AYUSH) history recorded for this case.",
      ayush_load_error: "Could not load the AYUSH question list.",
      ayush_save_error: "Could not save the AYUSH history.",

      abdm_toggle_label: "Link this visit to your ABHA (Ayushman Bharat Health Account) ID",
      abdm_request_intro: "Enter your Aadhaar or mobile number to link this visit to your ABHA record.",
      abdm_identifier_placeholder: "Aadhaar or mobile number",
      abdm_identifier_invalid: "Enter a valid Aadhaar or mobile number.",
      abdm_send_otp_label: "Send OTP",
      abdm_not_configured_note: "ABDM sandbox isn't configured in this environment (no live credentials) — this is the real, honest state, not a bug.",
      abdm_request_otp_error_prefix: "Could not request an OTP: ",
      abdm_request_unreachable: "Could not reach the ABDM enrollment endpoint.",
      abdm_verify_intro: "Enter the OTP sent to your phone.",
      abdm_otp_placeholder: "6-digit OTP",
      abdm_otp_empty: "Enter the OTP you received.",
      abdm_verify_otp_label: "Verify OTP",
      abdm_verify_otp_error_prefix: "Could not verify the OTP: ",
      abdm_verify_unreachable: "Could not reach the ABDM verification endpoint.",
      abdm_linked_prefix: "Linked to ABHA number ",

      step1_label: "Symptoms",
      step2_label: "Photo",
      step3_label: "Details",
      step4_label: "Review",
      step_next_label: "Next",
      step_back_label: "Back",
      step2_intro: "Have a prior prescription or lab report? Add a photo (optional).",
      step_review_heading: "Review before you submit",
      review_recap_symptoms: "Symptoms",
      review_recap_age: "Age",
      review_recap_duration: "Days",
      review_recap_document: "Photo",
      review_recap_not_provided: "Not provided",
      review_recap_no_document: "No photo added",

      document_button_label: "Add a photo of a prescription or report",
      document_hint: "Optional — JPG or PNG",
      document_change_label: "Change photo",
      document_remove_label: "Remove photo",
      document_remove_aria: "Remove selected photo",
      document_filename_prefix: "Selected: ",

      submit_label: "Submit My Symptoms",
      submit_loading: "Submitting…",
      submit_loading_document: "Reading your photo and submitting…",
      submission_complete_note: "Your symptoms have been submitted — see the summary alongside for what happens next.",
      submission_complete_button: "Submit another case",

      results_heading: "Your Case Summary",

      field_chief_complaint: "Chief Complaint",
      field_hpi: "History of Present Illness",
      field_past_history: "Past Medical / Surgical History",
      field_drug_allergy: "Drug & Allergy History",
      field_family_history: "Family History",
      field_personal_history: "Personal History",
      field_ros: "Review of Systems",
      field_investigations: "Prior Investigations",

      priority_emergency: "EMERGENCY — Seek help immediately",
      priority_urgent: "URGENT — See a doctor very soon",
      priority_clinic_visit: "CLINIC VISIT — Please see a doctor",
      priority_self_care: "SELF-CARE — Manage at home, watch for changes",
      priority_unknown_prefix: "Priority level: ",

      review_note_reviewed: "This summary has been reviewed by a physician.",
      review_note_unreviewed: "This is an AI-drafted summary and has not yet been reviewed by a physician. It is meant to help a doctor, not to replace one.",

      degraded_mode_note: "⚠ A doctor needs to check this case in person. Please wait to be seen — do not rely on the priority level above by itself.",
      physician_manual_triage_badge: "⚠ Needs your review — automated triage was unavailable for this case",

      listen_button_label: "🔊 Listen to summary",
      listen_loading: "Loading audio…",
      listen_error: "Couldn't load audio right now. Please try again.",

      footer_note: "Inayat demo — for evaluation purposes only. Always seek care from a qualified physician.",

      error_symptom_too_short: "Please describe your symptoms in at least a few words before submitting.",
      error_consent_required: "Please agree to the consent statement above before submitting.",
      error_network: "Could not reach the CarePilot server. Please check your connection and try again.",
      error_backend_unavailable: "The AI assistant isn't available right now, so we can't process your case summary at this moment. Please try again in a little while, or speak to hospital staff directly.",
      error_422_prefix: "There was a problem with the information entered. ",
      error_422_fallback: "Please check your symptom description and try again.",
      error_server_generic: "Something went wrong on the server. Please try again, or speak to hospital staff.",
      error_generic_prefix: "Something went wrong (error ",
      error_generic_suffix: "). Please try again.",
      error_unexpected_response: "The server returned an unexpected response. Please try again.",

      error_mic_permission_denied: "We couldn't access your microphone. Please allow microphone access in your browser's settings and try again, or type your symptoms instead.",
      error_mic_not_found: "No microphone was found on this device. Please type your symptoms instead.",
      error_mic_unsupported: "Voice recording isn't supported in this browser. Please type your symptoms instead.",
      error_mic_generic: "Something went wrong while recording. Please try again, or type your symptoms instead.",
      error_recording_too_short: "That recording was too short or unclear to use. Please try again and speak for a few seconds.",

      error_document_unreadable: "We couldn't read that photo clearly. Please try a clearer, well-lit photo of the prescription or report (JPG or PNG), or submit without a photo.",
      error_document_too_large: "That photo is too large to upload. Please choose a smaller photo or take a new one at a lower resolution.",
      error_document_invalid_type: "Please choose an image file (JPG or PNG).",

      status_sending: "Sending your information, please wait..."
    },

    // ---------------------------------------------------------------
    // Hindi
    // ---------------------------------------------------------------
    hi: {
      brand_tagline: "एआई-सहायता प्राप्त केस इनटेक · SIH26047 डेमो",

      hero_eyebrow: "भारत के 2–5 मिनट के ओपीडी परामर्श के लिए बनाया गया",
      hero_title: "आपके डॉक्टर के पास बस कुछ मिनट होते हैं। उन्हें वही बात दोहराने में न गंवाएं।",
      hero_body: "Inayat आपकी मुलाक़ात से पहले आपकी बात को एक स्पष्ट, व्यवस्थित सारांश में बदल देता है, जिसे डॉक्टर कुछ ही सेकंड में पढ़ सकें — न कि लगभग बिना समय वाले कमरे में वही सवाल दोबारा पूछें। टाइप करें, बोलें, या पुराने पर्चे या रिपोर्ट की फोटो दिखाएं — जो भी आपके लिए आसान हो।",

      live_demo_label: "इसे एक वास्तविक आपातकाल पकड़ते हुए देखें — लाइव, बिना कुछ क्लिक किए",
      live_demo_result_note: "हर वास्तविक सबमिशन जिस निर्धारक सुरक्षा स्कैनर से गुजरता है, उसी से तुरंत पकड़ा गया — किसी एआई कॉल की ज़रूरत नहीं, ऑफ़लाइन भी काम करता है।",
      live_demo_try_button: "इसे स्वयं आज़माएं →",

      hero_stat_num_1: "70–80%",
      hero_stat_label_1: "सही निदान अकेले एक अच्छे इतिहास से ही मिल जाता है, किसी जांच या टेस्ट से पहले",
      hero_stat_num_2: "~2 मिनट",
      hero_stat_label_2: "भारत में औसत प्राथमिक स्वास्थ्य परामर्श की अवधि है — अध्ययन किए गए 67 देशों में सबसे कम में से एक",
      hero_stat_source: "स्रोत: पारंपरिक नैदानिक इतिहास-लेखन शिक्षण; BMJ Open, 2017 (67 देशों का परामर्श-अवधि अध्ययन)। पूर्ण उद्धरण के लिए docs/sih/ देखें।",
      method_type_label: "टाइप करें",
      method_speak_label: "बोलें",
      method_photo_label: "फोटो लें",

      emergency_bar_label: "यदि यह एक आपातकालीन स्थिति है:",
      emergency_bar_cta: "अभी 108 पर कॉल करें",
      emergency_bar_note: "निःशुल्क · 24×7 · राष्ट्रीय एम्बुलेंस",

      notice: "यह केवल लक्षण दर्ज करने के चरण का एक डेमो है। यह डॉक्टर की समीक्षा के लिए आपके लक्षणों को व्यवस्थित तरीके से लिखने में मदद करता है — यह आपका निदान नहीं करता और डॉक्टर से मिलने का विकल्प नहीं है। यदि यह एक आपातकालीन स्थिति है, तो 108 पर कॉल करें या नज़दीकी अस्पताल जाएं।",

      sidebar_title: "Inayat कैसे काम करता है",
      sidebar_step1: "अपने लक्षण बताएं — टाइप करके, बोलकर, या फोटो से",
      sidebar_step2: "हमारा एआई एक स्पष्ट, व्यवस्थित सारांश तैयार करता है",
      sidebar_step3: "कोई भी निर्णय लेने से पहले आपका डॉक्टर इसकी समीक्षा करता है",
      sidebar_privacy_note: "आपके उत्तर केवल इस सारांश को तैयार करने के लिए उपयोग किए जाते हैं।",

      safety_metrics_title: "मापी गई सुरक्षा निष्पादन",
      safety_metrics_recall_label: "इमरजेंसी रिकॉल",
      safety_metrics_accuracy_label: "समग्र सटीकता",
      safety_metrics_na: "लागू नहीं",
      safety_metrics_evaluated_prefix: "लाइव मूल्यांकन किया गया: ",
      safety_metrics_of_total_mid: " में से ",
      safety_metrics_cases_suffix: " परीक्षण मामले। ",
      safety_metrics_skipped_suffix: " का मूल्यांकन नहीं किया जा सका — इस डेमो में कोई लाइव एआई कुंजी कॉन्फ़िगर नहीं है।",
      safety_metrics_toggle_show: "प्रत्येक मामले का पूरा विवरण दिखाएं",
      safety_metrics_toggle_hide: "प्रत्येक मामले का पूरा विवरण छिपाएं",
      safety_metrics_col_case: "मामला",
      safety_metrics_col_expected: "अपेक्षित",
      safety_metrics_col_actual: "वास्तविक",
      safety_metrics_col_result: "परिणाम",
      safety_metrics_row_skipped: "छोड़ा गया",
      safety_metrics_row_pass: "सही",
      safety_metrics_row_fail: "गलत",
      safety_metrics_false_negatives_prefix: "⚠ इस परीक्षण सेट में छूटे हुए आपातकालीन मामले: ",
      safety_metrics_honesty_note: "11 मामलों के, लेखक-लेबल किए गए परीक्षण सेट पर मापा गया — एक वास्तविक गणना, विपणन दावा नहीं, लेकिन वास्तविक रोगी डेटा पर नैदानिक सत्यापन का विकल्प नहीं।",

      lang_toggle_aria: "भाषा चुनें",

      field_symptom_label: "आप कैसा महसूस कर रहे हैं, अपने शब्दों में बताएं",
      field_symptom_placeholder: "उदाहरण के लिए: मुझे तीन दिन से बुखार और तेज़ खांसी है, और सांस लेते समय सीने में दर्द होता है।",
      field_age_label: "आपकी उम्र (वैकल्पिक)",
      field_age_placeholder: "जैसे 65",
      field_duration_label: "कितने दिनों से? (वैकल्पिक)",
      field_duration_placeholder: "जैसे 3",

      mic_button_idle: "लक्षण रिकॉर्ड करें",
      mic_button_recording: "रिकॉर्डिंग रोकें",
      mic_hint_idle: "टाइप करने के बजाय बोलने के लिए टैप करें",
      recording_live_label: "रिकॉर्डिंग हो रही है",
      recording_processing: "आपकी रिकॉर्डिंग प्रोसेस हो रही है…",
      voice_shortcut_note: "रिकॉर्डिंग आपके लक्षण तुरंत भेज देती है — बाकी चरणों से गुजरने की ज़रूरत नहीं होगी।",

      consent_checkbox_label: "मैं सहमत हूं कि यह जानकारी दर्ज की जाएगी और इस विज़िट के लिए मेरे इलाज करने वाले डॉक्टर के साथ साझा की जाएगी, भारत के डिजिटल व्यक्तिगत डेटा संरक्षण अधिनियम, 2023 के अनुसार।",

      redflag_hint: "⚠ इसे तुरंत ध्यान देने की ज़रूरत हो सकती है। जारी रखें — सबमिट करते ही आपको स्पष्ट जवाब मिलेगा, और अगर चिंता हो तो आप अभी भी 108 पर कॉल कर सकते हैं।",

      socrates_heading: "डॉक्टर संभवतः यह भी पूछेंगे:",

      view_toggle_aria: "मरीज़ और चिकित्सक दृश्य के बीच स्विच करें",
      view_patient_label: "मरीज़",
      view_physician_label: "चिकित्सक कंसोल",
      physician_console_heading: "चिकित्सक कंसोल",
      physician_console_intro: "हर वह मामला जिसके लिए मरीज़ ने इनटेक पूरा किया है, सबसे हाल का पहले। परामर्श से पहले एआई द्वारा तैयार सारांश की समीक्षा करने के लिए किसी एक को खोलें।",
      physician_ayush_filter_label: "केवल आयुर्वेदिक (आयुष) मामले",
      physician_no_cases: "अभी तक कोई मामला नहीं।",
      physician_load_error: "मामलों की सूची लोड नहीं हो सकी।",
      physician_select_case_prompt: "समीक्षा के लिए सूची से एक मामला चुनें।",
      physician_status_reviewed: "समीक्षित",
      physician_status_draft: "मसौदा",
      physician_loading_case: "मामला लोड हो रहा है…",
      physician_case_load_error: "यह मामला लोड नहीं हो सका।",
      physician_confirm_label: "सारांश स्वीकार करें",
      physician_confirm_amend_label: "बदलाव सहेजें",
      physician_review_error: "आपकी समीक्षा सहेजी नहीं जा सकी। कृपया पुनः प्रयास करें।",
      physician_ayush_heading: "दशविध परीक्षा (आयुष इतिहास)",
      physician_ayush_not_recorded: "दर्ज नहीं किया गया",
      physician_login_heading: "चिकित्सक साइन-इन",
      physician_login_intro: "यह कंसोल वास्तविक मरीज़ों का नैदानिक इतिहास दिखाता है — जारी रखने के लिए स्टाफ पासकोड दर्ज करें।",
      physician_passcode_label: "स्टाफ पासकोड",
      physician_login_submit_label: "साइन इन करें",
      physician_login_not_configured: "इस वातावरण में चिकित्सक कंसोल पासकोड कॉन्फ़िगर नहीं है — यह वास्तविक, ईमानदार स्थिति है, कोई बग नहीं।",
      physician_login_incorrect_passcode: "गलत पासकोड।",
      physician_login_unreachable: "साइन-इन एंडपॉइंट तक नहीं पहुंचा जा सका।",
      physician_logout_label: "साइन आउट करें",

      ayush_toggle_label: "यह एक आयुर्वेदिक ओपीडी विज़िट है — आयुष इतिहास जोड़ें",
      ayush_intro: "दशविध परीक्षा — जो जानते हैं उसका उत्तर दें; हर प्रश्न कुछ ऐसा है जो केवल आप ही जानते हैं।",
      ayush_deferred_heading: "परामर्श के समय चिकित्सक द्वारा जांचा जाएगा, यहां नहीं पूछा जाता:",
      ayush_submit_label: "आयुर्वेदिक इतिहास सहेजें",
      ayush_recorded_note: "इस मामले के लिए आयुर्वेदिक (आयुष) इतिहास दर्ज किया गया।",
      ayush_load_error: "आयुष प्रश्न सूची लोड नहीं हो सकी।",
      ayush_save_error: "आयुष इतिहास सहेजा नहीं जा सका।",

      abdm_toggle_label: "इस विज़िट को अपनी आभा (आयुष्मान भारत हेल्थ अकाउंट) आईडी से जोड़ें",
      abdm_request_intro: "इस विज़िट को अपने आभा रिकॉर्ड से जोड़ने के लिए अपना आधार या मोबाइल नंबर दर्ज करें।",
      abdm_identifier_placeholder: "आधार या मोबाइल नंबर",
      abdm_identifier_invalid: "एक मान्य आधार या मोबाइल नंबर दर्ज करें।",
      abdm_send_otp_label: "ओटीपी भेजें",
      abdm_not_configured_note: "इस वातावरण में एबीडीएम सैंडबॉक्स कॉन्फ़िगर नहीं है (कोई लाइव क्रेडेंशियल नहीं) — यह वास्तविक, ईमानदार स्थिति है, कोई बग नहीं।",
      abdm_request_otp_error_prefix: "ओटीपी का अनुरोध नहीं किया जा सका: ",
      abdm_request_unreachable: "एबीडीएम नामांकन एंडपॉइंट तक नहीं पहुंचा जा सका।",
      abdm_verify_intro: "अपने फोन पर भेजा गया ओटीपी दर्ज करें।",
      abdm_otp_placeholder: "6 अंकों का ओटीपी",
      abdm_otp_empty: "आपको प्राप्त ओटीपी दर्ज करें।",
      abdm_verify_otp_label: "ओटीपी सत्यापित करें",
      abdm_verify_otp_error_prefix: "ओटीपी सत्यापित नहीं किया जा सका: ",
      abdm_verify_unreachable: "एबीडीएम सत्यापन एंडपॉइंट तक नहीं पहुंचा जा सका।",
      abdm_linked_prefix: "आभा नंबर से जोड़ा गया ",

      step1_label: "लक्षण",
      step2_label: "फोटो",
      step3_label: "विवरण",
      step4_label: "समीक्षा",
      step_next_label: "आगे",
      step_back_label: "पीछे",
      step2_intro: "क्या आपके पास पहले का कोई पर्चा या लैब रिपोर्ट है? एक फोटो जोड़ें (वैकल्पिक)।",
      step_review_heading: "सबमिट करने से पहले समीक्षा करें",
      review_recap_symptoms: "लक्षण",
      review_recap_age: "उम्र",
      review_recap_duration: "दिन",
      review_recap_document: "फोटो",
      review_recap_not_provided: "नहीं दिया गया",
      review_recap_no_document: "कोई फोटो नहीं जोड़ी गई",


      document_button_label: "पर्चे या रिपोर्ट की फोटो जोड़ें",
      document_hint: "वैकल्पिक — JPG या PNG",
      document_change_label: "फोटो बदलें",
      document_remove_label: "फोटो हटाएं",
      document_remove_aria: "चुनी गई फोटो हटाएं",
      document_filename_prefix: "चयनित: ",

      submit_label: "अपने लक्षण भेजें",
      submit_loading: "भेजा जा रहा है…",
      submit_loading_document: "आपकी फोटो पढ़ी जा रही है और सबमिट हो रही है…",
      submission_complete_note: "आपके लक्षण सबमिट कर दिए गए हैं — आगे क्या होगा यह देखने के लिए बगल में सारांश देखें।",
      submission_complete_button: "एक और मामला सबमिट करें",

      results_heading: "आपका केस सारांश",

      field_chief_complaint: "मुख्य शिकायत",
      field_hpi: "वर्तमान बीमारी का इतिहास",
      field_past_history: "पिछली बीमारी और ऑपरेशन का इतिहास",
      field_drug_allergy: "दवा एवं एलर्जी का इतिहास",
      field_family_history: "पारिवारिक इतिहास",
      field_personal_history: "व्यक्तिगत इतिहास",
      field_ros: "अंग प्रणाली समीक्षा",
      field_investigations: "पूर्व जांच",

      priority_emergency: "आपातकाल — तुरंत मदद लें",
      priority_urgent: "अत्यावश्यक — बहुत जल्द डॉक्टर से मिलें",
      priority_clinic_visit: "क्लिनिक जाएं — कृपया डॉक्टर को दिखाएं",
      priority_self_care: "स्वयं देखभाल — घर पर ध्यान रखें, बदलाव पर नज़र रखें",
      priority_unknown_prefix: "प्राथमिकता स्तर: ",

      review_note_reviewed: "इस सारांश की समीक्षा एक डॉक्टर द्वारा की जा चुकी है।",
      review_note_unreviewed: "यह एक एआई द्वारा तैयार सारांश है और अभी तक किसी डॉक्टर ने इसकी समीक्षा नहीं की है। इसका उद्देश्य डॉक्टर की मदद करना है, उनकी जगह लेना नहीं।",

      degraded_mode_note: "⚠ इस मामले को डॉक्टर को खुद देखना होगा। कृपया इंतज़ार करें — केवल ऊपर दिए गए प्राथमिकता स्तर पर भरोसा न करें।",
      physician_manual_triage_badge: "⚠ आपकी समीक्षा आवश्यक — इस मामले के लिए स्वचालित ट्राइएज उपलब्ध नहीं था",

      listen_button_label: "🔊 सारांश सुनें",
      listen_loading: "ऑडियो लोड हो रहा है…",
      listen_error: "अभी ऑडियो लोड नहीं हो सका। कृपया पुनः प्रयास करें।",

      footer_note: "Inayat डेमो — केवल मूल्यांकन उद्देश्यों के लिए। हमेशा किसी योग्य चिकित्सक से परामर्श लें।",

      error_symptom_too_short: "कृपया सबमिट करने से पहले अपने लक्षणों के बारे में कम से कम कुछ शब्दों में बताएं।",
      error_consent_required: "कृपया सबमिट करने से पहले ऊपर दिए गए सहमति कथन से सहमत हों।",
      error_network: "CarePilot सर्वर से संपर्क नहीं हो सका। कृपया अपना कनेक्शन जांचें और पुनः प्रयास करें।",
      error_backend_unavailable: "एआई सहायक अभी उपलब्ध नहीं है, इसलिए हम अभी आपके केस सारांश को प्रोसेस नहीं कर सकते। कृपया थोड़ी देर बाद पुनः प्रयास करें, या सीधे अस्पताल के कर्मचारियों से बात करें।",
      error_422_prefix: "दर्ज की गई जानकारी में एक समस्या थी। ",
      error_422_fallback: "कृपया अपने लक्षण विवरण की जांच करें और पुनः प्रयास करें।",
      error_server_generic: "सर्वर पर कुछ गड़बड़ी हो गई। कृपया पुनः प्रयास करें, या अस्पताल के कर्मचारियों से बात करें।",
      error_generic_prefix: "कुछ गड़बड़ी हो गई (त्रुटि ",
      error_generic_suffix: ")। कृपया पुनः प्रयास करें।",
      error_unexpected_response: "सर्वर से एक अप्रत्याशित प्रतिक्रिया मिली। कृपया पुनः प्रयास करें।",

      error_mic_permission_denied: "हम आपके माइक्रोफ़ोन तक नहीं पहुंच सके। कृपया अपने ब्राउज़र की सेटिंग में माइक्रोफ़ोन की अनुमति दें और पुनः प्रयास करें, या इसके बजाय अपने लक्षण टाइप करें।",
      error_mic_not_found: "इस डिवाइस पर कोई माइक्रोफ़ोन नहीं मिला। कृपया अपने लक्षण टाइप करें।",
      error_mic_unsupported: "इस ब्राउज़र में वॉइस रिकॉर्डिंग समर्थित नहीं है। कृपया अपने लक्षण टाइप करें।",
      error_mic_generic: "रिकॉर्डिंग के दौरान कुछ गड़बड़ी हो गई। कृपया पुनः प्रयास करें, या अपने लक्षण टाइप करें।",
      error_recording_too_short: "वह रिकॉर्डिंग उपयोग करने के लिए बहुत छोटी या अस्पष्ट थी। कृपया पुनः प्रयास करें और कुछ सेकंड तक बोलें।",

      error_document_unreadable: "हम वह फोटो स्पष्ट रूप से नहीं पढ़ पाए। कृपया पर्चे या रिपोर्ट की एक स्पष्ट, अच्छी रोशनी वाली फोटो (JPG या PNG) आज़माएं, या बिना फोटो के सबमिट करें।",
      error_document_too_large: "वह फोटो अपलोड करने के लिए बहुत बड़ा है। कृपया एक छोटी फोटो चुनें या कम रिज़ॉल्यूशन पर नई फोटो लें।",
      error_document_invalid_type: "कृपया एक इमेज फ़ाइल चुनें (JPG या PNG)।",

      status_sending: "आपकी जानकारी भेजी जा रही है, कृपया प्रतीक्षा करें..."
    },

    // ---------------------------------------------------------------
    // Telugu
    // ---------------------------------------------------------------
    te: {
      brand_tagline: "AI సహాయంతో కేస్ ఇన్‌టేక్ · SIH26047 డెమో",

      hero_eyebrow: "భారత్‌లోని 2–5 నిమిషాల OPD సంప్రదింపు కోసం రూపొందించబడింది",
      hero_title: "మీ డాక్టర్ వద్ద కేవలం కొన్ని నిమిషాలే ఉంటాయి. అదే విషయం మళ్ళీ చెప్పడంలో వాటిని వృథా చేయకండి.",
      hero_body: "Inayat మీ సందర్శనకు ముందే మీరు చెప్పే విషయాలను స్పష్టమైన, క్రమబద్ధమైన సారాంశంగా మారుస్తుంది, దాన్ని డాక్టర్ కొన్ని సెకన్లలో చదవగలరు — దాదాపు సమయమే లేని గదిలో అదే ప్రశ్నలు మళ్ళీ అడగకుండా. టైప్ చేయండి, మాట్లాడండి, లేదా పాత ప్రిస్క్రిప్షన్ లేదా రిపోర్ట్ ఫోటో చూపించండి — మీకు సులభమైనది ఎంచుకోండి.",

      live_demo_label: "ఇది నిజమైన అత్యవసర పరిస్థితిని పట్టుకోవడం చూడండి — లైవ్, ఏమీ క్లిక్ చేయకుండానే",
      live_demo_result_note: "ప్రతి నిజమైన సమర్పణ వెళ్ళే అదే నిర్ధారిత భద్రతా స్కానర్ ద్వారా తక్షణమే పట్టుకోబడింది — AI కాల్ అవసరం లేదు, ఆఫ్‌లైన్‌లో కూడా పనిచేస్తుంది.",
      live_demo_try_button: "మీరే ప్రయత్నించండి →",

      hero_stat_num_1: "70–80%",
      hero_stat_label_1: "సరైన నిర్ధారణలు కేవలం మంచి హిస్టరీ ద్వారానే వస్తాయి, ఏ పరీక్షకు ముందే",
      hero_stat_num_2: "~2 నిమిషాలు",
      hero_stat_label_2: "భారత్‌లో సగటు ప్రాథమిక వైద్య సంప్రదింపు వ్యవధి — అధ్యయనం చేసిన 67 దేశాల్లో అత్యల్పమైనది",
      hero_stat_source: "మూలాలు: సాంప్రదాయ క్లినికల్ హిస్టరీ బోధన; BMJ Open, 2017 (67 దేశాల సంప్రదింపు-వ్యవధి అధ్యయనం). పూర్తి ఆధారం కోసం docs/sih/ చూడండి.",
      method_type_label: "టైప్ చేయండి",
      method_speak_label: "మాట్లాడండి",
      method_photo_label: "ఫోటో తీయండి",

      emergency_bar_label: "ఇది అత్యవసర పరిస్థితి అయితే:",
      emergency_bar_cta: "ఇప్పుడే 108కి కాల్ చేయండి",
      emergency_bar_note: "ఉచితం · 24×7 · జాతీయ అంబులెన్స్",

      notice: "ఇది కేవలం లక్షణాల నమోదు దశ యొక్క డెమో మాత్రమే. ఇది డాక్టర్ పరిశీలన కోసం మీ లక్షణాలను క్రమబద్ధంగా రాసేందుకు సహాయపడుతుంది — ఇది మీకు వ్యాధి నిర్ధారణ చేయదు, డాక్టర్‌ను కలవడానికి ప్రత్యామ్నాయం కాదు. ఇది అత్యవసర పరిస్థితి అయితే, 108కి కాల్ చేయండి లేదా సమీపంలోని ఆసుపత్రికి వెళ్ళండి.",

      sidebar_title: "Inayat ఎలా పనిచేస్తుంది",
      sidebar_step1: "మీ లక్షణాలను చెప్పండి — టైప్ చేయడం, మాట్లాడటం, లేదా ఫోటో మూలంగా",
      sidebar_step2: "మా AI ఒక స్పష్టమైన, క్రమబద్ధమైన సారాంశాన్ని తయారు చేస్తుంది",
      sidebar_step3: "ఏ నిర్ణయం తీసుకోనే ముందు మీ డాక్టర్ దీన్ని సమీక్షిస్తారు",
      sidebar_privacy_note: "మీ సమాధానాలు ఈ సారాంశాన్ని తయారు చేయడానికి మాత్రమే ఉపయోగించబడతాయి.",

      safety_metrics_title: "కొలవబడిన భద్రతా పనితీరు",
      safety_metrics_recall_label: "ఎమర్జెన్సీ రీకాల్",
      safety_metrics_accuracy_label: "మొత్తం ఖచ్చితత్వం",
      safety_metrics_na: "వర్తించదు",
      safety_metrics_evaluated_prefix: "ప్రత్యక్షంగా మూల్యాంకనం చేయబడింది: ",
      safety_metrics_of_total_mid: " లో ",
      safety_metrics_cases_suffix: " పరీక్షా కేసులు. ",
      safety_metrics_skipped_suffix: " మూల్యాంకనం చేయలేకపోయాము — ఈ డెమోలో ప్రత్యక్ష AI కీ కాన్ఫిగర్ చేయబడలేదు.",
      safety_metrics_toggle_show: "ప్రతి కేసు పూర్తి వివరాలు చూపించు",
      safety_metrics_toggle_hide: "ప్రతి కేసు పూర్తి వివరాలు దాచు",
      safety_metrics_col_case: "కేసు",
      safety_metrics_col_expected: "ఊహించినది",
      safety_metrics_col_actual: "వాస్తవం",
      safety_metrics_col_result: "ఫలితం",
      safety_metrics_row_skipped: "దాటవేయబడింది",
      safety_metrics_row_pass: "సరైనది",
      safety_metrics_row_fail: "తప్పు",
      safety_metrics_false_negatives_prefix: "⚠ ఈ పరీక్షా సెట్‌లో మిస్ అయిన అత్యవసర కేసు(లు): ",
      safety_metrics_honesty_note: "11-కేసుల, రచయిత-లేబుల్ చేసిన పరీక్షా సెట్‌పై కొలవబడింది — ఇది నిజమైన గణన, మార్కెటింగ్ దావా కాదు, కానీ నిజమైన రోగి డేటాపై క్లినికల్ ధ్రువీకరణకు ప్రత్యామ్నాయం కాదు.",

      lang_toggle_aria: "భాషను ఎంచుకోండి",

      field_symptom_label: "మీకు ఎలా అనిపిస్తుందో మీ సొంత మాటల్లో చెప్పండి",
      field_symptom_placeholder: "ఉదాహరణకు: నాకు మూడు రోజులుగా జ్వరం మరియు తీవ్రమైన దగ్గు ఉంది, మరియు శ్వాస తీసుకున్నప్పుడు ఛాతీలో నొప్పిగా ఉంది.",
      field_age_label: "మీ వయస్సు (ఐచ్ఛికం)",
      field_age_placeholder: "ఉదా. 65",
      field_duration_label: "ఎన్ని రోజులుగా? (ఐచ్ఛికం)",
      field_duration_placeholder: "ఉదా. 3",

      mic_button_idle: "లక్షణాలను రికార్డ్ చేయండి",
      mic_button_recording: "రికార్డింగ్ ఆపండి",
      mic_hint_idle: "టైప్ చేయడానికి బదులుగా మాట్లాడటానికి నొక్కండి",
      recording_live_label: "రికార్డింగ్ జరుగుతోంది",
      recording_processing: "మీ రికార్డింగ్ ప్రాసెస్ అవుతోంది…",
      voice_shortcut_note: "రికార్డింగ్ మీ లక్షణాలను వెంటనే పంపిస్తుంది — మిగతా దశల ద్వారా వెళ్లాల్సిన అవసరం ఉండదు.",

      consent_checkbox_label: "ఈ సమాచారం నమోదు చేయబడి, ఈ సందర్శన కోసం నా చికిత్స చేసే వైద్యుడితో పంచుకోబడుతుందని నేను అంగీకరిస్తున్నాను, భారతదేశ డిజిటల్ వ్యక్తిగత డేటా రక్షణ చట్టం, 2023కి అనుగుణంగా.",

      redflag_hint: "⚠ దీనికి తక్షణ శ్రద్ధ అవసరం కావచ్చు. కొనసాగించండి — సమర్పించిన వెంటనే మీకు స్పష్టమైన సమాధానం లభిస్తుంది, ఆందోళనగా అనిపిస్తే మీరు ఇప్పుడే 108కి కాల్ చేయవచ్చు.",

      socrates_heading: "వైద్యుడు బహుశా ఇవి కూడా అడగవచ్చు:",

      view_toggle_aria: "రోగి మరియు వైద్యుడి వీక్షణ మధ్య మారండి",
      view_patient_label: "రోగి",
      view_physician_label: "వైద్యుడి కన్సోల్",
      physician_console_heading: "వైద్యుడి కన్సోల్",
      physician_console_intro: "రోగి ఇన్‌టేక్ పూర్తి చేసిన ప్రతి కేసు, ఇటీవలివి మొదట. సంప్రదింపులకు ముందు AI రూపొందించిన సారాంశాన్ని సమీక్షించడానికి ఒకదాన్ని తెరవండి.",
      physician_ayush_filter_label: "ఆయుర్వేద (ఆయుష్) కేసులు మాత్రమే",
      physician_no_cases: "ఇంకా కేసులు లేవు.",
      physician_load_error: "కేసుల జాబితాను లోడ్ చేయలేకపోయాము.",
      physician_select_case_prompt: "సమీక్షించడానికి జాబితా నుండి ఒక కేసును ఎంచుకోండి.",
      physician_status_reviewed: "సమీక్షించబడింది",
      physician_status_draft: "డ్రాఫ్ట్",
      physician_loading_case: "కేసు లోడ్ అవుతోంది…",
      physician_case_load_error: "ఈ కేసును లోడ్ చేయలేకపోయాము.",
      physician_confirm_label: "సారాంశాన్ని ఆమోదించండి",
      physician_confirm_amend_label: "మార్పులను సేవ్ చేయండి",
      physician_review_error: "మీ సమీక్షను సేవ్ చేయలేకపోయాము. దయచేసి మళ్లీ ప్రయత్నించండి.",
      physician_ayush_heading: "దశవిధ పరీక్ష (ఆయుష్ చరిత్ర)",
      physician_ayush_not_recorded: "నమోదు చేయబడలేదు",
      physician_login_heading: "వైద్యుడి సైన్-ఇన్",
      physician_login_intro: "ఈ కన్సోల్ నిజమైన రోగుల క్లినికల్ చరిత్రలను చూపిస్తుంది — కొనసాగించడానికి స్టాఫ్ పాస్‌కోడ్‌ను నమోదు చేయండి.",
      physician_passcode_label: "స్టాఫ్ పాస్‌కోడ్",
      physician_login_submit_label: "సైన్ ఇన్ చేయండి",
      physician_login_not_configured: "ఈ వాతావరణంలో వైద్యుడి కన్సోల్ పాస్‌కోడ్ కాన్ఫిగర్ చేయబడలేదు — ఇది నిజమైన, నిజాయితీ గల స్థితి, బగ్ కాదు.",
      physician_login_incorrect_passcode: "తప్పు పాస్‌కోడ్.",
      physician_login_unreachable: "సైన్-ఇన్ ఎండ్‌పాయింట్‌ను చేరుకోలేకపోయాము.",
      physician_logout_label: "సైన్ అవుట్ చేయండి",

      ayush_toggle_label: "ఇది ఆయుర్వేద OPD సందర్శన — ఆయుష్ చరిత్రను జోడించండి",
      ayush_intro: "దశవిధ పరీక్ష — మీకు తెలిసినది సమాధానం ఇవ్వండి; ప్రతి ప్రశ్న మీకు మాత్రమే తెలిసిన విషయం.",
      ayush_deferred_heading: "సంప్రదింపుల సమయంలో వైద్యుడు అంచనా వేస్తారు, ఇక్కడ అడగబడదు:",
      ayush_submit_label: "ఆయుర్వేద చరిత్రను సేవ్ చేయండి",
      ayush_recorded_note: "ఈ కేసు కోసం ఆయుర్వేద (ఆయుష్) చరిత్ర నమోదు చేయబడింది.",
      ayush_load_error: "ఆయుష్ ప్రశ్నల జాబితాను లోడ్ చేయలేకపోయాము.",
      ayush_save_error: "ఆయుష్ చరిత్రను సేవ్ చేయలేకపోయాము.",
      abdm_toggle_label: "ఈ సందర్శనను మీ ABHA (ఆయుష్మాన్ భారత్ హెల్త్ అకౌంట్) IDకి లింక్ చేయండి",
      abdm_request_intro: "ఈ సందర్శనను మీ ABHA రికార్డుకు లింక్ చేయడానికి మీ ఆధార్ లేదా మొబైల్ నంబర్‌ను నమోదు చేయండి.",
      abdm_identifier_placeholder: "ఆధార్ లేదా మొబైల్ నంబర్",
      abdm_identifier_invalid: "చెల్లుబాటు అయ్యే ఆధార్ లేదా మొబైల్ నంబర్‌ను నమోదు చేయండి.",
      abdm_send_otp_label: "OTP పంపండి",
      abdm_not_configured_note: "ఈ వాతావరణంలో ABDM సాండ్‌బాక్స్ కాన్ఫిగర్ చేయబడలేదు (లైవ్ క్రెడెన్షియల్స్ లేవు) — ఇది నిజమైన, నిజాయితీ గల స్థితి, బగ్ కాదు.",
      abdm_request_otp_error_prefix: "OTP అభ్యర్థించలేకపోయాము: ",
      abdm_request_unreachable: "ABDM ఎన్‌రోల్‌మెంట్ ఎండ్‌పాయింట్‌ను చేరుకోలేకపోయాము.",
      abdm_verify_intro: "మీ ఫోన్‌కు పంపిన OTPని నమోదు చేయండి.",
      abdm_otp_placeholder: "6 అంకెల OTP",
      abdm_otp_empty: "మీకు వచ్చిన OTPని నమోదు చేయండి.",
      abdm_verify_otp_label: "OTPని ధృవీకరించండి",
      abdm_verify_otp_error_prefix: "OTPని ధృవీకరించలేకపోయాము: ",
      abdm_verify_unreachable: "ABDM ధృవీకరణ ఎండ్‌పాయింట్‌ను చేరుకోలేకపోయాము.",
      abdm_linked_prefix: "ABHA నంబర్‌కు లింక్ చేయబడింది ",

      step1_label: "లక్షణాలు",
      step2_label: "ఫోటో",
      step3_label: "వివరాలు",
      step4_label: "సమీక్ష",
      step_next_label: "తర్వాత",
      step_back_label: "వెనక్కి",
      step2_intro: "మీ వద్ద పాత ప్రిస్క్రిప్షన్ లేదా ల్యాబ్ రిపోర్ట్ ఉందా? ఒక ఫోటో జోడించండి (ఐచ్ఛికం).",
      step_review_heading: "సమర్పించే ముందు సమీక్షించండి",
      review_recap_symptoms: "లక్షణాలు",
      review_recap_age: "వయస్సు",
      review_recap_duration: "రోజులు",
      review_recap_document: "ఫోటో",
      review_recap_not_provided: "ఇవ్వలేదు",
      review_recap_no_document: "ఫోటో జోడించలేదు",


      document_button_label: "ప్రిస్క్రిప్షన్ లేదా రిపోర్ట్ ఫోటో జోడించండి",
      document_hint: "ఐచ్ఛికం — JPG లేదా PNG",
      document_change_label: "ఫోటో మార్చండి",
      document_remove_label: "ఫోటో తీసివేయండి",
      document_remove_aria: "ఎంచుకున్న ఫోటోను తీసివేయండి",
      document_filename_prefix: "ఎంచుకున్నది: ",

      submit_label: "నా లక్షణాలను సమర్పించండి",
      submit_loading: "సమర్పిస్తోంది…",
      submit_loading_document: "మీ ఫోటోను చదివి సమర్పిస్తోంది…",
      submission_complete_note: "మీ లక్షణాలు సమర్పించబడ్డాయి — తర్వాత ఏమి జరుగుతుందో చూడటానికి పక్కన ఉన్న సారాంశాన్ని చూడండి.",
      submission_complete_button: "మరో కేసును సమర్పించండి",

      results_heading: "మీ కేస్ సారాంశం",

      field_chief_complaint: "ప్రధాన సమస్య",
      field_hpi: "ప్రస్తుత అనారోగ్యం వివరాలు",
      field_past_history: "గత అనారోగ్యం మరియు ఆపరేషన్ చరిత్ర",
      field_drug_allergy: "మందులు మరియు అలర్జీ చరిత్ర",
      field_family_history: "కుటుంబ చరిత్ర",
      field_personal_history: "వ్యక్తిగత చరిత్ర",
      field_ros: "శరీర వ్యవస్థల సమీక్ష",
      field_investigations: "గత పరీక్షలు",

      priority_emergency: "అత్యవసరం — వెంటనే సహాయం తీసుకోండి",
      priority_urgent: "అర్జెంట్ — వీలైనంత త్వరగా డాక్టర్‌ను కలవండి",
      priority_clinic_visit: "క్లినిక్ సందర్శన — దయచేసి డాక్టర్‌ను కలవండి",
      priority_self_care: "స్వీయ సంరక్షణ — ఇంట్లోనే జాగ్రత్త వహించండి, మార్పులను గమనించండి",
      priority_unknown_prefix: "ప్రాధాన్యత స్థాయి: ",

      review_note_reviewed: "ఈ సారాంశాన్ని ఒక డాక్టర్ సమీక్షించారు.",
      review_note_unreviewed: "ఇది AI రూపొందించిన సారాంశం, దీన్ని ఇంకా ఏ డాక్టర్ సమీక్షించలేదు. దీని ఉద్దేశ్యం డాక్టర్‌కు సహాయం చేయడం, వారి స్థానంలో ఉండటం కాదు.",

      degraded_mode_note: "⚠ ఈ కేసును డాక్టర్ ప్రత్యక్షంగా చూడాలి. దయచేసి వేచి ఉండండి — పైన ఇచ్చిన ప్రాధాన్యత స్థాయిపై మాత్రమే ఆధారపడకండి.",
      physician_manual_triage_badge: "⚠ మీ సమీక్ష అవసరం — ఈ కేసుకు స్వయంచాలక ట్రయాజ్ అందుబాటులో లేదు",

      listen_button_label: "🔊 సారాంశం వినండి",
      listen_loading: "ఆడియో లోడ్ అవుతోంది…",
      listen_error: "ఇప్పుడు ఆడియో లోడ్ కాలేదు. దయచేసి మళ్ళీ ప్రయత్నించండి.",

      footer_note: "Inayat డెమో — కేవలం మూల్యాంకన ప్రయోజనాల కోసం మాత్రమే. ఎల్లప్పుడూ అర్హత గల డాక్టర్‌ను సంప్రదించండి.",

      error_symptom_too_short: "దయచేసి సమర్పించే ముందు మీ లక్షణాలను కనీసం కొన్ని పదాల్లో వివరించండి.",
      error_consent_required: "దయచేసి సమర్పించే ముందు పైన ఉన్న సమ్మతి ప్రకటనకు అంగీకరించండి.",
      error_network: "CarePilot సర్వర్‌ను చేరుకోలేకపోయాము. దయచేసి మీ కనెక్షన్‌ను తనిఖీ చేసి, మళ్ళీ ప్రయత్నించండి.",
      error_backend_unavailable: "AI అసిస్టెంట్ ప్రస్తుతం అందుబాటులో లేదు, కాబట్టి మేము ఇప్పుడు మీ కేస్ సారాంశాన్ని ప్రాసెస్ చేయలేకపోతున్నాము. దయచేసి కొద్ది సేపటి తర్వాత మళ్ళీ ప్రయత్నించండి, లేదా నేరుగా ఆసుపత్రి సిబ్బందితో మాట్లాడండి.",
      error_422_prefix: "నమోదు చేసిన సమాచారంలో ఒక సమస్య ఉంది. ",
      error_422_fallback: "దయచేసి మీ లక్షణాల వివరణను తనిఖీ చేసి, మళ్ళీ ప్రయత్నించండి.",
      error_server_generic: "సర్వర్ లో ఏదో తప్పు జరిగింది. దయచేసి మళ్ళీ ప్రయత్నించండి, లేదా ఆసుపత్రి సిబ్బందితో మాట్లాడండి.",
      error_generic_prefix: "ఏదో తప్పు జరిగింది (ఎర్రర్ ",
      error_generic_suffix: "). దయచేసి మళ్ళీ ప్రయత్నించండి.",
      error_unexpected_response: "సర్వర్ నుండి ఊహించని ప్రతిస్పందన వచ్చింది. దయచేసి మళ్ళీ ప్రయత్నించండి.",

      error_mic_permission_denied: "మేము మీ మైక్రోఫోన్‌ను యాక్సెస్ చేయలేకపోయాము. దయచేసి మీ బ్రౌజర్ సెట్టింగ్స్లో మైక్రోఫోన్ అనుమతి ఇచ్చి, మళ్ళీ ప్రయత్నించండి, లేదా బదులుగా మీ లక్షణాలను టైప్ చేయండి.",
      error_mic_not_found: "ఈ పరికరంలో మైక్రోఫోన్ కనుగొనబడలేదు. దయచేసి మీ లక్షణాలను టైప్ చేయండి.",
      error_mic_unsupported: "ఈ బ్రౌజర్‌లో వాయిస్ రికార్డింగ్కు మద్దతు లేదు. దయచేసి మీ లక్షణాలను టైప్ చేయండి.",
      error_mic_generic: "రికార్డింగ్ సమయంలో ఏదో తప్పు జరిగింది. దయచేసి మళ్ళీ ప్రయత్నించండి, లేదా మీ లక్షణాలను టైప్ చేయండి.",
      error_recording_too_short: "ఆ రికార్డింగ్ ఉపయోగించడానికి చాలా చిన్నదిగా లేదా అస్పష్టంగా ఉంది. దయచేసి మళ్ళీ ప్రయత్నించి కొన్ని సెకన్ల పాటు మాట్లాడండి.",

      error_document_unreadable: "మేము ఆ ఫోటోను స్పష్టంగా చదవలేకపోయాము. దయచేసి ప్రిస్క్రిప్షన్ లేదా రిపోర్ట్ యొక్క స్పష్టమైన, బాగా వెలుతురు ఉన్న ఫోటో (JPG లేదా PNG) ప్రయత్నించండి, లేదా ఫోటో లేకుండా సమర్పించండి.",
      error_document_too_large: "ఆ ఫోటో అప్‌లోడ్ చేయడానికి చాలా పెద్దగా ఉంది. దయచేసి చిన్న ఫోటోను ఎంచుకోండి లేదా తక్కువ రిజొల్యూషన్‌లో కొత్త ఫోటో తీయండి.",
      error_document_invalid_type: "దయచేసి ఒక ఇమేజ్ ఫైల్‌ను ఎంచుకోండి (JPG లేదా PNG).",

      status_sending: "మీ సమాచారం పంపబడుతోంది, దయచేసి వేచి ఉండండి..."
    }
  };

  function safeGetStoredLang() {
    try {
      var stored = global.localStorage ? global.localStorage.getItem(STORAGE_KEY) : null;
      if (stored && SUPPORTED.indexOf(stored) !== -1) {
        return stored;
      }
    } catch (e) {
      // localStorage can throw (privacy mode, disabled storage, etc.) -
      // fall through to the default language rather than letting this
      // take down page init.
    }
    return DEFAULT_LANG;
  }

  function safeSetStoredLang(lang) {
    try {
      if (global.localStorage) {
        global.localStorage.setItem(STORAGE_KEY, lang);
      }
    } catch (e) {
      // Persistence is a nice-to-have, not a requirement - a user whose
      // browser blocks storage still gets a working language toggle for
      // the current page view, it just won't be remembered next time.
    }
  }

  var currentLang = safeGetStoredLang();

  function getLang() {
    return currentLang;
  }

  function setLang(lang) {
    if (SUPPORTED.indexOf(lang) === -1) {
      return currentLang;
    }
    currentLang = lang;
    safeSetStoredLang(lang);
    return currentLang;
  }

  function t(key) {
    var table = STRINGS[currentLang] || STRINGS[DEFAULT_LANG];
    if (table && Object.prototype.hasOwnProperty.call(table, key)) {
      return table[key];
    }
    var fallback = STRINGS[DEFAULT_LANG];
    if (fallback && Object.prototype.hasOwnProperty.call(fallback, key)) {
      return fallback[key];
    }
    return key;
  }

  global.CarePilotI18n = {
    SUPPORTED: SUPPORTED,
    DEFAULT_LANG: DEFAULT_LANG,
    getLang: getLang,
    setLang: setLang,
    t: t
  };
})(window);
