// CarePilot / MediKiosk UI translations - English, Hindi, Telugu.
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

      hero_title: "Tell us how you're feeling",
      hero_body: "MediKiosk helps turn what you share into a clear summary your doctor can act on quickly. Type, speak, or show us a photo — whatever's easiest for you.",
      method_type_label: "Type",
      method_speak_label: "Speak",
      method_photo_label: "Photograph",

      notice: "This is a demo of the case-intake step only. It helps write down your symptoms in an organized way for a doctor to review — it does not diagnose you and it is not a substitute for seeing a doctor. If this is an emergency, call for help or go to the nearest hospital right now.",

      sidebar_title: "How MediKiosk works",
      sidebar_step1: "Describe your symptoms — by typing, speaking, or a photo",
      sidebar_step2: "Our AI drafts a clear, structured summary",
      sidebar_step3: "Your doctor reviews it before any decision is made",
      sidebar_privacy_note: "Your answers are used only to prepare this summary for your visit.",

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

      document_button_label: "Add a photo of a prescription or report",
      document_hint: "Optional — JPG or PNG",
      document_change_label: "Change photo",
      document_remove_label: "Remove photo",
      document_remove_aria: "Remove selected photo",
      document_filename_prefix: "Selected: ",

      submit_label: "Submit My Symptoms",
      submit_loading: "Submitting…",
      submit_loading_document: "Reading your photo and submitting…",

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

      listen_button_label: "🔊 Listen to summary",
      listen_loading: "Loading audio…",
      listen_error: "Couldn't load audio right now. Please try again.",

      footer_note: "CarePilot demo — for evaluation purposes only. Always seek care from a qualified physician.",

      error_symptom_too_short: "Please describe your symptoms in at least a few words before submitting.",
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

      hero_title: "हमें बताएं कि आपको कैसा महसूस हो रहा है",
      hero_body: "MediKiosk आपकी बात को एक स्पष्ट सारांश में बदलने में मदद करता है, जिसे डॉक्टर जल्दी समझ सकें। टाइप करें, बोलें, या फोटो दिखाएं — जो भी आपके लिए आसान हो।",
      method_type_label: "टाइप करें",
      method_speak_label: "बोलें",
      method_photo_label: "फोटो लें",

      notice: "यह केवल लक्षण दर्ज करने के चरण का एक डेमो है। यह डॉक्टर की समीक्षा के लिए आपके लक्षणों को व्यवस्थित तरीके से लिखने में मदद करता है — यह आपका निदान नहीं करता और डॉक्टर से मिलने का विकल्प नहीं है। यदि यह एक आपातकालीन स्थिति है, तो तुरंत मदद के लिए कॉल करें या नज़दीकी अस्पताल जाएं।",

      sidebar_title: "MediKiosk कैसे काम करता है",
      sidebar_step1: "अपने लक्षण बताएं — टाइप करके, बोलकर, या फोटो से",
      sidebar_step2: "हमारा एआई एक स्पष्ट, व्यवस्थित सारांश तैयार करता है",
      sidebar_step3: "कोई भी निर्णय लेने से पहले आपका डॉक्टर इसकी समीक्षा करता है",
      sidebar_privacy_note: "आपके उत्तर केवल इस सारांश को तैयार करने के लिए उपयोग किए जाते हैं।",

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

      document_button_label: "पर्चे या रिपोर्ट की फोटो जोड़ें",
      document_hint: "वैकल्पिक — JPG या PNG",
      document_change_label: "फोटो बदलें",
      document_remove_label: "फोटो हटाएं",
      document_remove_aria: "चुनी गई फोटो हटाएं",
      document_filename_prefix: "चयनित: ",

      submit_label: "अपने लक्षण भेजें",
      submit_loading: "भेजा जा रहा है…",
      submit_loading_document: "आपकी फोटो पढ़ी जा रही है और सबमिट हो रही है…",

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

      listen_button_label: "🔊 सारांश सुनें",
      listen_loading: "ऑडियो लोड हो रहा है…",
      listen_error: "अभी ऑडियो लोड नहीं हो सका। कृपया पुनः प्रयास करें।",

      footer_note: "CarePilot डेमो — केवल मूल्यांकन उद्देश्यों के लिए। हमेशा किसी योग्य चिकित्सक से परामर्श लें।",

      error_symptom_too_short: "कृपया सबमिट करने से पहले अपने लक्षणों के बारे में कम से कम कुछ शब्दों में बताएं।",
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

      hero_title: "మీకు ఎలా అనిపిస్తుందో మాకు చెప్పండి",
      hero_body: "MediKiosk మీ లక్షణాలను స్పష్టమైన సారాంశంగా మార్చుతుంది, తద్వారా డాక్టర్ త్వరగా అర్థం చేసుకోగలరు. టైప్ చేయండి, మాట్లాడండి, లేదా ఫోటో చూపించండి — మీకు సులభమైనది ఎంచుకోండి.",
      method_type_label: "టైప్ చేయండి",
      method_speak_label: "మాట్లాడండి",
      method_photo_label: "ఫోటో తీయండి",

      notice: "ఇది కేవలం లక్షణాల నమోదు దశ యొక్క డెమో మాత్రమే. ఇది డాక్టర్ పరిశీలన కోసం మీ లక్షణాలను క్రమబద్ధంగా రాసేందుకు సహాయపడుతుంది — ఇది మీకు వ్యాధి నిర్ధారణ చేయదు, డాక్టర్‌ను కలవడానికి ప్రత్యామ్నాయం కాదు. ఇది అత్యవసర పరిస్థితి అయితే, వెంటనే సహాయం కోసం కాల్ చేయండి లేదా సమీపంలోని ఆసుపత్రికి వెళ్ళండి.",

      sidebar_title: "MediKiosk ఎలా పనిచేస్తుంది",
      sidebar_step1: "మీ లక్షణాలను చెప్పండి — టైప్ చేయడం, మాట్లాడటం, లేదా ఫోటో మూలంగా",
      sidebar_step2: "మా AI ఒక స్పష్టమైన, క్రమబద్ధమైన సారాంశాన్ని తయారు చేస్తుంది",
      sidebar_step3: "ఏ నిర్ణయం తీసుకోనే ముందు మీ డాక్టర్ దీన్ని సమీక్షిస్తారు",
      sidebar_privacy_note: "మీ సమాధానాలు ఈ సారాంశాన్ని తయారు చేయడానికి మాత్రమే ఉపయోగించబడతాయి.",

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

      document_button_label: "ప్రిస్క్రిప్షన్ లేదా రిపోర్ట్ ఫోటో జోడించండి",
      document_hint: "ఐచ్ఛికం — JPG లేదా PNG",
      document_change_label: "ఫోటో మార్చండి",
      document_remove_label: "ఫోటో తీసివేయండి",
      document_remove_aria: "ఎంచుకున్న ఫోటోను తీసివేయండి",
      document_filename_prefix: "ఎంచుకున్నది: ",

      submit_label: "నా లక్షణాలను సమర్పించండి",
      submit_loading: "సమర్పిస్తోంది…",
      submit_loading_document: "మీ ఫోటోను చదివి సమర్పిస్తోంది…",

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

      listen_button_label: "🔊 సారాంశం వినండి",
      listen_loading: "ఆడియో లోడ్ అవుతోంది…",
      listen_error: "ఇప్పుడు ఆడియో లోడ్ కాలేదు. దయచేసి మళ్ళీ ప్రయత్నించండి.",

      footer_note: "CarePilot డెమో — కేవలం మూల్యాంకన ప్రయోజనాల కోసం మాత్రమే. ఎల్లప్పుడూ అర్హత గల డాక్టర్‌ను సంప్రదించండి.",

      error_symptom_too_short: "దయచేసి సమర్పించే ముందు మీ లక్షణాలను కనీసం కొన్ని పదాల్లో వివరించండి.",
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
