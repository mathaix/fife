"""07 · AI code interpreter — the LLM writes code, the sandbox runs it, errors go back until it's right."""

import os
import re
import sys

import anthropic
import modal
from common import ROOT, app, data_image, step

QUESTION = sys.argv[1] if len(sys.argv) > 1 else "Which region grew revenue the most from January to December, and by how much?"
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
MAX_TURNS = 5
SYSTEM = (
    "You answer questions about the CSV at /data/sales.csv by writing Python (pandas is installed). "
    "Reply with exactly one ```python code block and nothing else. The code must print the final answer as one sentence. "
    "If you are sent an error, fix the code."
)

llm = anthropic.Anthropic()

with step("Create one sandbox for the whole conversation (no network)"):
    sb = modal.Sandbox.create(app=app, image=data_image, block_network=True, timeout=600)
    sb.filesystem.copy_from_local(ROOT / "data/sales.csv", "/data/sales.csv")

print(f"\n\033[1mQ: {QUESTION}\033[0m")
messages = [{"role": "user", "content": QUESTION}]

for turn in range(1, MAX_TURNS + 1):
    with step(f"Turn {turn}: LLM writes code"):
        reply = llm.messages.create(model=MODEL, max_tokens=1024, system=SYSTEM, messages=messages).content[0].text
        code = re.search(r"```python\n(.*?)```", reply, re.S).group(1)
        print("\033[2m" + code.rstrip() + "\033[0m")
        messages.append({"role": "assistant", "content": reply})

    with step(f"Turn {turn}: sandbox runs it"):
        sb.filesystem.write_text(code, "/work/attempt.py")
        p = sb.exec("python", "/work/attempt.py", timeout=60)
        out, err = p.stdout.read(), p.stderr.read()
        p.wait()

    if p.returncode == 0:
        print(f"\n\033[1;32mA: {out.strip()}\033[0m")
        break
    print(f"  \033[31m✗ {err.strip().splitlines()[-1]}\033[0m — sending the traceback back to the LLM")
    messages.append({"role": "user", "content": f"That failed:\n{err}"})
else:
    print(f"\n\033[31mGave up after {MAX_TURNS} turns.\033[0m")

sb.terminate()
