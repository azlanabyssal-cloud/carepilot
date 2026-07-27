# Interview Notes — built alongside the code, not after it

Rule for this file: every entry is tied to a real file/line in this repo.
If you can't point to the code while explaining the note, the note doesn't
go in here yet.

---

## Entry 1 — Why a rule-based red-flag scan runs *before* any model

**Where:** `app/agents/intake.py`, `scan_red_flags()`

**What we built:** a plain substring match against a small, fixed list of
emergency terms (`RED_FLAG_TERMS`), run on every case before the
Triage-Reasoning agent (an LLM, coming next session) ever sees it.

**Why this way, not the "obvious" way:** the obvious move for a CSM student
is to reach straight for an ML/LLM classifier for everything, because that's
what the course teaches. I deliberately put a *dumber*, deterministic layer
in front of it. An LLM can paraphrase-match ("can't catch my breath" →
difficulty breathing) which a substring scan can't — but an LLM can also
have an off night, get a weird prompt, or silently miscategorize. A
substring match on a known emergency term is either right or absent — no
in-between failure mode. This is "defense in depth": two independent
mechanisms have to both miss an emergency for the system to miss it,
instead of one.

**The tradeoff, said out loud (this is the part that impresses an
interviewer, not the code):** `test_scan_red_flags_misses_paraphrase_by_design`
proves the scan misses "can't catch my breath." That's a real, known gap —
not a bug I didn't notice. It's covered by the next layer (LLM reasoning),
not by this one. Knowing exactly what a component does *not* do is the
signal that you designed it, rather than copy-pasted it.

**The question an interviewer will actually ask:**
*"Why not just use an LLM for this whole step?"*
→ *"Because I want the emergency path to not have a single point of
failure. The keyword scan and the LLM reasoning agent have to both miss
a case for a real emergency to be misclassified — that's a much lower-risk
failure mode than one smart system doing everything."*

---

## Entry 2 — Why the schemas (`app/schemas.py`) exist before any agent logic

**Where:** `app/schemas.py`

**What we built:** `PatientInput`, `CaseSummary`, `TriageDecision` as
Pydantic models, written *before* the second, third, and fourth agents.

**Why this way:** each agent in a multi-agent pipeline should be testable
and explainable in isolation. Defining the data contract first means agent
2 can be built next session against a `CaseSummary` that already exists and
is already tested — you're never blocked waiting for the "whole system" to
be done before anything is provably correct.

**The question an interviewer will actually ask:**
*"Why Pydantic instead of plain dicts?"*
→ *"Type validation at the boundary — a malformed request fails fast with
a clear 422 error instead of an agent three steps downstream crashing on
a missing field. It's also what FastAPI uses natively for request/response
validation and OpenAPI docs generation, so it's not extra work, it's the
same model doing three jobs."*

---

## Entry 3 — Why FastAPI, and why the pipeline is exposed one agent at a time

**Where:** `app/main.py`

**What we built:** a `/health` endpoint and a `/intake` endpoint that runs
*only* the Intake Agent — deliberately not the full 4-agent chain yet.

**Why this way:** you can `curl` this right now and get a real answer (see
the terminal output from this session) instead of having something that
only works once all four agents exist. Ship the smallest working slice,
prove it, then extend — the same discipline the MLOps elective (§08 of the
placement report) is trying to teach you, applied here instead of on a
throwaway assignment.

**The question an interviewer will actually ask:**
*"Walk me through what happens when a request comes in."* → be able to
literally narrate `main.py` → `intake.py` → `schemas.py` without opening
the files. That's the actual bar, not reciting this note.

---

## Entry 4 — Why the red-flag short-circuit happens before the LLM is even called

**Where:** `app/agents/triage.py`, `run_triage_reasoning()`

