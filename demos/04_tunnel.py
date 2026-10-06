"""04 · Live app via tunnel — a web server inside the sandbox, on a public HTTPS URL."""

import modal
from common import ROOT, app, step
from modal.stream_type import StreamType

with step("Create a sandbox with port 8000 exposed"):
    sb = modal.Sandbox.create(app=app, encrypted_ports=[8000], timeout=600)

with step("Upload and start the server"):
    sb.filesystem.copy_from_local(ROOT / "demos/payloads/server.py", "/work/server.py")
    sb.exec("python", "/work/server.py", stdout=StreamType.DEVNULL, stderr=StreamType.DEVNULL)

with step("Get the public URL"):
    print(f"  \033[1;32m{sb.tunnels()[8000].url}\033[0m")

input("\n  Open it, refresh a few times, then press Enter to shut it down… ")
sb.terminate()
