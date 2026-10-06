"""01 · Hello sandbox — a fresh remote container, driven from a few lines of Python."""

import modal
from common import app, step

with step("Create a sandbox"):
    sb = modal.Sandbox.create(app=app)
    print(f"  id: {sb.object_id}")

with step("Run a shell command inside it"):
    p = sb.exec("uname", "-a")
    print("  " + p.stdout.read().strip())

with step("Run Python and stream its output live"):
    p = sb.exec("python", "-u", "-c", "import time\nfor i in range(5): print('tick', i); time.sleep(0.5)")
    for line in p.stdout:
        print("  " + line, end="")
    p.wait()

with step("Terminate"):
    sb.terminate()
