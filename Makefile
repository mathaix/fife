# Issue agent: label a GitHub issue `agent`, get a PR. Settings live in .env (see README).
PY := .venv/bin/python
VENV := .venv/.installed

.PHONY: help setup watch issue seed demos

help: ## list the commands
	@grep -E '^[a-z]+:.*## ' Makefile | sed 's/:.*## /\t/'

$(VENV): requirements.txt
	test -d .venv || uv venv -q
	uv pip install -q -r requirements.txt && touch $@

setup: $(VENV) ## create .venv with the dependencies (other commands do this automatically)

watch: $(VENV) ## watch every repo GH_DEMO_TOKEN can push to for issues labelled `agent`
	$(PY) agent/run.py --watch

issue: $(VENV) ## handle one issue: make issue ISSUE=owner/name#3
	@test -n "$(ISSUE)" || { echo 'usage: make issue ISSUE=owner/name#3'; exit 2; }
	$(PY) agent/run.py --issue "$(ISSUE)"

seed: $(VENV) ## create the three sample_app demo issues: make seed REPO=owner/name
	@test -n "$(REPO)" || { echo 'usage: make seed REPO=owner/name'; exit 2; }
	$(PY) agent/seed_issues.py --repo "$(REPO)"

demos: $(VENV) ## run the Act 1 and Act 2 sandbox demos
	PATH=.venv/bin:$$PATH ./run_all.sh
