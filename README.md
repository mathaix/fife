# Modal Sandboxes in 7 demos

Runnable demos for a developer talk on [Modal Sandboxes](https://modal.com/docs/guide/sandbox):
throwaway, locked-down cloud containers you create, drive and destroy from Python —
the building block behind code interpreters and coding agents.

Each demo is one short file meant to fit on a slide. Timings print after every step.

## Setup

```bash
pip install -r requirements.txt
modal setup                       # or export MODAL_TOKEN_ID / MODAL_TOKEN_SECRET
export ANTHROPIC_API_KEY=...      # demo 07 only
python demos/prewarm.py           # before the talk: builds images so nothing cold-starts on stage
```

Run any demo with `python demos/0N_name.py`, or all of them with `./run_all.sh`.

## How the orchestration works

Your Python process is the orchestrator. Sandboxes are passive workers: they only do what you tell them.

```
your code ──Modal SDK──► Modal ──► sandbox 1 … sandbox N
   create → exec / upload → read stdout, files → decide next step → terminate
```

In demo 07 an LLM joins the loop, but it never touches the sandbox directly — your code relays
code from the LLM to the sandbox and errors from the sandbox back to the LLM.

## The demos and talk track

| # | File | Say | They see | Takeaway |
|---|------|-----|----------|----------|
| 1 | `01_hello.py` | "Here's a computer I didn't have a second ago." | Sandbox id, `uname`, live streamed ticks | A remote container is one `Sandbox.create` away |
| 2 | `02_your_data.py` | "Ship it data and code, get results back." | Growth per region, `out/chart.png` | Custom images + `sandbox.filesystem` = the data-agent loop |
| 3 | `03_isolation.py` | "Now let's try to break out." | Network call fails, infinite loop killed at 10s, memory hog OOM-killed | `block_network`, `timeout`, `memory` make untrusted code safe |
| 4 | `04_tunnel.py` | "Agents can build things people can use." | A public HTTPS URL; refresh and the counter goes up | `encrypted_ports` + `tunnels()` expose a live process |
| 5 | `05_fan_out.py` | "One sandbox or ten — same code." | 10 π estimates, wall clock vs serial speed-up | `.aio` + `asyncio.gather` for parallel attempts |
| 6 | `06_snapshots.py` | "Don't redo setup — freeze and resume." | Slow setup in A, B starts with everything installed | `snapshot_filesystem()` returns an image you can boot from |
| 7 | `07_ai_interpreter.py` | "Put it together: a code interpreter in ~50 lines." | LLM code, a failure, the traceback fed back, a corrected answer | The LLM ⇄ sandbox loop is the whole trick |

Demo 07 doesn't tell the LLM the CSV's column names (`sales_region`, `net_revenue_usd`), so the first
attempt usually guesses wrong and hits a `KeyError`; the self-correction is the point. Pass your own
question as an argument: `python demos/07_ai_interpreter.py "Which month had the most units sold?"`.
Set `ANTHROPIC_MODEL` to use a different Claude model.

## Tips for running live

- Run `prewarm.py` shortly before you're on.
- Open each file in your editor next to the terminal; the code is the slide.
- Record a fallback run with `./run_all.sh` in case the venue Wi-Fi fails.
- Everything runs under one Modal app, `sandbox-demo`; watch sandboxes appear in the Modal dashboard during demo 5.
