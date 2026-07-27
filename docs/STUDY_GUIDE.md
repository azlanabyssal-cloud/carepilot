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
