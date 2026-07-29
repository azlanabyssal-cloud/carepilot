# CarePilot Study Guide

Grows by day, tiered by difficulty and format. Every answer below is
checkable against real, running code in this repo — nothing here is
theory that isn't also demonstrated somewhere in `app/`. If you can't
point to the file and line while answering, don't use the answer yet -
go read the code first.

**How to use this before an interview:** read Tier 1 once to refresh
vocabulary. Read Tier 2 and be able to say every "why this, not that"
from memory. Do Tier 3 with the file actually open, tracing it yourself
before checking the answer. Do Tier 4 with your editor open, no looking
at the repo's own solution until you've tried. Tier 5 is for when an
interviewer pushes past "does it work" into "would you ship this."

---

# Day 2 (26 Jul 2026) — OCR + CV Classifier Pipeline

## Tier 1 — Fundamentals (the vocabulary check)

**Q: What is OCR, in one sentence?**
A: Optical Character Recognition — turning an image containing text
into machine-readable text. Tesseract (the engine this project uses) is
a trained model that recognizes character shapes and assembles them
into words and lines.

**Q: What is transfer learning?**
A: Taking a model already trained on a large, general dataset (here,
MobileNetV3-Small pretrained on ImageNet — millions of general photos)
and reusing its learned features for a new, smaller, more specific task
instead of training a model from random weights. `app/models/cv_classifier.py`,
`build_model()`.

**Q: What does "freezing" a layer mean, mechanically?**
A: Setting `param.requires_grad = False` on every parameter tensor in
that layer. During training, gradients are still computed for the
forward pass but backpropagation skips updating frozen parameters — the
optimizer never touches them. Only parameters with `requires_grad = True`
(here, just the final classifier layer) get updated.

**Q: What is cross-entropy loss, and why is it the right choice here?**
A: A loss function for classification that measures how far the
model's predicted probability distribution is from the correct answer
— it penalizes confident wrong answers heavily and rewards confident
correct ones. `train_one_epoch()` uses `nn.CrossEntropyLoss()`, the
standard choice for any multi-class classification problem with
mutually exclusive classes (which `URGENCY_CLASSES` is — an image is
exactly one of low/moderate/high concern, never two at once).

**Q: What's the difference between `model.train()` and `model.eval()`?**
A: They change the behavior of certain layers (dropout, batch norm)
between training and inference modes — dropout is active in `.train()`
and disabled in `.eval()`. This model doesn't use dropout or batch norm
directly, but calling the right mode is still correct practice because
the pretrained backbone's internal layers do use batch norm, and
leaving it in train mode during inference would use batch statistics
from whatever tiny batch you're predicting on instead of the stable
learned statistics — `predict()` calls `model.eval()` for exactly this
reason.

**Q: Why normalize images with `mean=[0.485, 0.456, 0.406]`, `std=[0.229, 0.224, 0.225]`?**
A: Those are the exact per-channel statistics of the ImageNet dataset
MobileNetV3 was pretrained on. Feeding it images normalized the same
way keeps the input distribution consistent with what the pretrained
weights expect — using different normalization would silently degrade
the pretrained features' usefulness, even though the code would run
without error.

**Q: What is a PyTorch `Dataset` and `DataLoader`, and why two separate classes?**
A: `Dataset` (here, `ImageFolderDataset`) defines how to get one sample
by index — it doesn't know about batching. `DataLoader` wraps a
`Dataset` and handles batching, shuffling, and (optionally) parallel
loading. Separating them means the same `Dataset` can be reused with
different batch sizes or shuffling strategies without rewriting data-
loading logic.

---

## Tier 2 — Design decisions (the "why this, not that" set)

**Q: Why MobileNetV3-Small instead of ResNet50?**
A: ~2.5M parameters vs. ResNet50's ~25M — it actually finishes fine-
tuning on a laptop or free Colab GPU in reasonable time. A bigger model
sounds more impressive in a sentence but is wrong-sized for a small
dataset and constrained training budget; it would overfit faster and
iterate slower. `test_build_model_freezes_the_backbone_not_the_head`
proves the backbone-freezing half of this decision, not just states it.

**Q: Why raise `OcrError` instead of returning an empty string on bad input?**
A: "Corrupt/undecodable image" and "genuinely blank prescription" are
different situations that need different handling downstream — collapsing
them into the same empty string would hide that distinction from
whatever calls this function. Proven in two separate tests:
`test_extract_text_raises_not_silently_empty_on_bad_input` and
`test_extract_text_on_genuinely_blank_image_returns_empty_not_an_error`.

**Q: Why test the CV pipeline against synthetic solid-color images instead of waiting for a real dataset?**
A: Because "does the plumbing work" (data loads, tensors have the right
shape, backprop actually reduces loss) and "is this accurate on real
skin images" are two different claims, and only the first one can be
honestly tested right now. Waiting for the real dataset before writing
any tests would mean shipping untested code in the meantime.

**Q: What's the license situation on the dataset this is meant to train on?**
A: HAM10000, CC BY-NC 4.0 — free for academic/non-commercial use, which
covers a portfolio project, but would need a different license or
authors' permission before any commercial use. Requires a Kaggle account
or Harvard Dataverse access to actually download, neither configured in
this environment yet.

