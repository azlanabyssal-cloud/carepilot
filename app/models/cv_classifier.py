"""
Skin/wound image urgency classifier - transfer learning pipeline.

Not trained on real data yet - there is no shipped weights file. This
module is the complete, real pipeline (model, training loop, inference)
proven against synthetic plumbing-test images, explicitly NOT real
medical images - see tests/test_cv_classifier.py and
docs/INTERVIEW_NOTES.md for exactly what "proven" means here and what
it doesn't.

To actually train this: download HAM10000 (CC BY-NC 4.0 - free for
non-commercial/academic use, requires a Kaggle account or Harvard
Dataverse access this environment doesn't have configured), reorganize
it into data/cv_training/<class_name>/*.jpg per ImageFolderDataset's
layout below, then run train_one_epoch in a loop with a real GPU.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

# An image classifier here produces an urgency SIGNAL to combine with
# the text-based Triage-Reasoning Agent's output - not a standalone
# triage decision on its own. Kept as its own small vocabulary rather
# than reusing TriageLevel, since visual urgency and overall triage
# level are related but not the same axis.
URGENCY_CLASSES = ["low_concern", "moderate_concern", "high_concern"]

IMAGE_SIZE = 224  # MobileNetV3's expected input resolution, not arbitrary


def build_model(num_classes: int = len(URGENCY_CLASSES), pretrained: bool = True) -> nn.Module:
    """
    MobileNetV3-Small: ~2.5M parameters, fine-tunes in reasonable time
    on a laptop or a free-tier Colab GPU - unlike a full ResNet50, which
    would be the "impressive-sounding" default but wrong-sized for a
    student project that actually needs to finish training. The
    pretrained feature extractor is frozen; only the classifier head is
    trained - standard practice, and the right call with a dataset this
    small, where fine-tuning the whole backbone would overfit fast.
    """
    weights = MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
    model = mobilenet_v3_small(weights=weights)

    for param in model.features.parameters():
        param.requires_grad = False

    in_features = model.classifier[-1].in_features
    model.classifier[-1] = nn.Linear(in_features, num_classes)
    return model


def get_inference_transform() -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )


@dataclass(frozen=True)
class ClassificationResult:
    label: str
    confidence: float


def predict(model: nn.Module, image: Image.Image, device: str = "cpu") -> ClassificationResult:
    model.eval()
    transform = get_inference_transform()
    tensor = transform(image.convert("RGB")).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(tensor)
        probabilities = torch.softmax(logits, dim=1)
        confidence, predicted_idx = torch.max(probabilities, dim=1)

    return ClassificationResult(
        label=URGENCY_CLASSES[predicted_idx.item()],
        confidence=confidence.item(),
    )


class ImageFolderDataset(Dataset):
    """
    Minimal real Dataset: expects data/cv_training/<class_name>/*.jpg|png
    - the standard layout most Kaggle skin-image datasets ship in after
    a light reorganization script. Not wired to any specific dataset's
    raw metadata format, since no real dataset is downloaded in this
    environment to build and test that reorganization step against.
    """

    def __init__(self, root: Path, transform: transforms.Compose | None = None) -> None:
        self.samples: list[tuple[Path, int]] = []
        self.transform = transform or get_inference_transform()
        self.classes = URGENCY_CLASSES

        for class_idx, class_name in enumerate(self.classes):
            class_dir = root / class_name
            if not class_dir.is_dir():
                continue
            images = sorted(class_dir.glob("*.jpg")) + sorted(class_dir.glob("*.png"))
            self.samples.extend((path, class_idx) for path in images)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        image_path, label = self.samples[idx]
        image = Image.open(image_path).convert("RGB")
        return self.transform(image), label


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: str = "cpu",
) -> float:
    """Returns the mean training loss for the epoch - real backprop, not a stub."""
    model.train()
    criterion = nn.CrossEntropyLoss()
    total_loss = 0.0

    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * images.size(0)

    return total_loss / len(loader.dataset)
