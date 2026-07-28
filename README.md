# CarePilot

Agentic rural health-triage and referral copilot. **A triage aid, not a
diagnostic tool** — every design decision below exists to route a person
to the right level of care, never to replace one.

Status: all four core agents built, tested, and running end-to-end via
`/assess`. See `docs/INTERVIEW_NOTES.md` for the reasoning behind each
decision as it was made — that file is the real changelog, including two
real bugs found and fixed.

## Problem

A first-mile triage question — "is this self-care, a clinic visit, or an
emergency" — answered for someone without easy doctor access, who may not
be English-fluent, and needs an answer now.

## Architecture

```
Patient input (text / voice / image)
        │
        ▼
  Intake Agent            ← done: normalizes input, runs a deterministic
        │                     red-flag keyword scan before any model sees it
        ▼
  Triage-Reasoning Agent   ← done: LLM proposes self-care / clinic / urgent /
        │                     emergency; red-flag cases short-circuit here
        ▼
  Guideline-Verification   ← done: TF-IDF retrieval over data/guidelines/,
        │                     escalation-only, never lowers a proposed level
        ▼
  Referral Agent           ← done: self-care instructions, a named facility,
                               or an emergency message - never a diagnosis
```

## Progress

- [x] Data contracts (`app/schemas.py`)
- [x] Intake Agent + rule-based emergency pre-filter (`app/agents/intake.py`) — tested, running
- [x] Triage-Reasoning Agent (`app/agents/triage.py`) — Anthropic backend, retry/backoff, graceful failure without a key, red-flag short-circuit — tested and running
- [x] Guideline-Verification Agent (`app/agents/verify.py`) — TF-IDF retrieval over a starter guideline corpus, escalation-only logic — tested and running
- [x] Referral Agent (`app/agents/referral.py`) — self-care/facility/emergency branching over a small, sourced Kurnool-district facility list — tested and running, full pipeline wired into `/assess`
- [~] CV image-triage model (`app/models/cv_classifier.py`, `app/models/ocr.py`) — OCR is complete and tested; the image classifier's full pipeline (model, training loop, inference) is real and tested against synthetic plumbing images, but **not yet trained on a real dataset** (HAM10000, CC BY-NC 4.0, needs a Kaggle account this environment doesn't have) and **not yet wired into `/assess`**
- [x] Bhashini (Telugu) input layer (`app/adapters/bhashini.py`) — Protocol + real `httpx`-based implementation, now wired into a live `POST /assess/voice` endpoint (`app/main.py`); **real API integration still honestly unverified** (no live `BHASHINI_USER_ID`/`BHASHINI_API_KEY` in this environment), but the orchestration logic is proven by `tests/test_main.py`
- [~] Docker deployment (`Dockerfile`, `.dockerignore`) — built and run locally, `GET /health` verified end-to-end (see `## Deployment` below); Hugging Face Spaces steps documented below but **not yet actually pushed live** — that's still a real next step, not done
- [ ] SHAP/LIME explainability report
- [ ] Evaluation: recall on emergency-flagged cases (the metric that matters, not accuracy)

## Running it

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

```bash
curl -X POST http://127.0.0.1:8000/assess \
  -H "Content-Type: application/json" \
  -d '{"symptom_text": "chest pain since this morning", "age": 45, "duration_days": 0}'
```

Telugu voice input, via the Bhashini adapter (real API calls need
`BHASHINI_USER_ID`/`BHASHINI_API_KEY` set, see Deployment below):

```bash
curl -X POST http://127.0.0.1:8000/assess/voice \
  -F "audio=@symptom.flac;type=audio/flac" \
  -F "age=45"
```

`/intake` and `/triage` also exist as narrower, independently testable slices of the same pipeline — see `app/main.py`.

Automated tests for all of this, including live HTTP requests through
the real FastAPI app (not just the underlying functions), live in
`tests/test_main.py`.

## Deployment

### Docker — built and run locally, verified