---

## Tier 3 — Code-reading (trace it yourself first, then check)

**Q: Trace `predict()` step by step. What's the tensor shape at each line, for a single 300×300 RGB image?**
A: Verified by actually running it, not guessed:
```
transform(image)                     -> torch.Size([3, 224, 224])
.unsqueeze(0)                        -> torch.Size([1, 3, 224, 224])
model(batched) [the logits]          -> torch.Size([1, 3])
torch.softmax(logits, dim=1)         -> tensor([[0.3305, 0.3373, 0.3322]]), sums to 1.0
```
`.unsqueeze(0)` adds a batch dimension of 1 at position 0 — channel,
height, and width are unchanged. The logits shape `[1, 3]` reads as one
row (the single image) by three columns (one score per
`URGENCY_CLASSES` entry). The softmax output is close to uniform
(~0.33 each) because the classifier head is freshly initialized and
untrained — a real interview follow-up ("why are the probabilities all
close to 1/3?") has a real answer: random init, not a bug.

**Q: What happens if `extract_text()` is called with `None` instead of bytes — does it crash with an unhandled `TypeError`?**
A: No — verified, not assumed. `io.BytesIO(None)` does not raise;
`Image.open()` on the resulting empty buffer fails with "cannot
identify image file," which the broad `except Exception` clause catches
and converts to `OcrError`. This looks like it might be an unhandled
edge case if you only read the code — it isn't. Worth checking behavior
empirically before flagging something as broken, in an interview or
anywhere else.

**Q: In `ImageFolderDataset`, what happens if you index past the end, e.g. `dataset[999]` on a 1-item dataset?**
A: A plain `IndexError: list index out of range` — verified. This is
Python's built-in list indexing on `self.samples`, not custom code. No
bounds-checking was written on purpose: the standard library already
provides the correct, expected behavior, and writing custom logic to
re-implement it would be adding code that doesn't need to exist.

**Q: Walk through `train_one_epoch()` line by line — what would happen if `optimizer.zero_grad()` were removed?**
A: Gradients would accumulate across batches instead of resetting each
step, since PyTorch adds new gradients to existing `.grad` tensors by
default rather than replacing them. The model would effectively train
on a distorted, ever-growing gradient signal — loss would likely
behave erratically or diverge rather than the clean decrease
`test_train_one_epoch_actually_reduces_loss` currently proves.

---

## Tier 4 — Code exercises (try before reading the answer)

**Exercise: Write a function `predict_batch(model, images: list[Image.Image], device="cpu") -> list[ClassificationResult]` that classifies multiple images in one forward pass instead of calling `predict()` in a loop.**

<details>
<summary>One correct approach</summary>

```python
def predict_batch(model: nn.Module, images: list[Image.Image], device: str = "cpu") -> list[ClassificationResult]:
    model.eval()
    transform = get_inference_transform()
    batch = torch.stack([transform(img.convert("RGB")) for img in images]).to(device)

    with torch.no_grad():
        logits = model(batch)
        probabilities = torch.softmax(logits, dim=1)
        confidences, predicted_indices = torch.max(probabilities, dim=1)

    return [
        ClassificationResult(label=URGENCY_CLASSES[idx.item()], confidence=conf.item())
        for idx, conf in zip(predicted_indices, confidences)
    ]
```
The interview-relevant point isn't the syntax — it's *why* batching
matters: one forward pass over N images is dramatically faster than N
separate forward passes, because the GPU/CPU does the matrix math for
the whole batch in parallel instead of paying per-call overhead N times.
</details>

**Exercise: The current OCR tests don't cover a rotated image. Write a test that asserts `extract_text` on a 90-degree-rotated real text image either still works or fails gracefully — don't guess which, run it and find out.**

<details>
<summary>What actually happens, verified by running it</summary>

Rotating a rendered "PARACETAMOL 500MG" image 90° and running it
through `extract_text()` returns garbled text — literally
`'‘W00STOMMLaORE'` in one real run — not an exception. Tesseract
doesn't auto-detect rotation by default, so it tries to read sideways
text as if it were upright and produces nonsense rather than failing
loudly. The real, runnable test:
```python
def test_extract_text_on_rotated_image_does_not_crash():
    image_bytes = _render_text_image("PARACETAMOL 500MG")
    image = Image.open(io.BytesIO(image_bytes)).rotate(90, expand=True)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    result = extract_text(buffer.getvalue())  # must not raise

    assert isinstance(result, str)  # garbled output is expected, a crash is not
```
This is a real, honest limitation worth naming in an interview if asked
"does this handle photos taken at an angle?" — the honest answer is
"not yet, and here's what would need to change": orientation detection
via Tesseract's OSD (orientation and script detection) mode, one of the
three language data files already installed alongside `eng`.
</details>

**Exercise: `build_model()` currently hardcodes MobileNetV3-Small. Refactor it to accept a `backbone: str` parameter supporting `"mobilenet_v3_small"` and `"resnet18"`.**

<details>
<summary>One correct approach</summary>

```python
from torchvision.models import ResNet18_Weights, resnet18

def build_model(num_classes: int = len(URGENCY_CLASSES), pretrained: bool = True, backbone: str = "mobilenet_v3_small") -> nn.Module:
    if backbone == "mobilenet_v3_small":
        weights = MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
        model = mobilenet_v3_small(weights=weights)
        for param in model.features.parameters():
            param.requires_grad = False
        in_features = model.classifier[-1].in_features
        model.classifier[-1] = nn.Linear(in_features, num_classes)
        return model
    elif backbone == "resnet18":
        weights = ResNet18_Weights.DEFAULT if pretrained else None
        model = resnet18(weights=weights)
        for param in model.parameters():
            param.requires_grad = False
        model.fc = nn.Linear(model.fc.in_features, num_classes)
        return model
    else:
        raise ValueError(f"Unknown backbone: {backbone}")
```
The real point to make out loud: this is the kind of change a live-
coding interviewer asks for specifically to see if you understand *why*
the freezing logic differs between architectures — MobileNetV3 exposes
`.features`/`.classifier`, ResNet exposes a flat structure ending in
`.fc`. Knowing that difference, not just copying a pattern, is what
separates understanding from memorization.
</details>

---

## Tier 5 — Deep / production / "would you actually ship this" questions

**Q: This model isn't trained yet. If an interviewer asks "what's your plan to actually get this working," what's the real answer?**
A: Three concrete steps, in order: (1) download HAM10000 via a Kaggle
account, (2) reorganize it into `data/cv_training/<class>/*.jpg` per
`ImageFolderDataset`'s expected layout — HAM10000's own labels are per-
lesion-type (melanoma, nevus, etc.), so they'd need remapping into this
project's coarser urgency buckets, a real design decision to make and
document, not hide; (3) run `train_one_epoch()` in a loop with a
validation split and early stopping, on a free-tier Colab GPU.

**Q: How would you monitor this model for drift or degrading accuracy in production?**
A: Log every prediction's confidence score, not just the label — a
rising rate of low-confidence predictions over time is an early signal
the input distribution has shifted from training data (new phone camera
models, different lighting, different patient population). This project
doesn't have that logging built yet — an honest gap, not a solved
problem.

**Q: Why does "recall on emergency-flagged cases" matter more than overall accuracy, concretely, for this specific model?**
A: A missed high-concern image (false negative) means a patient who
needed urgent care doesn't get flagged — the worst possible failure
mode for a triage tool. An unnecessary high-concern flag (false
positive) costs an avoidable clinic visit — annoying, not dangerous.
Optimizing for overall accuracy treats both errors as equally bad, which
they aren't here; recall on the high-concern class specifically is the
number that should drive any future threshold-tuning decision.

**Q: Why does this matter in the 2028 hiring market, specifically, not just "AI is popular"?**
A: This doesn't introduce a new market claim beyond what's already
verified in the placement report (§03, §09) — multimodal perception
(text + image, combined through an agentic pipeline) is precisely the
kind of "real product, not a chatbot wrapper" signal that report's
recruiter research identified as separating a shipped project from a
rejected one. The differentiator isn't "used PyTorch" — every batchmate
building an AI project will have done that. It's the combination of a
tested, honestly-scoped pipeline with a documented plan for the part
that isn't done yet.

---

# Day 3 (27 Jul 2026) — Docker Deployment + Bhashini Adapter

## Tier 1 — Fundamentals

**Q: What is a container, in one sentence, and how is it different from a VM?**
A: A container packages an application with its exact dependencies and
runs it isolated from the host, sharing the host's kernel — a VM
virtualizes an entire separate OS and kernel underneath it. Containers
start in seconds and are far lighter because there's no second kernel to
boot; the tradeoff is a weaker isolation boundary than a full VM.

**Q: What does a Docker `HEALTHCHECK` actually do, mechanically?**
A: Docker runs the specified command inside the running container on an
interval (`--interval=30s` here) and marks the container `healthy` or
`unhealthy` based on its exit code — visible in `docker ps` and
queryable via `docker inspect`. It's not cosmetic: orchestrators (Docker
Compose, Kubernetes, HF Spaces) can use this status to decide whether to
route traffic to a container or restart it.

