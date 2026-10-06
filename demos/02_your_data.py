"""02 · Your data, your sandbox — custom image in, files in, results out."""

import modal
from common import ROOT, app, data_image, step

with step("Create a sandbox from an image with pandas + matplotlib"):
    sb = modal.Sandbox.create(app=app, image=data_image)

with step("Upload the CSV and the analysis script"):
    sb.filesystem.copy_from_local(ROOT / "data/sales.csv", "/data/sales.csv")
    sb.filesystem.copy_from_local(ROOT / "demos/payloads/analyze.py", "/work/analyze.py")

with step("Run the analysis"):
    p = sb.exec("python", "/work/analyze.py")
    print(p.stdout.read())
    p.wait()

with step("Download the chart"):
    (ROOT / "out").mkdir(exist_ok=True)
    sb.filesystem.copy_to_local("/work/chart.png", ROOT / "out/chart.png")
    print("  saved out/chart.png")

sb.terminate()