The `Dockerfile` (`python:3.13-slim`, non-root user, `tesseract-ocr` installed via
apt for `app/models/ocr.py`, a `HEALTHCHECK` against the app's own `GET /health`)
was actually built and run on this machine, not just written:

```bash
docker build -t carepilot:latest .
docker run -d -p 8000:8000 --name carepilot-test carepilot:latest
curl http://localhost:8000/health
# {"status":"ok"}
docker stop carepilot-test && docker rm carepilot-test
```

Real results from that run: the build completed in `docker build`, `docker run`
started the container, `curl http://localhost:8000/health` returned
`{"status":"ok"}` with HTTP 200, and Docker's own `HEALTHCHECK` independently
reported `"Status":"healthy"` a few seconds later via `docker inspect`. The test
container was then stopped and removed — nothing was left running.

**Image size, honestly:** `docker images` reports **1.82 GB** for
`carepilot:latest`. That is not a placeholder number rounded down — it's real,
measured on this build, and it's large because the app's actual dependencies
are large: `docker history` shows the `pip install -r requirements.txt` layer
alone is **969 MB** (almost entirely `torch`==2.7.1 + `torchvision`==0.22.1 for
`app/models/cv_classifier.py`, plus `scikit-learn` for
`app/agents/verify.py`), and the `apt-get install tesseract-ocr libgl1
libglib2.0-0` layer is another **300 MB**. A multi-stage build doesn't shrink
this — the size is in the installed packages themselves, not build tooling
left behind. The one real lever (a CPU-only torch wheel from
`download.pytorch.org`'s `-cpu` index instead of the default PyPI wheel, which
bundles CUDA/cuDNN this app never uses on CPU-only inference) is a legitimate
follow-up but was deliberately not applied here, so this image installs
`requirements.txt` exactly as pinned, unmodified.

### Hugging Face Spaces (Docker SDK) — the fastest free path, documented, not yet pushed live

HF Spaces was chosen over AWS/Azure as the first deployment target because it's
free, requires no cloud account or billing setup, and takes a Dockerfile
directly — no translation to a different deploy format. AWS (ECS/App Runner)
and Azure (Container Apps) are both real options later, but both need a
billing-enabled account and more infrastructure config than a student project
demoing a working prototype needs on day one.

Real steps to deploy this repo's `Dockerfile` as-is:

1. On huggingface.co, create a new **Space** → SDK: **Docker** → visibility
   Public or Private as preferred.
2. Push this repo's contents (including `Dockerfile`) to the Space's own git
   remote (HF Spaces are themselves git repos):
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/<space-name>
   git push space main
   ```
3. **The port detail that actually matters:** HF's Docker Spaces route
   incoming traffic to **port 7860 by default**, not 8000. This repo's
   `Dockerfile` uses `EXPOSE 8000` / `uvicorn ... --port 8000` to match the
   app's own documented local convention (`README.md` "Running it", above) —
   deliberately *not* rewritten to 7860, since 8000 is correct for local
   `docker run` and any non-HF host. Two ways to reconcile that with HF
   Spaces specifically, without changing the Dockerfile for every deploy
   target:
   - **Preferred — tell HF to use this Dockerfile's real port:** add an
     `app_port: 8000` line to the YAML metadata block at the very top of the
     *Space's* `README.md` (HF Spaces reads this block for `sdk`, `app_port`,
     etc. — it's separate from this repo's own `README.md`). That's a one-line
     config change on the Space side, and the Dockerfile stays identical to
     what was built and tested locally above.
   - **Alternative — match HF's default instead:** override the port at
     `docker build`/deploy time for HF specifically (e.g. a build arg or a
     Space-side `CMD` override binding `uvicorn` to `0.0.0.0:7860`), leaving
     `EXPOSE 7860` for that target. Not done here because it would make the
     Dockerfile diverge from the version actually build-tested above for no
     real benefit — `app_port: 8000` in the Space's `README.md` is the
     smaller, safer change.
4. HF's free CPU tier is enough to *run* this app (no GPU is used anywhere in
   the current pipeline — `app/models/cv_classifier.py`'s model isn't wired
   into `/assess` yet, see Progress above), but expect a slow first build: at
   969 MB, the `pip install` layer alone is the dominant cost, same as the
   local build timed above.
5. `ANTHROPIC_API_KEY` (needed for `/triage` and `/assess` on non-red-flag
   cases — see `app/agents/triage.py`) is never baked into the image
   (`.dockerignore` excludes `.env`); on HF Spaces it's set as a **Secret** in
   the Space's Settings, not committed anywhere.

This documents the real steps; actually creating and pushing to a public Space
is a live deployment and — per `docs/DAILY_PROTOCOL.md`'s pre-authorization
rules — needs an explicit go-ahead first, so it wasn't done as part of this
session.

## Data sources — what's real, and what still needs replacing

- **Facilities** (`data/facilities/kurnool_facilities.json`): the first two entries are real, sourced facilities — one verified directly against Kurnool district's own government portal (kurnool.ap.gov.in), one from a government-hospital directory listing. The third is an explicitly labeled placeholder pending a real PHC name from the district's own published PHC directory.
- **Guideline corpus** (`data/guidelines/seed_guidelines.json`): every entry is labeled `STARTER_SEED` — written for this repo, not extracted from a verified ICMR/WHO document. Replace before claiming "real government data" anywhere this project is presented.
- **Bhashini APIs** — real, government-run; the adapter layer (`app/adapters/bhashini.py`) is built and tested against a fake backend, but the real API calls are unverified without live credentials (see Progress above).
- **AIKosh / data.gov.in** — the intended source for the eventual CV-model training data and a larger, verified guideline corpus; not yet pulled in.

## Ethical framing (read before demoing this to anyone)

- Not diagnostic, ever — the system's only outputs are self-care guidance,
  a named facility referral, or an emergency flag.
- Health data used for evaluation must be public or de-identified.
  DPDP Act 2023 considerations apply if this ever handles real patient data.
- The metric that matters is **recall on emergency-flagged cases** — a
  missed emergency is a far worse failure than an unnecessary referral.
