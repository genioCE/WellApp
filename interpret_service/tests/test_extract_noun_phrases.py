import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from interpret_service.interpret_worker import extract_noun_phrases


def test_extract_noun_phrases():
    text = "Pressure was 88 psi at noon."
    phrases = extract_noun_phrases(text)
    assert "Pressure" in phrases
    assert "88 psi" in phrases
    assert "noon" in phrases
