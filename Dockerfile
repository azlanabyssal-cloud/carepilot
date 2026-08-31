# CarePilot - container image
#
# Base: python:3.13-slim (Debian-based, not alpine - torch/scikit-learn ship
# manylinux wheels built against glibc; alpine's musl libc would force a
# from-source build of torch, which is impractical here).
#
# HONEST NOTE ON IMAGE SIZE: requirements.txt pulls in torch==2.7.1 and
# torchvision==0.22.1 for the CV image-triage model (app/models/cv_classifier.py),
# plus scikit-learn for guideline retrieval (app/agents/verify.py) and
# pillow/pytesseract for OCR (app/models/ocr.py). The PyPI torch wheel alone is
# several hundred MB (it bundles CUDA/cuDNN runtime libraries even though this
# app only ever runs it on CPU), so the built image lands in the multi-GB range
# (measured at build time below - see the "Actually built" note in README.md).
# That is real and not hidden here. It is not reduced by switching to a
# multi-stage build, because the size lives in torch's site-packages payload,
# not in build tooling - there is no compilation step to discard. The one
# available lever (a CPU-only torch wheel from download.pytorch.org's -cpu
# index, which drops the bundled CUDA libraries) is intentionally not applied
# here so this image installs the exact pins in requirements.txt unmodified;
# swapping the torch source is a real, separate follow-up, not something to
# silently do inside a "just get it running" Dockerfile.

FROM python:3.13-slim

# tesseract-ocr: required at runtime by app/models/ocr.py (pytesseract shells
# out to the `tesseract` binary - the Python package alone is just a wrapper
# and does nothing without it installed on the system).
# libgl1 + libglib2.0-0: pillow/torchvision's image codecs (pulled in
# transitively) expect these even in CPU-only, headless use.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        libgl1 \
        libglib2.0-0 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first, app code second - so editing app/ code doesn't
# invalidate the (large, slow) pip install layer on every rebuild.
#
# requirements-deploy.txt, not requirements.txt: torch/torchvision (969 MB
# of this image's footprint per README.md's own measurement) exist only for
# app/models/cv_classifier.py, which is real and tested against synthetic
# images but explicitly NOT YET WIRED into app/main.py's served endpoints
# (see README.md's build roadmap) - paying multi-GB of build time and image
# size for a module the running app never imports has no upside for a
# deployed instance, only slower builds and a higher chance of hitting a
# free-tier host's build-time or image-size limit. requirements.txt (the
# full set, torch included) stays the source of truth for local dev/CI,
# where tests/test_cv_classifier.py still needs it. The day cv_classifier.py
# is actually wired into a live endpoint, its dependencies belong back in
# this file alongside the code that then needs them - not before.
COPY requirements-deploy.txt .
RUN pip install --no-cache-dir -r requirements-deploy.txt

COPY app ./app
COPY data ./data
# web/ - this app's own frontend (see app/main.py's closing
# `app.mount("/ui", StaticFiles(directory="web", ...))`, which runs at
# import time). Omitting this line was a real bug: StaticFiles' constructor
# checks the directory exists immediately, so a container built without
# this line fails at startup, before ever serving a single request - not a
# degraded /ui, a container that never comes up at all.
COPY web ./web

# Non-root user - the app never needs root at runtime (no privileged ports,
# no system files to write), so don't run it as root.
RUN useradd --create-home --uid 1000 carepilot \
    && chown -R carepilot:carepilot /app
USER carepilot

EXPOSE 8000

# Mirrors the app's own GET /health (app/main.py) - fails the container's
# health status if the FastAPI process is wedged or never came up, not just
# if the process exited.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
