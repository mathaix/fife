"""Run once before going on stage: builds the images so no demo waits on a cold build."""

import modal
from common import app, data_image, step

for name, image in [("default image", None), ("pandas + matplotlib image", data_image)]:
    with step(f"Build {name}"):
        modal.Sandbox.create(app=app, image=image).terminate()
