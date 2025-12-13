import pathlib
import re
import sys

from fastapi.testclient import TestClient

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
sys.path.append(str(ROOT / "../unison-common/src"))

from main import app  # noqa: E402


def test_legacy_routes_absent():
    client = TestClient(app)
    assert client.get("/dashboard").status_code == 404
    assert client.post("/gesture/select", json={"any": "thing"}).status_code == 404


def test_no_legacy_layout_terms_in_surface_sources():
    sources_root = ROOT / "src"
    text = read_tree_text(sources_root, extensions={".py", ".js", ".html", ".css"})

    forbidden = [
        r"\bdashboard\b",
        r"\bcards?\b",
        r"\bpanel(s)?\b",
        r"\bsidebar(s)?\b",
        r"\bdock(ed)?\b",
        r"\bwindowing\b",
    ]
    for pattern in forbidden:
        assert not re.search(pattern, text, flags=re.IGNORECASE), pattern

    assert "setinterval(" not in text.lower()


def test_no_person_as_user_language():
    roots = [ROOT / "src", ROOT / "tests", ROOT / "README.md", ROOT / "ANTI_PATTERN_MAP.md"]
    text = []
    for r in roots:
        if r.is_file():
            text.append(r.read_text(encoding="utf-8"))
        else:
            text.append(read_tree_text(r, extensions={".py", ".js", ".html", ".md"}))
    joined = "\n".join(text)

    assert not re.search(r"\buser\b", joined, flags=re.IGNORECASE)


def read_tree_text(root: pathlib.Path, extensions: set[str]) -> str:
    chunks: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.suffix not in extensions:
            continue
        chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)

