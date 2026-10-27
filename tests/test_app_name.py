import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOOKUP = re.compile(r'modal\.App\.lookup\("([^"]+)"')


def test_modal_app_is_named_fife():
    for rel in ("agent/run.py", "demos/common.py"):
        assert LOOKUP.findall((ROOT / rel).read_text()) == ["fife"], rel


def test_sandbox_tags_mark_fife():
    assert '"app": "fife"' in (ROOT / "agent/run.py").read_text()


def test_no_stale_sandbox_demo_references():
    skip = {".git", ".venv", "node_modules", "__pycache__"}
    for p in ROOT.rglob("*"):
        if p.is_file() and not skip & set(p.parts) and p != pathlib.Path(__file__).resolve():
            try:
                text = p.read_text()
            except UnicodeDecodeError:
                continue
            assert "sandbox-demo" not in text, p
