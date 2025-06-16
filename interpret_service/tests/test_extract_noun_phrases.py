import sys
import os
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)


# Stub spacy to avoid heavy model loading
def dummy_nlp(text):
    parts = ["Pressure", "88 psi", "noon"]
    chunks = [types.SimpleNamespace(text=p) for p in parts]
    return types.SimpleNamespace(noun_chunks=chunks)


dummy_spacy = types.ModuleType("spacy")
dummy_spacy.load = lambda *a, **k: dummy_nlp
sys.modules["spacy"] = dummy_spacy

from interpret_service.interpret_worker import extract_noun_phrases


def test_extract_noun_phrases():
    text = "Pressure was 88 psi at noon."
    phrases = extract_noun_phrases(text)
    assert "Pressure" in phrases
    assert "88 psi" in phrases
    assert "noon" in phrases