**Q: What's a Docker build "layer," and why does layer order matter?**
A: Each instruction in a Dockerfile (`RUN`, `COPY`, etc.) creates a
cached layer; if a layer's inputs haven't changed, Docker reuses the
cached result instead of re-running it. That's exactly why
`carepilot`'s Dockerfile copies `requirements.txt` and runs `pip install`
*before* copying the application code — editing `app/` on a rebuild
doesn't invalidate the slow `pip install` layer, so rebuilds after a
code change are fast instead of re-downloading everything.

**Q: What is an API adapter/client pattern, in one sentence?**
A: Code that translates between your application's internal interface
and a specific external service's actual request/response format —
isolating "how Bhashini's API happens to be shaped" behind a stable
interface (`BhashiniAdapter`) so the rest of the app never has to know
or care.

**Q: What does `httpx.raise_for_status()` do, and why call it instead of checking `response.status_code` manually?**
A: It raises `httpx.HTTPStatusError` if the response status is 4xx/5xx,
otherwise does nothing. Using it instead of a manual `if` check means
error handling is centralized at one call site (`_post_inference` /
`_get_pipeline_config` in `bhashini.py`) rather than repeated at every
call site — one line covers every non-2xx response instead of a
forgettable manual check.

---

## Tier 2 — Design decisions

