"""Shared by every demo: the Modal app and a timed step printer."""

import time
from contextlib import contextmanager

import modal

app = modal.App.lookup("sandbox-demo", create_if_missing=True)


@contextmanager
def step(title: str):
    print(f"\n\033[1;36m▶ {title}\033[0m")
    start = time.perf_counter()
    yield
    print(f"\033[2m  ✓ {time.perf_counter() - start:.2f}s\033[0m")
