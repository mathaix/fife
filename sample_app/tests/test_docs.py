"""Keeps the README and docs honest: links, commands, env vars and layout must match the repo."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
DOC_FILES = [README, *sorted((ROOT / "docs").glob("*.md"))]
SVG_NS = "{http://www.w3.org/2000/svg}"


def section(text: str, title: str) -> str:
    """Return the body of the `## title` section of a Markdown document."""
    body = text.split(f"## {title}\n", 1)[1]
    return re.split(r"\n## ", body, maxsplit=1)[0]


def test_logo_is_svg_with_title():
    root = ET.parse(ROOT / "docs" / "logo.svg").getroot()
    assert root.tag == f"{SVG_NS}svg"
    assert root.find(f"{SVG_NS}title").text == "Modal Sandboxes"


def test_local_links_and_images_resolve():
    link = re.compile(r'\]\(([^)\s]+)\)|(?:src|href)="([^"]+)"')
    for doc in DOC_FILES:
        for match in link.finditer(doc.read_text()):
            target = (match.group(1) or match.group(2)).split("#")[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            assert (doc.parent / target).exists(), f"{doc.name} links to missing {target}"


def test_documented_commands_exist_and_use_real_flags():
    command = re.compile(r"python ((?:agent|demos)/[\w/.-]+\.py)((?:\s+--[\w-]+)*)")
    for doc in DOC_FILES:
        for script, flags in command.findall(doc.read_text()):
            assert (ROOT / script).exists(), f"{doc.name} runs missing script {script}"
            source = (ROOT / script).read_text()
            for flag in flags.split():
                assert flag in source, f"{doc.name} uses {flag} but {script} does not accept it"


def test_setup_env_vars_are_read_by_the_agent():
    agent_code = "\n".join(p.read_text() for p in (ROOT / "agent").glob("*.py"))
    names = re.findall(r"^\| `([A-Z_]+)` \|", section(README.read_text(), "Setup"), re.M)
    assert names, "Setup should document the Act 3 environment variables"
    for name in names:
        assert name in agent_code, f"README documents {name} but the agent never reads it"


def test_repository_layout_paths_exist():
    paths = re.findall(r"^\| `([^`]+)` \|", section(README.read_text(), "Repository layout"), re.M)
    assert paths, "Repository layout should list the top-level paths"
    for path in paths:
        assert (ROOT / path).exists(), f"layout lists missing path {path}"
