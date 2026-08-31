"""
Tests for Content & License Safety Guard.
"""
import pytest
from backend.app.pipeline.safety_guard import ContentLicenseGuard


def test_safety_guard_clean_prompt():
    prompt = "Create a peaceful story about an Indian mother caring for her child during the monsoon season."
    res = ContentLicenseGuard.analyze_prompt(prompt)
    assert res.is_safe is True
    assert res.risk_level == "LOW"
    assert len(res.detected_violations) == 0


def test_safety_guard_protected_character():
    prompt = "Create an epic video of Spider-Man fighting Batman across the city rooftops."
    res = ContentLicenseGuard.analyze_prompt(prompt)
    assert res.is_safe is False
    assert res.risk_level in ["MEDIUM", "HIGH"]
    assert any("Spider-Man" in v for v in res.detected_violations)
    assert any("Batman" in v for v in res.detected_violations)
    assert res.suggested_rewrite is not None
    assert "spider-man" not in res.suggested_rewrite.lower()


def test_safety_guard_celebrity_likeness():
    prompt = "A documentary showing Elon Musk and Donald Trump talking in a boardroom."
    res = ContentLicenseGuard.analyze_prompt(prompt)
    assert res.is_safe is False
    assert any("Elon Musk" in v for v in res.detected_violations)
