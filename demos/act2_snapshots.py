"""06 · Snapshots — freeze a sandbox's filesystem, start new ones from it instantly."""

import modal
from common import app, step

with step("Sandbox A: slow setup (pip install + write state)"):
    a = modal.Sandbox.create(app=app)
    a.exec("pip", "install", "-q", "pandas", "scikit-learn").wait()
    a.filesystem.write_text("trained on 2025 data, accuracy 0.93", "/state/notes.txt")

with step("Snapshot A's filesystem into an image"):
    snapshot = a.snapshot_filesystem()
    a.terminate()
    print(f"  image id: {snapshot.object_id}")

with step("Sandbox B: start from the snapshot — setup already done"):
    b = modal.Sandbox.create(app=app, image=snapshot)
    p = b.exec("python", "-c", "import sklearn; print('sklearn', sklearn.__version__); print(open('/state/notes.txt').read())")
    print("  " + p.stdout.read().strip().replace("\n", "\n  "))
    b.terminate()
