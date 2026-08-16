"""Documentation release gates for framework coverage and GitBook structure."""
from __future__ import annotations

import re
from pathlib import Path

from supafone_labs.runtime.provider_contracts import PROVIDER_INJECTION_CONTRACTS


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_MATRICES = (
    REPO_ROOT / "gitbook" / "framework-support.md",
    REPO_ROOT / "docs" / "providers.md",
)
STALE_FRAMEWORK_LANGUAGE = (
    "ten frameworks",
    "10 frameworks",
    "possible for all 10",
    "cartesia/pipecat are n/a",
)


def test_every_audited_runtime_is_in_each_documentation_matrix():
    expected_ids = {contract.provider_id for contract in PROVIDER_INJECTION_CONTRACTS}
    assert len(expected_ids) == 14

    for path in CANONICAL_MATRICES:
        text = path.read_text(encoding="utf-8")
        documented_ids = set(re.findall(r'id="provider-([a-z0-9_]+)"', text))
        assert documented_ids == expected_ids, path.relative_to(REPO_ROOT)
        assert "fourteen audited" in text.lower()
        assert "GenericWebhookAdapter" in text


def test_framework_support_preserves_honest_support_boundaries():
    text = CANONICAL_MATRICES[0].read_text(encoding="utf-8")
    required_phrases = (
        "Managed native control",
        "Native control",
        "Developer-owned context",
        "Observation only",
        "Explicit host hook",
        "does **not** mean Supafone hosts every provider account automatically",
        "Unsupported or uncertain capability always degrades to no action",
    )
    for phrase in required_phrases:
        assert phrase in text


def test_public_docs_do_not_restore_the_stale_ten_framework_claim():
    paths = [REPO_ROOT / "README.md"]
    paths.extend((REPO_ROOT / "docs").glob("*.md"))
    paths.extend((REPO_ROOT / "gitbook").glob("*.md"))

    for path in paths:
        lowered = path.read_text(encoding="utf-8").lower()
        for phrase in STALE_FRAMEWORK_LANGUAGE:
            assert phrase not in lowered, f"{path.relative_to(REPO_ROOT)}: {phrase}"


def test_gitbook_is_problem_first_and_uses_the_real_logo():
    landing = (REPO_ROOT / "gitbook" / "README.md").read_text(encoding="utf-8")
    assert landing.index("## Why we built it") < landing.index("## The architecture")
    assert landing.index("## The architecture") < landing.index("## Framework coverage")
    assert '.gitbook/assets/supafone-logo.png' in landing

    source_logo = REPO_ROOT / "gitbook" / ".gitbook" / "assets" / "supafone-logo.png"
    mkdocs_logo = REPO_ROOT / "docs" / "assets" / "supafone-logo.png"
    assert source_logo.read_bytes() == mkdocs_logo.read_bytes()


def test_gitbook_summary_links_resolve():
    summary = (REPO_ROOT / "gitbook" / "SUMMARY.md").read_text(encoding="utf-8")
    links = re.findall(r"\[[^\]]+\]\(([^)]+\.md)\)", summary)
    assert links
    assert len(links) == len(set(links)), "GitBook navigation contains duplicate pages"
    for link in links:
        assert (REPO_ROOT / "gitbook" / link).is_file(), link


def test_gitbook_navigation_follows_the_developer_journey():
    summary = (REPO_ROOT / "gitbook" / "SUMMARY.md").read_text(encoding="utf-8")
    sections = re.findall(r"^## (.+)$", summary, flags=re.MULTILINE)
    assert sections == [
        "Understand Supafone",
        "Start Building",
        "Supervise Existing Agents",
        "Build Complete Agents",
        "Run Calls and Campaigns",
        "Test and Improve",
        "Operate and Administer",
    ]


def test_gitbook_configuration_points_at_the_documentation_root():
    config = (REPO_ROOT / ".gitbook.yaml").read_text(encoding="utf-8")
    assert "root: ./gitbook/" in config
    assert "readme: README.md" in config
    assert "summary: SUMMARY.md" in config
