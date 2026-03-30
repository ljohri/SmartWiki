from pathlib import Path

import pytest

from file_parser import FileParseError, extract_text

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_extract_md():
    raw = (FIXTURES / "test.md").read_bytes()
    text = extract_text("doc.md", raw)
    assert "markdown" in text


def test_extract_txt():
    raw = (FIXTURES / "sample.txt").read_bytes()
    text = extract_text("sample.txt", raw)
    assert "SmartWiki" in text


def test_unsupported_ext():
    with pytest.raises(FileParseError):
        extract_text("x.bin", b"abc")
