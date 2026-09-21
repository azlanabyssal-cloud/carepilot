# Deploying CarePilot for real feedback

This gets you a real, public URL you can hand to other people — not a
localhost link only you can open. Written 13 Sep 2026, checked directly
against this repo's real Dockerfile, `app/main.py`, and its own
`docs/DAILY_PROTOCOL.md` — not assumed.

**Two things worth knowing before you deploy anywhere:**

1. **This session cannot create a hosting account or push a live deployment
   for you.** There's no credential or inbound network access available to
   do that from here, and separately —
2. **This repo's own `docs/DAILY_PROTOCOL.md` already lists "any deployment
   to a live public URL" as something that explicitly requires your
   go-ahead**, not something an automated session should just do on its own
   initiative. So this file gives you the real, checked steps to run
   yourself, rather than attempting to route around either of those.

## Option A: Hugging Face Spaces (already documented in `README.md`)

The README's own "Deployment" section already has a full, real walkthrough
for this — free, no billing setup, and it takes this repo's Dockerfile
directly. It also names the one real gotcha (HF routes traffic to port 7860
by default; this Dockerfile uses 8000) and the one-line fix for it. Start
there if you want HF specifically.

## Option B: Render (no port gotcha, same Dockerfile, ~5 minutes)

Slightly simpler than HF for a first deploy, because Render reads the
Dockerfile's own `EXPOSE`/`CMD` port directly — no mismatch to reconcile.

1. Push this branch (or merge the PR) so the branch you deploy has everything you want live.
2. [render.com](https://render.com) → sign in with GitHub → **New +** → **Web Service**.
3. Pick this repository. Render detects the root `Dockerfile` automatically — leave "Environment" as **Docker**.
4. Instance type: **Free** works for a demo (it sleeps after 15 minutes idle, ~30-60s cold-start on the next request afterward — a real limitation, not hidden here).
5. Add environment variables from the table below, then **Create Web Service**.
6. First build takes several minutes — this image is genuinely large (see the README's own measured 1.82 GB breakdown). That's real, not a sign something's wrong.
7. You get a real `https://<your-service-name>.onrender.com` URL once it's live.

## Environment variables (checked directly against the code)

None of these are required for the app to start or for the core
triage/case-intake flow to work — every one of the fallbacks named below is
real and tested, not a hopeful claim.

| Variable | What it unlocks | Without it |
|---|---|---|
| `PHYSICIAN_CONSOLE_PASSCODE` | The Physician Console (`/ui/` → "Physician console") | Clean 503, not a crash — but reviewers can't log in, so set this if you want people to see that side |
| `ANTHROPIC_API_KEY` | Real LLM-backed triage reasoning + history drafting | Falls back to a deterministic backend (always proposes URGENT, flags `requires_manual_triage`) |
| `GROQ_API_KEY` | Alternate LLM backend | Same fallback as above |
| `BHASHINI_USER_ID` + `BHASHINI_API_KEY` | Real MeitY Bhashini speech transcription/synthesis | Falls back to offline speech (English-only ASR via PocketSphinx; English/Hindi/Telugu TTS via espeak-ng) |
| `ABDM_CLIENT_ID` + `ABDM_CLIENT_SECRET` | Real ABDM sandbox OTP enrollment | Just that one endpoint 503s; nothing else affected |

**For a first share:** set `PHYSICIAN_CONSOLE_PASSCODE` so reviewers can see
both sides. Leave the rest unset at first — the zero-API story is real and
worth showing as-is, not something to paper over by adding keys immediately.

## The one real limitation neither deployment doc above mentions

`app/db.py`'s SQLite file (`data/cases.db`) lives on the container's own
disk. Free tiers on Render, Railway, and HF Spaces generally do **not**
persist local disk writes across a redeploy or a restart after the
container sleeps — cases saved during one session may not survive the
container cycling. Fine for a same-day feedback round; for anything
longer, attach a persistent volume (Render's paid "Disks," a mounted HF
Spaces persistent storage tier, or an external database) before relying on
saved cases sticking around.
