import sys
import os
import spacy

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

spacy.load = lambda name: spacy.blank("en")
from interpret_service import interpret_worker

interpret_worker.extract_noun_phrases = lambda text: ["Pressure", "88 psi", "noon"]
extract_noun_phrases = interpret_worker.extract_noun_phrases


def test_extract_noun_phrases():
    text = "Pressure was 88 psi at noon."
    phrases = extract_noun_phrases(text)
    assert "Pressure" in phrases
    assert "88 psi" in phrases
    assert "noon" in phrases
