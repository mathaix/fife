---
marp: true
html: true
size: 16:9
title: Scale Software Development with AI Sandboxes
author: Mathew Mathew
style: |
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;700&display=swap');
  :root { --bg:#11161c; --card:#1a212a; --line:#2c3440; --text:#ede8df; --muted:#8b93a1; --orange:#ff7a3d; --blue:#6aa8ff; }
  section { background:var(--bg); color:var(--text); font-family:Inter,sans-serif; font-size:24px; padding:64px 64px; justify-content:flex-start; }
  h1, h2 { font-family:'Space Grotesk',sans-serif; color:var(--text); font-weight:600; letter-spacing:-0.01em; margin:0 0 28px; }
  h1 { font-size:76px; line-height:1.08; }
  h2 { font-size:56px; }
  code { font-family:'JetBrains Mono',monospace; background:none; color:inherit; }
  .eyebrow { font-family:'JetBrains Mono',monospace; font-size:16px; letter-spacing:.14em; text-transform:uppercase; color:var(--orange); margin:0 0 18px; }
  .blue { color:var(--blue); } .orange { color:var(--orange); } .muted { color:var(--muted); }
  .say { font-size:26px; margin-top:28px; }
  section.light { background:#f3efe6; color:#161b22; }
  section.light h2 { color:#161b22; } section.light .eyebrow { color:#c2410c; }
  /* ladder */
  .rung { display:flex; align-items:center; background:var(--card); border-radius:8px; padding:12px 26px; margin:9px 0; font-size:22px; }
  .rung b { width:60px; color:var(--orange); font-family:'Space Grotesk'; } .rung.up b { color:var(--blue); }
  .rung span { width:390px; font-weight:600; } .rung em { font-style:normal; color:var(--muted); }
  .divide { font-family:'JetBrains Mono'; font-size:14px; letter-spacing:.14em; color:var(--muted); padding:4px 26px; }
  /* stage cards */
  .cards { display:flex; gap:22px; height:360px; }
  .cards > div { flex:1; background:var(--card); border-radius:10px; border-top:4px solid var(--orange); padding:28px 30px; font-size:25px; line-height:1.35; }
  .cards small { display:block; font-family:'JetBrains Mono'; font-size:14px; letter-spacing:.12em; color:var(--muted); margin-bottom:12px; }
  .cards .neck { font-family:'Space Grotesk'; font-size:40px; font-weight:600; line-height:1.15; color:var(--orange); }
  .stages { display:flex; gap:12px; margin-top:28px; }
  .stages div { flex:1; border-top:3px solid var(--line); padding-top:10px; font-family:'JetBrains Mono'; font-size:14px; color:var(--muted); }
  .stages .on { border-color:var(--orange); color:var(--orange); font-weight:700; }
  section.sbx .eyebrow, section.sbx .cards .neck, section.sbx .stages .on { color:var(--blue); }
  section.sbx .cards > div, section.sbx .stages .on { border-color:var(--blue); }
  /* misc */
  .term { background:#0b0f14; border:1px solid var(--line); border-radius:8px; padding:20px 26px; font-family:'JetBrains Mono'; font-size:22px; }
  .two { display:flex; gap:22px; margin-top:22px; } .two > div { flex:1; background:var(--card); border-radius:10px; border-top:4px solid var(--blue); padding:22px 26px; }
  .two h3 { font-family:'Space Grotesk'; font-size:28px; margin:0 0 6px; } .two p { color:var(--muted); font-size:19px; margin:0 0 14px; }
  .flow { display:flex; align-items:center; gap:14px; font-size:17px; }
  .chip { border:1.5px solid var(--line); border-radius:8px; padding:6px 12px; margin:6px 0; font-family:'JetBrains Mono'; font-size:15px; white-space:nowrap; }
  .chip.b { border-color:var(--blue); } .chip.d { border-style:dashed; border-color:var(--blue); background:#1d2a3c; }
  .pills span { display:inline-block; background:#161b22; color:#f3efe6; font-family:'JetBrains Mono'; font-size:19px; border-radius:30px; padding:10px 20px; margin:6px 8px 0 0; }
  .spectrum { display:flex; gap:16px; } .spectrum div { flex:1; background:var(--card); border-radius:10px; border-top:3px solid var(--blue); padding:18px; font-size:18px; color:var(--muted); }
  .spectrum b { display:block; font-size:24px; color:var(--text); margin-bottom:8px; }
  .axis { height:6px; border-radius:3px; margin:30px 0 12px; background:linear-gradient(90deg,#3a4350,#a9ccff); }
  .axis + div { display:flex; justify-content:space-between; font-family:'JetBrains Mono'; font-size:15px; letter-spacing:.1em; color:var(--muted); }
  table { display:table; width:100%; font-size:21px; border-collapse:collapse; }
  section.light th, section.light td { background:#f3efe6; border:1px solid #c9c3b8; padding:10px 14px; color:#161b22; text-align:left; }
  section.light th { background:#e3ded5; } section.light tr:nth-child(even) td { background:#e9e4da; }
---

<!-- _class: title -->

<p class="eyebrow muted">[ EvoNexus · Oct 8 ]</p>

# Scale Software<br>Development with AI<br>Sandboxes

<p class="orange" style="font-size:28px;margin:0 0 30px">From laptop steering to agent swarms</p>
<p class="muted" style="font-size:20px">Mathew Mathew · CTO, <a href="https://claramap.com" style="color:inherit">Claramap.com</a></p>

<svg style="position:absolute;right:90px;top:90px" width="260" height="210" viewBox="0 0 260 210"><rect x="0" y="168" width="34" height="42" rx="4" fill="#ff7a3d"/><rect x="56" y="126" width="34" height="84" rx="4" fill="#ff7a3d"/><rect x="112" y="84" width="34" height="126" rx="4" fill="#ff7a3d"/><rect x="168" y="42" width="34" height="168" rx="4" fill="#6aa8ff"/><rect x="224" y="0" width="34" height="210" rx="4" fill="#6aa8ff"/></svg>

---

<div style="display:flex;gap:64px;align-items:center;height:100%">
<img src="img/headshot.jpg" style="width:390px;border-radius:12px">
<div>
<p class="eyebrow">Let's connect</p>
<h2 style="margin:0">Mathew Mathew</h2>
<p class="blue" style="font-size:26px;margin:6px 0 22px">CTO &amp; Founder, <a href="https://claramap.com" style="color:inherit">Claramap</a></p>
<p style="font-size:22px">Claramap helps companies design, build and run <b>agentic systems</b> in production.</p>
<p class="muted" style="font-size:21px">20+ years as a software engineer and data scientist at IBM Cloud, Amdocs, AT&amp;T, SolarWinds and Discover.</p>
<div style="display:flex;gap:40px;align-items:center;margin-top:20px">
<img src="img/qr.png" style="width:180px;border-radius:12px">
<div style="font-family:'JetBrains Mono';font-size:19px;line-height:2.1">
<span class="muted" style="font-size:15px;letter-spacing:.12em">SCAN FOR THE SLIDES</span><br>
<a href="https://claramap.com">claramap.com</a><br>
<a href="https://www.linkedin.com/in/mathewma">linkedin.com/in/mathewma</a><br>
<a href="https://github.com/mathaix/fife">github.com/mathaix/fife</a><br>
<a href="https://github.com/mathaix/signals">github.com/mathaix/signals</a>
</div></div></div></div>

---

<p class="eyebrow">Before we start</p>

## Where are you on the ladder?

<div class="rung up"><b>5</b><span>Agent swarm</span><em>Many agents, one problem</em></div>
<div class="rung up"><b>4</b><span>Agent factory</span><em>Tickets in, PRs out</em></div>
<div class="divide">▲ SANDBOXES · · · · · · · · · · · · · LAPTOP ▼</div>
<div class="rung"><b>3</b><span>Parallel local agents</span><em>Worktrees and YOLO mode</em></div>
<div class="rung"><b>2</b><span>Local agent</span><em>An agent in your terminal</em></div>
<div class="rung"><b>1</b><span>Autocomplete</span><em>AI suggests, you do the rest</em></div>

---

<p class="eyebrow">Foundations · 1 of 4</p>

## The agent loop

![w:1150](img/agent-loop.svg)

<p class="say">Every action is a tool you defined. <span class="blue">You know exactly what it can do.</span></p>

---

<p class="eyebrow">Foundations · 2 of 4</p>

## The coding agent

![w:1150](img/coding-agent.svg)

<p class="say">Give it bash and it writes its own tools. <span class="orange">You can't predict what it will run, so run it in a sandbox.</span></p>

---

<p class="eyebrow">Foundations · 3 of 4</p>

## Headless execution

<div class="term"><span class="orange">$</span> claude -p "Fix the failing test in auth/" --output-format json</div>

<div class="two">
<div>
<h3>Decompose</h3>
<p>Split a big task. Each subagent gets one job and only the context it needs.</p>
<div class="flow"><div class="chip">Lead agent</div><span class="muted">→</span><div>
<div class="chip b">claude -p "schema" <span class="blue">db/</span></div>
<div class="chip b">claude -p "route" <span class="blue">api/auth/</span></div>
<div class="chip b">claude -p "tests" <span class="blue">tests/</span></div></div></div>
</div>
<div>
<h3>Automate</h3>
<p>No one at the keyboard. Events and schedules start the agent.</p>
<div class="flow"><div><div class="chip">CI run</div><div class="chip">Cron</div><div class="chip">Webhook</div></div>
<span class="muted">→</span><div class="chip d">claude -p <span class="muted">· no human</span></div><span class="muted">→</span><div class="chip">Result</div></div>
</div>
</div>

---

<p class="eyebrow">Foundations · 4 of 4</p>

## Orchestrate

![w:1100](img/orchestrate.svg)

<p class="say">Same agent, many entry points. <span class="orange">Every task gets its own sandbox.</span></p>

---

<p class="eyebrow">Stage 1 of 5 · On your laptop</p>

## Autocomplete

<div class="cards">
<div><small>LOOKS LIKE</small>AI suggests. You type, run and check everything.</div>
<div><small>WHAT BREAKS</small>You want the AI to run the code, not just write it.</div>
<div><small>BOTTLENECK</small><span class="neck">Your typing</span></div>
</div>
<div class="stages"><div class="on">1 Autocomplete</div><div>2 Local agent</div><div>3 Parallel local</div><div>4 Agent factory</div><div>5 Agent swarm</div></div>

---

<p class="eyebrow">Stage 2 of 5 · On your laptop</p>

## Local agent

<div class="cards">
<div><small>LOOKS LIKE</small>An agent in your terminal runs commands. OS-level sandboxing lets you relax the prompts.</div>
<div><small>WHAT BREAKS</small>You spend the day clicking Allow.</div>
<div><small>BOTTLENECK</small><span class="neck">Your approvals</span></div>
</div>
<div class="stages"><div>1 Autocomplete</div><div class="on">2 Local agent</div><div>3 Parallel local</div><div>4 Agent factory</div><div>5 Agent swarm</div></div>

---

<p class="eyebrow">Stage 3 of 5 · Laptop, straining</p>

## Parallel local agents

<div class="cards">
<div><small>LOOKS LIKE</small>Several agents in worktrees and devcontainers, in YOLO mode.</div>
<div><small>WHAT BREAKS</small>Ports, RAM, credentials and blast radius, all on one machine.</div>
<div><small>BOTTLENECK</small><span class="neck">Your hardware</span></div>
</div>
<div class="stages"><div>1 Autocomplete</div><div>2 Local agent</div><div class="on">3 Parallel local</div><div>4 Agent factory</div><div>5 Agent swarm</div></div>

---

<!-- _class: light -->

<p class="eyebrow">The pivot</p>

## What a sandbox is

<p style="font-family:'Space Grotesk';font-size:40px;line-height:1.3;margin:0 0 28px">An ephemeral, isolated computer with an API, where an agent can run anything inside a blast radius <span style="color:#c2410c">you control</span>.</p>

<div class="pills"><span>Isolated</span><span>Ephemeral</span><span>Programmable</span><span>Fast to start</span><span>Snapshottable</span></div>

---

<p class="eyebrow blue">Isolation</p>

## The isolation spectrum

<div class="spectrum">
<div><b>OS sandbox</b>Seatbelt, bubblewrap, Landlock</div>
<div><b>Container</b>Namespaces and cgroups; shared host kernel</div>
<div><b>gVisor</b>User-space kernel intercepts syscalls</div>
<div><b>microVM</b>Firecracker, Kata; own kernel</div>
<div><b>Full VM</b>Full hardware virtualization</div>
</div>
<div class="axis"></div>
<div><span>← FASTER START · LESS OVERHEAD</span><span>STRONGER BOUNDARY →</span></div>

---

<!-- _class: sbx -->

<p class="eyebrow">Stage 4 of 5 · In sandboxes</p>

## Agent factory

<div class="cards">
<div><small>LOOKS LIKE</small>Tickets in, PRs out. One disposable sandbox per task.</div>
<div><small>WHAT BREAKS</small>One attempt per task isn't enough for hard problems.</div>
<div><small>BOTTLENECK</small><span class="neck">Review &amp; verification</span></div>
</div>
<div class="stages"><div>1 Autocomplete</div><div>2 Local agent</div><div>3 Parallel local</div><div class="on">4 Agent factory</div><div>5 Agent swarm</div></div>

---

<!-- _class: sbx -->

<p class="eyebrow">Demo · Stage 4 in practice</p>

## Fife: your AI backlog resolver

<div style="display:flex;gap:56px;align-items:center">
<div style="flex:1;font-size:26px;line-height:1.5">

1. Label a GitHub issue `agent`
2. A fresh Modal sandbox per issue; Claude Code does the work
3. It writes tests and fixes until they pass, up to 3 rounds
4. A pull request arrives with the passing run as proof

<p class="say">Stop steering agents. <span class="blue">Start managing them.</span></p>
<p class="muted" style="font-family:'JetBrains Mono';font-size:19px">github.com/mathaix/fife</p>
</div>
<img src="img/fife.svg" style="width:300px">
</div>

---

<!-- _class: sbx -->

<p class="eyebrow">Stage 5 of 5 · In sandboxes</p>

## Agent swarm

<div class="cards">
<div><small>LOOKS LIKE</small>Many agents on one problem: fan out, fork, compare.</div>
<div><small>WHAT BREAKS</small>Cold start and cost per sandbox become architecture decisions.</div>
<div><small>BOTTLENECK</small><span class="neck">Isolation vs. speed vs. cost</span></div>
</div>
<div class="stages"><div>1 Autocomplete</div><div>2 Local agent</div><div>3 Parallel local</div><div>4 Agent factory</div><div class="on">5 Agent swarm</div></div>

---

<!-- _class: light -->

<p class="eyebrow">The ecosystem</p>

## Who builds the sandboxes

| Tool | Isolation | Notable |
|---|---|---|
| Firecracker | microVM | Open-source building block from AWS; not a product |
| Docker | Container | Dev default; not enough alone for untrusted code |
| E2B | Firecracker microVM | Agent-focused code-interpreter SDK |
| Modal | gVisor | Built for scale; locked down by default |
| Daytona | Container (Sysbox) | Fast creation; egress allowlists; placeholder secrets |

---

<h1 style="font-size:58px;margin-top:20px">Laptops are where agents learn to code.<br><span class="blue">Sandboxes are where they learn to scale.</span></h1>

<div style="position:absolute;bottom:80px">
<p style="font-size:26px;margin:0 0 8px">Thank you · Questions?</p>
<p class="muted" style="font-family:'JetBrains Mono';font-size:18px;margin:0">Mathew Mathew · <a href="mailto:mmathew@claramap.com" style="color:inherit">mmathew@claramap.com</a> · <a href="https://claramap.com" style="color:inherit">claramap.com</a></p>
</div>