**Q: Why `python:3.13-slim` instead of `python:3.13-alpine` for a smaller image?**
A: `torch` and `scikit-learn` ship prebuilt `manylinux` wheels linked
against glibc. Alpine uses musl libc instead, which means pip can't use
those prebuilt wheels and would try to compile torch from source — slow,
fragile, and impractical for a dependency this large. The "smaller base
image" instinct is right in general; here it would trade a smaller base
for a broken or multi-hour build.

**Q: Why is the Bhashini pipeline ID a constructor parameter instead of a fixed constant?**
A: Because it's explicitly unverified — `DEFAULT_PIPELINE_ID` is the one
that appears across public samples and the community wrapper, not
confirmed live against Bhashini's real servers. Making it overridable
means the moment a real, current pipeline ID is available, nothing about
the class's shape needs to change — just the value passed in. Hardcoding
an unverified value as a constant with no escape hatch would have been
the wrong call twice: unverified, and rigid.

**Q: Why wrap `KeyError`/`IndexError` into `BhashiniAdapterError` in the response-parsing code instead of letting them propagate?**
A: Because a raw `KeyError: 'pipelineResponse'` tells a caller nothing
about *what* failed or why — it looks identical to a bug in unrelated
code. Wrapping it into `BhashiniAdapterError` with a message naming the
`task_type` and the raw exception keeps the failure mode identifiable:
"the Bhashini response didn't have the shape we expected," not "some
dict lookup somewhere failed."

---

## Tier 3 — Code-reading (real, verified output)

**Q: What's the actual measured size of the built image, and where does it come from — trace it.**
A: `docker images carepilot:latest` reports **1.82 GB** disk usage,
verified directly on this machine, not estimated from reading the
Dockerfile. `docker history` attributes it: the `pip install
-r requirements.txt` layer alone is **969 MB** (torch + torchvision +
scikit-learn), the `apt-get install tesseract-ocr libgl1 libglib2.0-0`
layer is **300 MB**, and the remainder is the `python:3.13-slim` base
image itself plus the small application code layer. Being able to name
which specific layer costs what — not just "it's kind of big" — is the
actual signal an interviewer is checking for.

**Q: Trace `bhashini_to_intake()` for a real (fake-backend) test case. What gets called, in what order, with what arguments?**
A: From `tests/test_bhashini.py`, `test_bhashini_to_intake_chains_transcribe_then_translate`:
```
bhashini_to_intake(fake, b"fake-flac-bytes")
  -> fake.transcribe(b"fake-flac-bytes", source_language="te")
       -> returns "నాకు జ్వరం గా ఉంది" (the fake's canned transcript)
  -> fake.translate("నాకు జ్వరం గా ఉంది", source_language="te", target_language="en")
       -> returns "I have a fever" (the fake's canned translation)
  -> bhashini_to_intake returns "I have a fever"
```
The test asserts `fake.translate_calls == [(fake._transcript, "te", "en")]`
— proving `translate` was called on the *transcript*, not on the raw
audio bytes a second time. That's the one-line difference between
"chained correctly" and "both steps ran but on the wrong input," and
it's checked explicitly, not assumed from the code reading correctly.

**Q: What does `docker inspect` actually show for the `HEALTHCHECK` status, and when does it flip to healthy?**
A: On this real run, `docker inspect` showed `"Status": "unhealthy"` (or
`"starting"`) immediately after `docker run`, because `--start-period=15s`
gives the app time to boot before the first check counts against it —
then flipped to `"Status": "healthy"` a few seconds later once
`curl -f http://localhost:8000/health` inside the container started
succeeding. The `--start-period` grace window is why a freshly-started
container isn't marked unhealthy just because uvicorn takes a moment to
come up.

---

## Tier 4 — Code exercises

**Exercise: The Dockerfile currently installs `torch` from the default PyPI index, which bundles CUDA/cuDNN this CPU-only app never uses. Rewrite the `pip install` step to use the CPU-only wheel index instead, and explain what you'd expect to happen to the 969 MB `pip install` layer.**

<details>
<summary>One correct approach</summary>

```dockerfile
RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.7.1 torchvision==0.22.1 \
    && pip install --no-cache-dir -r requirements.txt
```
(installing torch/torchvision first from the CPU-specific index, then the
rest of `requirements.txt` — pip will see they're already satisfied and
skip reinstalling them from the default index.) Expected effect: the CPU-
only torch wheel is meaningfully smaller than the default one because it
excludes the bundled CUDA/cuDNN shared libraries — this app never touches
a GPU in this deployment, so nothing is lost by dropping them. This is
named as a real, deliberately-deferred follow-up in today's notes, not
speculation — a legitimate live-coding exercise precisely because it's an
honest next step, not a solved problem being re-demonstrated.
</details>

