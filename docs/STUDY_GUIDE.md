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
