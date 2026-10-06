"""05 · Parallel fan-out — ten sandboxes cost the same code as one."""

import asyncio
import sys
import time

import modal
from common import app

N = int(sys.argv[1]) if len(sys.argv) > 1 else 10
TASK = """
import random, sys
random.seed(int(sys.argv[1]))
n = 3_000_000
inside = sum(random.random() ** 2 + random.random() ** 2 < 1 for _ in range(n))
print(4 * inside / n)
"""


async def run_one(seed: int):
    start = time.perf_counter()
    sb = await modal.Sandbox.create.aio(app=app)
    p = await sb.exec.aio("python", "-c", TASK, str(seed))
    estimate = float(await p.stdout.read.aio())
    await sb.terminate.aio()
    return seed, estimate, time.perf_counter() - start


async def main():
    print(f"\033[1;36m▶ Estimating π in {N} sandboxes at once\033[0m")
    start = time.perf_counter()
    results = await asyncio.gather(*(run_one(i) for i in range(N)))
    wall = time.perf_counter() - start

    for seed, estimate, secs in results:
        print(f"  sandbox {seed:>2}  π ≈ {estimate:.5f}  ({secs:.1f}s)")
    serial = sum(r[2] for r in results)
    mean = sum(r[1] for r in results) / N
    print(f"\n  mean π ≈ {mean:.5f}")
    print(f"  wall clock {wall:.1f}s vs {serial:.1f}s if run one after another ({serial / wall:.1f}x)")


asyncio.run(main())