**What we built:** if `case.has_red_flag` is `True` (set by the Intake
Agent's deterministic scan), this function returns `TriageLevel.EMERGENCY`
immediately and never calls `backend.propose()`.

**Why this way:** cost and latency are real reasons, but the actual reason
is safety — a case already flagged as a likely emergency should not have
its outcome depend on a third-party LLM API being reachable, authenticated,
and correct at that moment. `test_red_flag_case_short_circuits_without_calling_backend`
asserts `fake.called is False` — the guarantee is proven, not just claimed
in a docstring.

**The question an interviewer will actually ask:**
*"What happens if the LLM API is down during an emergency case?"*
→ *"Nothing happens to it — the emergency path never touches the LLM at
all. That's the entire point of Entry 1's red-flag scan and this
short-circuit working together."*

---

## Entry 5 — A real bug, caught by actually running the code, not assumed away

**Where:** `app/main.py`, the `/triage` endpoint, first version vs. current version.

**What happened:** the first version of the `/triage` handler constructed
`AnthropicReasoningBackend()` unconditionally, before checking whether the
case even needed it. Result: a red-flag emergency case — the one path that
is supposed to work with **zero dependency on the LLM** — returned a 503
"backend not configured" error when no API key was set, because backend
construction happened before the short-circuit logic ever ran.

**How it was caught:** by curling the live endpoint with `ANTHROPIC_API_KEY`
unset, exactly the condition this project will actually run under until a
key is added. The bug was invisible in the code on paper — it only showed
up under execution.

**The fix:** move the red-flag check in front of backend construction, so
the safety-critical path never even tries to build a network client.

**The question an interviewer will actually ask:**
*"Tell me about a bug you found in your own project."*
→ this one, verbatim. It's a better answer than "no bugs, it worked first
try" — it shows you test the failure paths, not just the happy path, and
that you understand *why* the ordering mattered, not just that it broke.

---

## Guideline-Verification Agent — Q&A form

This section is deliberately Q&A, not prose — the shape of an actual
interview, not an essay about the code. Every answer below is checkable
against a real file in this repo, run today, not theory.

---

**Q: What does the Guideline-Verification Agent actually do?**
A: It takes the Triage-Reasoning Agent's proposed level (`app/agents/triage.py`)
and checks it against a corpus of guideline text (`data/guidelines/seed_guidelines.json`)
using TF-IDF retrieval (`app/agents/verify.py`). If a matched guideline implies
something *more* severe than what the LLM proposed, it escalates. It never
lowers a level based on retrieval.

**Q: Why TF-IDF instead of a transformer embedding model — isn't that the "less advanced" choice?**
A: It's the *right-sized* choice, not a lesser one. The corpus is a few dozen
short, domain-specific chunks where exact medical-term overlap ("chest pain,"
"slurred speech") is already a strong signal. `sentence-transformers` would add
a multi-hundred-MB dependency and real inference latency for a retrieval
problem this size gains almost nothing from. I'd revisit this the moment the
corpus grows into the hundreds of documents, or needs to match heavily
paraphrased wording TF-IDF can't see. Knowing *when* the simple tool stops
being the right one is the actual signal here, not defaulting to the fanciest
option available.

**Q: Why is escalation asymmetric — why can't a guideline match ever lower the proposed level?**
A: Because the two failure modes aren't equally bad. Escalating on an
imperfect match costs an unnecessary clinic visit. De-escalating on an
imperfect match could downgrade a real emergency. `verify_triage_decision`
in `app/agents/verify.py` only ever raises the level, never lowers it —
proven in `test_verify_never_deescalates_even_with_a_mild_top_match`, not
just claimed in a comment.

**Q: Walk me through a real bug you found while building this.**
A: The first version of `top_matches()` returned the top-3 matches with no
relevance floor. For the query "mild headache, no visual changes or
confusion," the correct match scored 0.70 cosine similarity — but a
completely unrelated fever guideline scored 0.10 just for sharing the word
"mild," and because it ranked #2 in the top-3, it was allowed to vote on
escalation and incorrectly pushed a self-care case to clinic-visit. I found
it by actually running `pytest`, not by reading the code and assuming it
was right. Fixed by adding a `min_similarity=0.2` floor — a real, measured
threshold sitting between the ~0.6-0.7 cluster of genuine matches and the
~0.09-0.10 cluster of incidental one-word overlaps in this corpus, not a
guessed number. `test_top_matches_filters_out_weak_incidental_overlap` is
the regression test.

**Q: What happens if no guideline chunk matches at all?**
A: The proposed level passes through unchanged, and a warning is logged
(`app/agents/verify.py`, `verify_triage_decision`). It fails toward "trust
the LLM's proposal," not toward silently doing nothing — the alternative,
raising an error or defaulting to self-care, would be worse in both
directions.

**Q: How does this map to what GPREC actually teaches?**
A: Directly — this is the practical form of the Explainable AI & Model
Interpretability elective (§08 of the placement roadmap): a decision that
comes with a retrievable, human-readable reason ("escalated on guideline
match: ...") instead of a bare label. It's also the reason a TCS Prime-style
"defend your AI project" interview or a SAP Labs live-coding round holds up
here — every design choice above has a concrete, evidenced answer, not a
hand-wave.

---

## Referral Agent — Q&A form

**Q: What does the Referral Agent actually do?**
A: Takes the verified `TriageDecision` and turns it into exactly one of
three things: self-care instructions, a named facility with a timing
window ("as soon as possible today" vs. "within the next day or two"),
or the emergency escalation message. Never a diagnosis, never a
prescription — see `app/agents/referral.py`, `run_referral()`.

**Q: Why does the emergency path skip the facility lookup entirely, instead of pointing to the nearest hospital?**
A: Speed and certainty. A facility lookup is one more thing that could be
slow, wrong, or point to a facility that's shut. The emergency message
tells the patient to act *now* — go to the nearest hospital or call for
transport — rather than waiting on this system to compute a "best"
answer. Same reasoning as Entry 4's red-flag short-circuit in
`app/agents/triage.py`: the highest-stakes path is also the simplest and
fastest one, on purpose.

**Q: Why does "nearest facility" just return the first entry in a list instead of actually finding the nearest one?**
A: Because computing a real "nearest" would need live location data and
a maintained, complete district directory — Kurnool district alone has
around 88 PHCs, and building that pipeline honestly is a separate project.
The MVP scope is stated plainly, not disguised: name one real, verified
facility a patient can act on. `test_load_facilities_reads_the_bundled_kurnool_directory`
checks that the facility actually returned is the one independently
verified against Kurnool district's own government portal, not a
placeholder — a real interviewer question ("is that data real?") has a
real, checkable answer.

**Q: Is the facility data real?**
A: Two of three entries are — verified against Kurnool district's own
government portal (`kurnool.ap.gov.in`) and a government-hospital
directory listing, both cited by source in `data/facilities/kurnool_facilities.json`.
The third is explicitly labeled `STARTER_PLACEHOLDER`, not silently
left looking real. Same honesty standard as the guideline corpus, applied
consistently rather than only where it was convenient the first time.

---

## Day 2 (26 Jul 2026) — OCR + CV classifier pipeline — Q&A form

**Q: What got built today?**
A: Two pieces of the perception layer. `app/models/ocr.py` — real
prescription/lab-report text extraction via Tesseract, tested against
genuine rendered images, not fixtures pulled from anywhere. And
`app/models/cv_classifier.py` — the complete image-urgency classifier
pipeline: a MobileNetV3-Small transfer-learning model, a real training
loop, a real inference function, and a `Dataset` class for loading
labeled images from disk.

**Q: Why MobileNetV3-Small instead of a bigger, more "impressive" model like ResNet50?**
A: ~2.5M parameters means it actually finishes fine-tuning on a laptop
or a free Colab GPU. A ResNet50 sounds more impressive in a sentence but
is the wrong-sized tool for a dataset this small and a training budget
this constrained — it would overfit faster and take longer to iterate
on. Only the classifier head is trained; the pretrained backbone is
frozen, standard transfer-learning practice for a small dataset.
`test_build_model_freezes_the_backbone_not_the_head` proves this, not
just states it.

**Q: Is this model trained? Can it actually classify a real skin image right now?**
A: No, and say this straightforwardly if asked — overclaiming here is
exactly the kind of thing that falls apart under one follow-up question.
There is no shipped weights file. What's proven is the *pipeline*: model
architecture, forward pass, training loop, and inference function all
work correctly, verified with `test_train_one_epoch_actually_reduces_loss`
- a real convergence test on synthetic images (plain solid-color squares,
explicitly not medical images) that would fail if backprop or the
optimizer wiring were broken. Training on real data (HAM10000, CC BY-NC
4.0 license, free for this non-commercial use) is the next real step,
gated on downloading it via a Kaggle account this environment doesn't
have configured.

**Q: Tell me about a wrong assumption you caught today.**
A: The OCR preprocessing step (grayscale + sharpen + autocontrast) is
standard advice for OCR pipelines, and I wrote it assuming it would
measurably help. I tested it empirically instead of shipping the
assumption: on a low-contrast synthetic image, raw Tesseract read
"AMOXICILLIN 250M" correctly, while the "improved" preprocessed version
misread it as "ANTONICILLIN 250" — a wrong drug name, which is a serious
failure mode for a health tool specifically. The code comment now says
exactly that, instead of the confident claim I started with. Caught by
running a real test before committing to the claim, not by getting
lucky.

**Q: Why does the OCR module raise an error on bad input instead of just returning an empty string?**
A: Because "the image was corrupt/undecodable" and "the image was a
genuinely blank prescription" are different situations that need
different handling downstream, and collapsing them into the same empty
string would hide that distinction from whatever calls this function.
`test_extract_text_raises_not_silently_empty_on_bad_input` and
`test_extract_text_on_genuinely_blank_image_returns_empty_not_an_error`
prove both halves of that design decision separately.

**Q: How does this map to GPREC coursework?**
A: Directly — Computer Vision & Image Processing and the AI &
System Programming Lab, both Sem V (§08 of the placement report),
are the exact courses this pipeline puts into practice. The transfer-
learning technique (freeze backbone, retrain head) is standard material
in any CV course; applying it to a real, defensible triage use case
instead of a generic Kaggle exercise is the differentiator §09 already
established.

**Q: Why does this matter for the 2028 market specifically?**
A: It doesn't introduce a new claim beyond what's already verified in
the placement report — multimodal perception (text + image) is part of
what makes an agentic system look like a real product instead of a
chatbot wrapper, which is the exact distinction §05's recruiter research
flagged as separating a rejected project from a shipped one.

---

## Day 3 (27 Jul 2026) — Docker deployment — Q&A form

**Q: What got built today?**
A: A real, complete Docker deployment for the FastAPI app — `Dockerfile` and
`.dockerignore` at the repo root. Not a placeholder: the image was actually
built (`docker build -t carepilot:latest .`), actually run
(`docker run -d -p 8000:8000 --name carepilot-test carepilot:latest`), and
actually curled from the host — `curl http://localhost:8000/health` returned
`{"status":"ok"}` with HTTP 200, and Docker's own `HEALTHCHECK` independently
reported `"Status":"healthy"` a few seconds later. The test container was then
stopped and removed, same discipline as every other piece of this project:
proven by running it, not claimed from reading the code.

**Q: Walk me through the structure of the Dockerfile — why each piece?**
A: `python:3.13-slim` as the base, not alpine — `torch`/`scikit-learn` ship
`manylinux` wheels built against glibc, and alpine's musl libc would force
building `torch` from source, which is impractical for a dependency this
size. Dependencies are installed (`COPY requirements.txt .` then
`pip install`) *before* `COPY app ./app` — a layer-ordering choice, not
cosmetic: editing application code shouldn't invalidate and re-run the
slowest layer in the whole build. `tesseract-ocr` is installed via `apt-get`
because `app/models/ocr.py` imports `pytesseract`, which is only a thin
wrapper around the `tesseract` binary — the Python package installs fine
without it, then fails at runtime the first time OCR is actually called,
which is a worse failure mode (looks fine until someone hits that one
endpoint) than catching it at image-build time. The container runs as a
non-root user (`useradd --uid 1000 carepilot`, then `USER carepilot`) because
this app never needs root — no privileged ports, no system file writes — so
running as root would be an unjustified privilege with no corresponding
benefit. And the `HEALTHCHECK` calls the app's *own* `GET /health`
(`app/main.py`) rather than a synthetic check, so "healthy" in `docker ps`
means the actual FastAPI process actually answered, not just that the
process didn't crash.

**Q: Be honest — how big is this image, and why?**
A: 1.82 GB, measured directly from `docker images` on this machine, not
estimated. That's real and it's not hidden in a comment nobody reads — it's
called out explicitly in `README.md`'s new Deployment section. The reason is
equally real, not mysterious: `docker history` shows the `pip install`
layer alone is 969 MB, almost entirely `torch==2.7.1` and
`torchvision==0.22.1` (needed for `app/models/cv_classifier.py`) plus
`scikit-learn` (needed for `app/agents/verify.py`'s TF-IDF retrieval). The
`apt-get install tesseract-ocr libgl1 libglib2.0-0` layer adds another
300 MB on top. A multi-stage build was considered and deliberately not used
here — it would shrink nothing, because the size lives in the installed
package payload itself (torch's bundled CUDA/cuDNN runtime libraries this
CPU-only app never calls), not in leftover build tooling a multi-stage build
would discard. The one lever that would actually help — pulling a CPU-only
torch wheel from `download.pytorch.org`'s `-cpu` index instead of the
default PyPI wheel — was deliberately not applied, so this image installs
`requirements.txt` exactly as pinned, unmodified. That's a real, named
follow-up, not a claim that today's Dockerfile is already optimal.

**Q: Why Hugging Face Spaces as the first deployment target, and not AWS or Azure?**
A: Free, and it takes a Dockerfile directly with no translation step — push
this repo's actual `Dockerfile` to a Space's git remote and it builds as-is.
AWS (ECS/App Runner) and Azure (Container Apps) are both real, legitimate
options for later, but both need a billing-enabled cloud account and more
infrastructure configuration (task definitions, container registries, IAM)
before a single request can be served — overhead a student project proving
"this runs in a container" on day one doesn't need yet. HF Spaces gets to a
working public URL fastest, which is the actual question at this stage:
prove it deploys, not prove it scales.

**Q: What's the one HF-Spaces-specific detail that would silently break this deployment if missed?**
A: Port mismatch. HF's Docker Spaces route incoming traffic to port 7860 by
default — not 8000, which is what this repo's `Dockerfile` uses to match
the app's own documented local convention (`README.md`, "Running it"). Get
this wrong and the Space builds successfully, shows no error anywhere, and
just times out on every request — the single most confusing failure mode
for a first deployment, because the build log looks completely clean. The
fix documented in `README.md`'s Deployment section doesn't touch the
Dockerfile at all: add `app_port: 8000` to the YAML metadata block at the
top of the *Space's* `README.md` (a file HF Spaces itself reads for `sdk`,
`app_port`, etc., separate from this repo's own `README.md`), which tells
HF's proxy to route to the port this image actually listens on. That keeps
the exact Dockerfile that was build-tested locally today identical across
both targets, instead of maintaining a second HF-only variant that could
quietly drift out of sync with the one that's actually been proven to work.

**Q: Was this actually pushed live to a public URL today?**
A: No, and that's stated plainly in `README.md` rather than implied by
omission. `docs/DAILY_PROTOCOL.md`'s own pre-authorization rules mark "any
deployment to a live public URL" and "pushing this repo to GitHub or any
remote" as needing an explicit go-ahead, not something pre-authorized by
default. What's actually done and provable today: the image builds, runs,
and answers `/health` correctly on this machine, and the exact HF Spaces
steps (including the port fix above) are documented accurately enough to
execute in one sitting once that go-ahead is given. Progress in
`README.md` reflects that distinction honestly — `[~]` (in progress), not
`[x]`.

**Q: How does this map to GPREC coursework?**
A: This is the deployment half of what the MLOps elective (§08 of the
placement report) is pointing at — the same "ship a smallest working
slice, prove it, then extend" discipline Entry 3 in this file already ties
to `app/main.py`'s one-agent-at-a-time API design, applied one layer up the
stack: not just "does the code work" but "does it run the same way outside
my own machine." Containerization and cloud deployment basics are also
directly Sem-relevant to any DevOps/cloud-computing elective GPREC offers
alongside the AI-focused ones already cited in this file.

**Q: Why does this matter for the 2028 market specifically?**
A: Because "I built an AI pipeline" and "I can put an AI pipeline somewhere
someone else can actually hit it" are different claims, and interviewers at
TCS Prime/Digital or Infosys Digital-Specialist level (the actual target
band recorded in `docs/DAILY_PROTOCOL.md`) test for the second one, not just
the first. A candidate who can also speak honestly about *why* an image is
1.82 GB instead of hand-waving past the question is demonstrating the same
"know what your own system doesn't do yet" signal Entry 1 of
`docs/INTERVIEW_NOTES.md` already established as the differentiator that
matters — applied here to infrastructure instead of model design.

---

## Day 3 (27 Jul 2026) — Bhashini vernacular (Telugu) adapter — Q&A form

**Q: What got built today?**
A: `app/adapters/bhashini.py` — a standalone adapter layer that turns
Telugu speech into English text for the intake pipeline. A
`BhashiniAdapter` Protocol with `transcribe()` and `translate()`,
a real implementation (`RealBhashiniAdapter`) that calls the actual
two-step MeitY/Dhruva Bhashini API over `httpx`, and a pure orchestration
function `bhashini_to_intake()` that chains transcribe → translate.
Tested end-to-end with a fake adapter in `tests/test_bhashini.py` — zero
network calls, zero credentials required to run the suite.

**Q: Why reuse the exact Protocol/fake-backend pattern from
`app/agents/triage.py` instead of designing something fresh for this?**
A: Because the problem shape is identical, not just similar. Triage
needed a component that (a) calls a real third-party API, (b) can fail
in ways outside this codebase's control (missing credentials, network
errors, rate limits), and (c) still has to be unit-testable without a
live API key sitting in CI. Bhashini has exactly the same three
properties. Inventing a different abstraction for a problem that's
already solved in this repo would be novelty for its own sake — worse,
it would mean two different conventions for "how do we talk to an
external AI service" in the same codebase, which is a maintenance cost
with no upside. `AnthropicReasoningBackend` → `RealBhashiniAdapter`,
`TriageBackendError` → `BhashiniAdapterError`, `FakeBackend` →
`FakeBhashiniAdapter`, `run_triage_reasoning(case, backend)` →
`bhashini_to_intake(adapter, audio_bytes)` — same shape, same reasons,
on purpose. If an interviewer asks "why does this look like the triage
file," that's the honest answer: consistency was the design goal, not
an accident of copy-paste.

**Q: Is the real Bhashini API integration actually verified?**
A: No — say this plainly, same standard as the CV classifier note from
Day 2. This environment has no `BHASHINI_USER_ID` / `BHASHINI_API_KEY`,
so no live call to `meity-auth.ulcacontrib.org` or
`dhruva-api.bhashini.gov.in` was made or could be made while building
this. The two-step request/response shape (pipeline-config call to get a
serviceId + per-session auth key, then the inference call using that
key) is transcribed from the community-maintained `bhashini-api` Python
wrapper on GitHub, which itself wraps the real endpoints — the best
available ground truth without credentials, but still second-hand, not
first-hand-confirmed. The module docstring in `bhashini.py` says this
directly, in a "Verification Status" section, so nobody reading the code
mistakes "shaped like the real API" for "proven to work against the real
API." What genuinely is proven, by `tests/test_bhashini.py`: the
credential-missing fail-fast path raises `BhashiniAdapterError` with a
clear message naming both required env vars, and `bhashini_to_intake()`
correctly calls `transcribe()` then feeds its output into `translate()`
— not the raw audio into both.

**Q: What happens if `BHASHINI_USER_ID` or `BHASHINI_API_KEY` is
missing?**
A: `RealBhashiniAdapter.__init__` raises `BhashiniAdapterError`
immediately, before any network attempt — it names whichever
variable(s) are missing in the message. Same "fail fast and clearly
instead of crashing three calls deep" standard as
`AnthropicReasoningBackend` in `app/agents/triage.py`. Three separate
tests cover this: missing user ID alone, missing API key alone, and both
missing at once with an assertion that both variable names appear in the
error text.

**Q: What's the honest gap here — what would break first if someone
plugged in real credentials today?**
A: Two knowns, stated instead of hidden. First, the `pipelineId` used
(`DEFAULT_PIPELINE_ID` in `bhashini.py`) is the one that shows up across
public Bhashini samples and the community wrapper, but it's not
confirmed still-valid — MeitY has been known to rotate or deprecate
pipeline IDs, and there's no way to check that without a live call.
It's a constructor parameter specifically so it can be overridden the
moment a real, current ID is available. Second, the response-parsing
code (`data["pipelineResponse"][0]["output"][0]["source"]` for ASR,
`["target"]` for translation) assumes a specific nesting that matches
the wrapper's documented examples — if Bhashini's real response has an
extra wrapping layer or a renamed field, that specific line breaks, not
the whole design. This is the same class of honesty as the OCR
preprocessing note from Day 2: state exactly what's assumed and what
would need a real credential + real call to confirm, rather than
implying more certainty than the environment allows.

**Q: How does this map to GPREC coursework / the placement narrative?**
A: This is the practical form of the multilingual/vernacular-access
story already flagged in the placement report — a rural Telugu-speaking
patient should not need to type or speak English to use this system.
Building it as an adapter layer that plugs into intake via a pure
function (`bhashini_to_intake`), rather than hard-wiring Bhashini calls
into `app/agents/intake.py` directly, is the same "isolated, individually
testable component" discipline Entry 2 already established for
`schemas.py` — Bhashini can be swapped, mocked, or dropped without
touching intake's own code or tests.

---

## What's next (so you know where we are)

- [x] Data contracts (`schemas.py`)
- [x] Intake Agent + rule-based safety net, tested and running
- [x] Triage-Reasoning Agent — LLM backend (Anthropic), Protocol-based for testability, retry/backoff, graceful 503 on missing credentials, red-flag short-circuit — tested and running
- [x] Guideline-Verification Agent — TF-IDF retrieval, asymmetric escalation-only logic, one real bug found and fixed with a regression test — tested and running
- [x] Referral Agent — self-care/facility/emergency branching, sourced Kurnool facility data, tested and running — **all 4 core agents now wired into a complete `/assess` pipeline, verified end-to-end**
- [~] Docker + deployment — image builds and runs locally, `/health` verified end-to-end; Hugging Face Spaces steps documented but not yet pushed live
- [~] Bhashini vernacular layer — `app/adapters/bhashini.py` complete and tested against a fake adapter; real API integration honestly unverified without live credentials, and not yet wired into `app/agents/intake.py`
- [ ] SHAP/LIME explainability layer (applies to the CV classifier once built — not to the Anthropic call, see §15 of the placement report for why)
- [ ] CV image-triage model trained on real data, evaluation harness