**Exercise: Write a fake `BhashiniAdapter` that simulates a transcription failure (raises `BhashiniAdapterError`) and prove `bhashini_to_intake` propagates it rather than swallowing it.**

<details>
<summary>One correct approach</summary>

```python
class FailingBhashiniAdapter:
    def transcribe(self, audio_bytes: bytes, source_language: str = "te") -> str:
        raise BhashiniAdapterError("simulated ASR failure")

    def translate(self, text: str, source_language: str = "te", target_language: str = "en") -> str:
        raise AssertionError("translate should never be called if transcribe failed")


def test_bhashini_to_intake_propagates_transcribe_failure():
    with pytest.raises(BhashiniAdapterError, match="simulated ASR failure"):
        bhashini_to_intake(FailingBhashiniAdapter(), b"audio")
```
The `AssertionError` in the fake's `translate()` is the real point of the
exercise: it turns "translate silently got called anyway" from a subtle,
easy-to-miss bug into a loud, immediate test failure — the same
"prove the guarantee, don't just assume it" standard already used for
`_NullBackendNeverCalled` in `app/main.py`.
</details>

---

## Tier 5 — Deep / production questions

**Q: If this were deployed today and Bhashini's real API returned a response shape slightly different from what's assumed, what's the actual failure mode a user sees?**
A: A `KeyError` inside `_get_pipeline_config` or `transcribe`/`translate`,
caught and re-raised as `BhashiniAdapterError` with the field name that
was missing — not a silent wrong answer, not a crash with no context. The
Telugu-speaking patient using this feature would see whatever the calling
code (not yet built — intake isn't wired to Bhashini yet) chooses to show
on that error, which is itself an honest open question for whoever wires
it in next: fail the whole request, or fall back to asking for typed
English input?

**Q: Why does "builds and runs locally" not equal "production ready," and what specifically is still missing?**
A: Three concrete gaps, not a vague caveat: (1) no CI pipeline runs
`docker build` automatically on every push, so a future change could
silently break the image without anyone noticing until a manual rebuild;
(2) the image has never been pushed to a public registry or run outside
this one machine, so "works here" hasn't been tested against a different
host's environment; (3) there's no logging/monitoring wired into the
container beyond the `HEALTHCHECK` — a crash loop would show as
"unhealthy" but nothing captures *why*. Naming these precisely, instead
of a generic "needs more testing," is what separates a real production
conversation from a hand-wave.

**Q: Why does this matter for the 2028 market specifically?**
A: Same standard as every other "why does this matter" question in this
guide — no new claim, just applying what's already verified. A deployed,
containerized, multilingual-capable pipeline is the concrete evidence
behind "I can ship something real," which is exactly what separates a
TCS Prime/Digital or Infosys Digital-Specialist offer from the Ninja-tier
one, per `docs/DAILY_PROTOCOL.md`'s own target band. The Bhashini piece
specifically is also the one component in this whole project tied to a
named national mission (Bhashini/IndiaAI) rather than a generic AI
pattern — worth stating explicitly if an interviewer asks "why does this
project matter beyond being technically correct."

---

# Day 4 (28 Jul 2026) — Wiring Bhashini Into a Live Endpoint, Closing a Test Gap

## Tier 1 — Fundamentals

**Q: What is FastAPI's `TestClient`, and why does it not need a running server?**
A: `TestClient` wraps the ASGI app object directly (`from app.main import app`)
and sends requests straight into it in-process, using `httpx`'s ASGI
transport under the hood — no socket, no port, no separately running
`uvicorn` process. That's why `tests/test_main.py` can run in under a
second: it's not doing real network I/O, it's calling the app's own
routing/middleware stack directly in memory.

**Q: What's the practical difference between `File(...)` and `Form(...)` in a FastAPI route signature?**
A: `File(...)` declares a parameter as multipart file-upload data
(`UploadFile`, with a `.read()` method); `Form(...)` declares a parameter
as a regular multipart form field (a string, int, etc. sent alongside
the file). `/assess/voice`'s signature — `audio: UploadFile = File(...)`,
`age: Optional[int] = Form(default=None)` — mixes both because a real
voice-triage request needs an audio blob *and* structured metadata in
the same request, not two separate calls.

**Q: What does `monkeypatch.setattr` actually do, mechanically, in `test_assess_voice_wires_transcription_into_the_full_pipeline`?**
A: It temporarily replaces the `RealBhashiniAdapter` name inside the
`app.main` module's namespace with `FakeAdapter`, for the duration of
that one test, then automatically restores the original after the test
finishes (even if it fails) — pytest's `monkeypatch` fixture handles the
teardown. It works here specifically because `/assess/voice` references
`RealBhashiniAdapter` as a module-level name at call time, not a value
captured once at import — swapping the name before the request is made
is enough.

---

## Tier 2 — Design decisions

**Q: Why is `_run_pipeline()` a new extraction today, and not something that should have existed from Day 1?**
A: Because until today there was only one caller (`/assess`) — extracting
a shared function for logic used in exactly one place is premature
abstraction, the same anti-pattern this project's own standards (stated
back in the original scoping conversation) explicitly warn against.
The moment a second caller (`/assess/voice`) needed the identical
Triage→Verify→Referral tail, *that's* the correct moment to extract it
— not before, on the guess that it might be needed someday.

