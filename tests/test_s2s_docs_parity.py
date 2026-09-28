"""Keep public docs, SDK metadata, and native realtime claims aligned."""

from pathlib import Path
import json
import re


ROOT = Path(__file__).resolve().parents[1]
MODELS = (
    "gpt-realtime-2.1",
    "gpt-live-1",
    "gemini-3.1-flash-live-preview",
    "grok-voice-latest",
    "hydra-v1.1",
    "hydra-v1.0",
)
TRANSPORTS = ("Supafone-managed", "Twilio", "Telnyx", "Plivo", "SIP")


def test_public_native_realtime_docs_and_sdk_are_aligned():
    docs = [
        ROOT / "README.md",
        ROOT / "docs" / "realtime-agent-factory.md",
        ROOT / "gitbook" / "README.md",
        ROOT / "gitbook" / "realtime-agent-factory.md",
        ROOT / "sdk-ts" / "README.md",
    ]
    for path in docs:
        body = path.read_text(encoding="utf-8")
        for model in MODELS:
            assert model in body, path

    guide = (ROOT / "gitbook" / "realtime-agent-factory.md").read_text(encoding="utf-8")
    for transport in TRANSPORTS:
        assert transport in guide

    assert 'realtime-agent-factory.md' in (ROOT / "gitbook" / "SUMMARY.md").read_text(encoding="utf-8")
    assert 'Native Realtime Agent Factory: realtime-agent-factory.md' in (ROOT / "mkdocs.yml").read_text(encoding="utf-8")


def test_public_docs_use_one_canonical_labs_path():
    paths = [ROOT / "README.md", ROOT / "docs", ROOT / "gitbook", ROOT / "sdk-ts" / "README.md"]
    stale = []
    for path in paths:
        files = [path] if path.is_file() else path.rglob("*.md")
        for file in files:
            body = file.read_text(encoding="utf-8")
            if "labs.supafone.ai/docs.html" in body:
                stale.append(file)
    assert not stale
    assert "https://labs.supafone.ai/docs/" in (ROOT / "README.md").read_text(encoding="utf-8")


def test_package_metadata_matches_release_version():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package = json.loads((ROOT / "sdk-ts" / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "sdk-ts" / "package-lock.json").read_text(encoding="utf-8"))
    assert re.search(r'^version = "0\.7\.1"$', pyproject, flags=re.MULTILINE)
    assert '__version__ = "0.7.1"' in (ROOT / "src/supafone_labs/__init__.py").read_text()
    assert package["version"] == "0.7.0"
    assert lock["version"] == "0.7.0"
    assert lock["packages"][""]["version"] == "0.7.0"
