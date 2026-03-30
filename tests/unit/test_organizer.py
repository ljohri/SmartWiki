import json

import pytest

from organizer import OrganizerDecision, _parse_json_from_claude, build_organizer_prompt


def test_parse_json_from_claude_plain():
    data = _parse_json_from_claude(
        '{"targetPath": "/docs/engineering/foo", "pageTitle": "Foo", "suggestedTags": ["a"], "summary": "S"}'
    )
    assert data["targetPath"] == "/docs/engineering/foo"


def test_parse_json_from_claude_with_noise():
    text = 'Here you go:\n{"targetPath": "/x", "pageTitle": "T", "suggestedTags": [], "summary": "S"}\n'
    data = _parse_json_from_claude(text)
    assert data["pageTitle"] == "T"


def test_organizer_decision_normalizes_path():
    d = OrganizerDecision.model_validate(
        {
            "targetPath": "docs/product/no-leading",
            "pageTitle": "P",
            "suggestedTags": [],
            "summary": "",
        }
    )
    assert d.targetPath.startswith("/")


def test_build_organizer_prompt_contains_metadata():
    p = build_organizer_prompt(
        wiki_tree="[page] / — root",
        title="T",
        category="engineering",
        tags="a,b",
        description="D",
        content_excerpt="Body",
    )
    assert "engineering" in p
    assert "Body" in p


def test_parse_json_invalid():
    with pytest.raises((ValueError, json.JSONDecodeError)):
        _parse_json_from_claude("not json")