**Q: Why raise `HTTPException(503, ...)` for a missing Bhashini credential instead of `422` or `400`?**
A: `422`/`400` mean "the request itself was malformed" — but a request
to `/assess/voice` with a perfectly well-formed audio file is not
malformed; the *server's* dependency (Bhashini) isn't configured. `503
Service Unavailable` is the status code that means exactly that: the
server can't currently fulfill a valid request due to a dependency
issue, not a client error. Same reasoning `AnthropicReasoningBackend`'s
missing-key path already used for `/assess` and `/triage` — applied
consistently to the new endpoint rather than picked fresh.

**Q: Why test the credential-missing path for `/assess/voice` at the API layer, when `test_bhashini.py` already tests `BhashiniAdapterError` at the unit level?**
A: They're proving different things. `test_bhashini.py` proves
`RealBhashiniAdapter.__init__` raises the right error with the right
message. `test_main.py`'s version proves that error actually gets
caught by the *endpoint* and turned into a `503` HTTP response instead
of an unhandled 500 — the wiring between the two, which is exactly the
kind of thing that looks obviously correct on a read-through and turns
out not to be (see: Entry 5's backend-construction-order bug from Day
1, caught by testing the actual endpoint, not the underlying function).

---

## Tier 3 — Code-reading (real, verified)

**Q: Trace a request to `/assess/voice` with a red-flag-triggering translated result. What actually executes, in order?**
A: From `test_assess_voice_wires_transcription_into_the_full_pipeline`,
verified by running it:
```
POST /assess/voice (audio bytes, age=50)
  -> RealBhashiniAdapter() constructed  [substituted with FakeAdapter in this test]
  -> bhashini_to_intake(adapter, audio_bytes)
       -> adapter.transcribe(audio_bytes, "te") -> "raw telugu transcript"
       -> adapter.translate("raw telugu transcript", "te", "en") -> "chest pain and unconscious"
  -> PatientInput(symptom_text="chest pain and unconscious", age=50)
  -> run_intake(patient_input)
       -> scan_red_flags() finds "chest pain" AND "unconscious"
       -> CaseSummary.has_red_flag == True
  -> _run_pipeline(case)
       -> _run_triage(case): has_red_flag is True, short-circuits to EMERGENCY,
          _NullBackendNeverCalled is passed but never invoked
       -> verify_triage_decision(): level is already EMERGENCY, returns unchanged
       -> run_referral(): EMERGENCY -> no facility lookup, returns the fixed emergency message
  -> HTTP 200, {"level": "emergency", "message": "...", "facility": null}
```
Every one of those steps was already individually tested in earlier
days' test files — what's new and proven *today* is that they actually
chain together correctly starting from an audio upload, not just that
each piece works in isolation.

---

## Tier 4 — Code exercises

**Exercise: `/assess/voice` currently has no test proving the "audio decodes fine but transcription itself fails" case (e.g., Bhashini reachable but returns malformed audio error). Write one.**

<details>
<summary>One correct approach</summary>

```python
def test_assess_voice_fails_gracefully_when_transcription_fails(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    class FailingTranscribeAdapter:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, audio_bytes: bytes, source_language: str = "te") -> str:
            from app.adapters.bhashini import BhashiniAdapterError
            raise BhashiniAdapterError("simulated Bhashini ASR failure")

        def translate(self, text, source_language="te", target_language="en") -> str:
            raise AssertionError("translate should never run if transcribe failed")

    monkeypatch.setattr(main_module, "RealBhashiniAdapter", FailingTranscribeAdapter)

    response = client.post(
        "/assess/voice",
        files={"audio": ("symptom.flac", b"fake-audio-bytes", "audio/flac")},
    )

    assert response.status_code == 503
    assert "Bhashini" in response.json()["detail"]
```
The `AssertionError` inside `translate()` does the same job it did in
Day 3's `FakeBhashiniAdapter` exercise: turning "translate silently ran
anyway after transcribe failed" from a subtle bug into a loud, immediate
test failure if the endpoint's exception handling is ever refactored
incorrectly.
</details>

**Exercise: Extend `_run_pipeline()`'s docstring-implied contract into an actual test that proves `/assess` and `/assess/voice` produce byte-identical `ReferralResult`s for equivalent input.**

<details>
<summary>One correct approach</summary>

```python
def test_assess_and_assess_voice_agree_on_equivalent_input(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    text_response = client.post(
        "/assess",
        json={"symptom_text": "severe bleeding", "age": 40, "duration_days": 0},
    )

    class FakeAdapter:
        def __init__(self, *args, **kwargs): pass
        def transcribe(self, audio_bytes, source_language="te"): return "raw"
        def translate(self, text, source_language="te", target_language="en"):
            return "severe bleeding"

    monkeypatch.setattr(main_module, "RealBhashiniAdapter", FakeAdapter)
    voice_response = client.post(
        "/assess/voice",
        files={"audio": ("a.flac", b"x", "audio/flac")},
        data={"age": "40", "duration_days": "0"},
    )

    assert text_response.json() == voice_response.json()
```
This is the actual proof behind the design claim in `app/main.py`'s
docstring ("the same `ReferralResult` `/assess` produces") — asserting
it directly instead of trusting the comment that says so.
</details>

