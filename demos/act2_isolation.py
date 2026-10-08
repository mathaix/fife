"""03 · Isolation and limits — untrusted code can't phone home, run forever, or eat the host."""

import modal
from common import app, step

with step("No network: block_network=True"):
    sb = modal.Sandbox.create(app=app, block_network=True)
    p = sb.exec("python", "-c", "import urllib.request; urllib.request.urlopen('https://example.com', timeout=5)")
    p.wait()
    print(f"  exit code {p.returncode}: {p.stderr.read().strip().splitlines()[-1]}")
    sb.terminate()

with step("Runaway loop: timeout=10"):
    sb = modal.Sandbox.create("python", "-c", "while True: pass", app=app, timeout=10)
    try:
        sb.wait()
    except modal.exception.SandboxTimeoutError:
        print("  sandbox killed after its 10s budget (SandboxTimeoutError)")

with step("Memory hog: hard limit of 256 MiB"):
    sb = modal.Sandbox.create(app=app, memory=(128, 256))
    p = sb.exec("python", "-c", "x = []\nwhile True: x.append(bytearray(10_000_000))")
    p.wait()
    print(f"  process OOM-killed (exit code {p.returncode})")
    sb.terminate()
