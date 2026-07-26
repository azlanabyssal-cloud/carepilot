"""
These tests prove the CV pipeline's PLUMBING works - data loading,
forward pass, training loop, inference - using small synthetic images
generated with PIL. They are explicitly NOT real medical images and
prove nothing about real-world classification accuracy. That requires
a real dataset (HAM10000 or similar) this environment doesn't have
downloaded - see app/models/cv_classifier.py's module docstring.
"""

import torch
from PIL import Image
from torch.utils.data import DataLoader

from app.models.cv_classifier import (
    URGENCY_CLASSES,
    ClassificationResult,
    ImageFolderDataset,
    build_model,
    get_inference_transform,
    predict,
    train_one_epoch,
)


def _synthetic_image(color: tuple[int, int, int] = (128, 64, 32)) -> Image.Image:
    """A plain solid-color image - a plumbing fixture, not a medical image."""
    return Image.new("RGB", (300, 300), color=color)


def test_build_model_outputs_correct_number_of_classes():
    model = build_model(pretrained=False)  # no network download needed for this check
    dummy_batch = torch.randn(2, 3, 224, 224)

    with torch.no_grad():
        logits = model(dummy_batch)

    assert logits.shape == (2, len(URGENCY_CLASSES))


def test_build_model_freezes_the_backbone_not_the_head():
    model = build_model(pretrained=False)

    backbone_trainable = any(p.requires_grad for p in model.features.parameters())
    head_trainable = all(p.requires_grad for p in model.classifier[-1].parameters())

    assert backbone_trainable is False
    assert head_trainable is True


def test_predict_returns_a_valid_classification_result():
    model = build_model(pretrained=False)
    image = _synthetic_image()

    result = predict(model, image)

    assert isinstance(result, ClassificationResult)
    assert result.label in URGENCY_CLASSES
    assert 0.0 <= result.confidence <= 1.0


def test_image_folder_dataset_loads_from_a_real_temp_directory(tmp_path):
    for class_name in URGENCY_CLASSES:
        class_dir = tmp_path / class_name
        class_dir.mkdir()
        _synthetic_image().save(class_dir / "sample.jpg")

    dataset = ImageFolderDataset(tmp_path)

    assert len(dataset) == len(URGENCY_CLASSES)
    tensor, label = dataset[0]
    assert tensor.shape == (3, 224, 224)
    assert label in range(len(URGENCY_CLASSES))


def test_image_folder_dataset_skips_missing_class_directories(tmp_path):
    class_dir = tmp_path / URGENCY_CLASSES[0]
    class_dir.mkdir()
    _synthetic_image().save(class_dir / "sample.jpg")
    # The other two class directories are never created.

    dataset = ImageFolderDataset(tmp_path)

    assert len(dataset) == 1


def test_train_one_epoch_actually_reduces_loss(tmp_path):
    # Two visually distinct synthetic classes - a real convergence
    # check, not just "the loop runs without crashing." If backprop or
    # the optimizer wiring were broken, this would fail.
    colors = [(240, 240, 240), (10, 10, 10)]
    for class_name, color in zip(URGENCY_CLASSES[:2], colors):
        class_dir = tmp_path / class_name
        class_dir.mkdir()
        for i in range(6):
            _synthetic_image(color).save(class_dir / f"sample_{i}.jpg")

    dataset = ImageFolderDataset(tmp_path, transform=get_inference_transform())
    loader = DataLoader(dataset, batch_size=4, shuffle=True)

    model = build_model(num_classes=len(URGENCY_CLASSES), pretrained=False)
    optimizer = torch.optim.Adam(model.classifier[-1].parameters(), lr=0.01)

    first_epoch_loss = train_one_epoch(model, loader, optimizer)
    for _ in range(4):
        latest_loss = train_one_epoch(model, loader, optimizer)

    assert latest_loss < first_epoch_loss