---

## Tier 5 — Deep / production questions

**Q: The daily cloud-automation routine has now failed 4 consecutive times, including a minimal diagnostic-only push test. What's the actual, precise conclusion — and what isn't concluded yet?**
A: Precisely: the cloud sandbox environment cannot push to this GitHub
repo. That's concluded with real evidence — not just "the complex daily
task is failing," which could mean many things, but "a 6-step diagnostic
whose only real action was one trivial commit+push also failed to change
anything on the remote," which isolates the failure to push access
specifically, not task complexity or timeout. What's genuinely *not*
concluded, because the tooling available doesn't expose the cloud
session's raw logs: the exact error text (auth failure vs. missing
remote credential vs. something else entirely). Naming the boundary
of what's actually known, instead of guessing past it, is the same
discipline as every other honest gap in this project.

**Q: Why does closing the "zero API tests" gap matter more, as a signal, than the specific tests written?**
A: Because it demonstrates something about process, not just output —
noticing a category of missing coverage that four days of otherwise
careful work had walked past, and treating "I should flag this and fix
it" as more valuable than quietly patching just the day's new feature.
An interviewer who asks "what would you do differently" about this
project has a real, concrete, positive answer available: nothing hidden,
one thing found and fixed the same day it was noticed.

**Q: Why does this matter for the 2028 market specifically?**
A: No new claim — same standard as every "why does this matter" question
in this guide. Full-stack ownership (an API that's actually tested, not
just a model that's actually trained) is precisely the "ship something
real" signal §09 of the placement report already established as the
differentiator. A candidate who can describe finding and closing a
testing gap in their own project, unprompted, is demonstrating exactly
the "know what your own system doesn't do yet" discipline this whole
study guide has tied to interview credibility since Day 2's OCR
preprocessing note — applied here to process, not just to one specific
technical claim.

---

# Day 5 (29 Jul 2026) — The Evaluation Harness

## Tier 1 — Fundamentals

**Q: Define recall and precision. Why does this project pick recall as the headline metric?**
A: Recall = true positives / (true positives + false negatives) — of all
the cases that were *actually* emergencies, what fraction did the system
catch. Precision = true positives / (true positives + false positives) —
of everything the system *called* an emergency, what fraction really
were. This project picks recall because the two failure modes aren't
equally bad: a false positive costs an unnecessary clinic referral; a
false negative (missing a real emergency) is the worst possible outcome
a triage tool can produce. Optimizing for precision or blended accuracy
would treat both errors as equal weight, which is the wrong model of the
actual cost.

**Q: What is a factory function/callable, and where is it used today?**
A: A function (or any callable) whose job is to produce an object when
called, rather than being the object itself. `evaluate_case(..., backend_factory)`
takes a zero-argument callable, not a constructed `ReasoningBackend` —
calling `backend_factory()` is deferred until the code actually needs a
backend, inside the `else` branch that only runs for non-red-flag cases.

**Q: What does a Pydantic `BaseModel` buy `EvaluationReport` here, versus a plain dict?**
A: Type-checked fields (`emergency_recall: Optional[float]`, not "however
the last person who wrote this code happened to name the key"), free
`.json()`/`.model_dump()` serialization, and — same reason `TriageDecision` and
`ReferralResult` are Pydantic models — it can be handed straight to
FastAPI's `response_model` later if this harness's results are ever
exposed over an endpoint, with no translation layer needed.

---

## Tier 2 — Design decisions

**Q: Why does the test dataset deliberately include a case (`em-05`) designed to be missed by the deterministic scanner?**
A: Because a dataset built only from cases the system is guaranteed to
get right would produce a misleadingly perfect number. `em-05`
("can't catch my breath at all") intentionally avoids every exact
red-flag substring, the same documented gap
`test_scan_red_flags_misses_paraphrase_by_design` proved exists back on
Day 1 — it exists in the eval set specifically to eventually measure
whether the *LLM* layer, not the deterministic layer, closes that gap.
A dataset that hides the hard cases isn't measuring anything.

**Q: Why does a skipped case get `evaluated=False, error=<message>` instead of just being left out of the results list entirely?**
A: Because "this case was correctly excluded because we know why" and
"this case silently vanished for an unknown reason" look identical if
skipped cases are just omitted — and only one of those is trustworthy.
`compute_report` explicitly separates `evaluated_count` from
`skipped_count`, and `_print_report` shows every case's status, so a
7-out-of-11 skip rate is visible and explained, not hidden inside a
smaller-looking denominator.

**Q: Why is `_BackendNeverCalled` redefined in `evaluation.py` instead of importing `_NullBackendNeverCalled` from `main.py`?**
A: Because `app/evaluation.py` has no other reason to depend on the API
layer — it's a batch script, not an HTTP handler, and coupling it to
`main.py` just to reuse four lines would mean a future change to the API
layer could break the evaluation harness for no functional reason. Small,
duplicated, single-purpose guard classes are cheaper than an import
relationship that doesn't correspond to anything real.

---

## Tier 3 — Code-reading (real, verified output)

**Q: What did the actual run of `python -m app.evaluation` produce, exactly, with no `ANTHROPIC_API_KEY` set?**
A: Run for real, output copied verbatim, not retyped from memory:
```
Evaluated: 4 / 11 cases
Skipped (backend unavailable): 7
Overall accuracy (evaluated cases only): 100%
Emergency recall (the metric that matters): 100%
```
followed by all 11 cases listed individually — `em-01` through `em-04`
each showing `-> emergency OK`, `em-05` through `sc-02` each showing
`SKIPPED (ANTHROPIC_API_KEY is not set. ...)`. Every skip carries the
exact real error string from `TriageBackendError`, not a generic
"failed" placeholder.

**Q: Trace `compute_report` by hand for this exact run's 4 evaluated results.**
A: All 4 evaluated cases are `em-01` through `em-04`, all expected and
actual level `emergency`. `evaluated = [em-01, em-02, em-03, em-04]`,
`correct = 4` (all match), `accuracy = 4/4 = 1.0`. `true_emergencies` is
the same 4-item list (all 4 evaluated cases happen to be emergencies in
this particular run, since the skipped ones were the non-emergency
cases). `caught = 4`, `emergency_recall = 4/4 = 1.0`.
`emergency_false_negatives = []`. Matches the printed `100%` for both
figures exactly — the arithmetic in the report is traceable by hand, not
a black box.

---

## Tier 4 — Code exercises

**Exercise: Add a `per_level_accuracy` field to `EvaluationReport` — accuracy broken out by expected triage level, not just overall.**

<details>
<summary>One correct approach</summary>

```python
from collections import defaultdict

def compute_per_level_accuracy(results: list[EvalCaseResult]) -> dict[str, float]:
    by_level: dict[TriageLevel, list[EvalCaseResult]] = defaultdict(list)
    for r in results:
        if r.evaluated:
            by_level[r.expected_level].append(r)

    return {
        level.value: sum(1 for r in group if r.actual_level == r.expected_level) / len(group)
        for level, group in by_level.items()
    }
```
The reason this is a real exercise, not busywork: today's single 100%
number hides that it's built entirely from 4 emergency cases — a
per-level breakdown would immediately show 0 evaluated cases for
self_care/clinic_visit/urgent today, which is a more honest picture than
one aggregate number.
</details>

**Exercise: `evaluate_case` currently has no way to tell whether the *Guideline-Verification* step changed the answer (escalated it) versus the raw Triage-Reasoning proposal. Add that visibility.**

<details>
<summary>One correct approach</summary>

```python
class EvalCaseResult(BaseModel):
    case_id: str
    expected_level: TriageLevel
    proposed_level: Optional[TriageLevel] = None   # new: before verification
    actual_level: Optional[TriageLevel] = None      # after verification (existing)
    was_escalated_by_verification: bool = False
    evaluated: bool
    error: Optional[str] = None
```
then in `evaluate_case`, capture `decision.level` before calling
`verify_triage_decision`, and set
`was_escalated_by_verification = verified.level != decision.level`.
This is the concrete way to answer "how often does your
Guideline-Verification agent actually catch something the LLM got
wrong" with a real measured number instead of an assertion that it
matters.
</details>

---

## Tier 5 — Deep / production questions

**Q: Is a 100% recall figure from 4 cases something to be confident about?**
A: No, and say so unprompted if an interviewer doesn't ask first. 4
cases is not statistically meaningful — a single missed case would drop
it to 75%, and the sample is entirely drawn from the deterministic
red-flag path, which has zero model uncertainty by construction (a
substring either matches or it doesn't). The real test of this system's
recall — on paraphrased, ambiguous, or borderline language — is
precisely the 7 cases that couldn't run today. Reporting a clean number
without this caveat would be a worse answer than reporting a messier,
honest one.

**Q: How would you scale this evaluation approach for a real clinical validation, beyond a portfolio project?**
A: Three concrete gaps between today's harness and a real validation:
(1) sample size — dozens of cases, not 11, ideally sourced from real
(de-identified, consented) triage interactions rather than authored
ones; (2) inter-rater ground truth — today's `expected_level` is a
single author's judgment call; a real validation needs agreement between
multiple clinicians on what the "correct" label even is; (3) confidence
intervals on the recall estimate, not a bare percentage — 4/4 and 40/40
are both "100%" but represent very different amounts of evidence.

**Q: Why does this matter for the 2028 market specifically?**
A: No new claim — same standard as every other "why does this matter"
question in this guide. The specific skill on display isn't "built an
eval script," it's recognizing that a metric without a caveat about
sample size and coverage is a red flag, and saying so before being
asked. That's the exact "know what your own system doesn't do yet"
signal already tied to interview credibility throughout this guide,
applied here to statistics instead of code.
