"""Shared bits every demo needs: the Modal app, the data image, and a timed step printer."""

import time
from contextlib import contextmanager
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent.parent
app = modal.App.lookup("sandbox-demo", create_if_missing=True)
data_image = modal.Image.debian_slim(python_version="3.12").pip_install("pandas", "matplotlib")


@contextmanager
def step(title: str):
    print(f"\n\033[1;36m▶ {title}\033[0m")
    start = time.perf_counter()
    yield
    print(f"\033[2m  ✓ {time.perf_counter() - start:.2f}s\033[0m")
