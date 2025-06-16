import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

import types

dummy_spacy = types.ModuleType("spacy")
dummy_doc = types.SimpleNamespace(
    noun_chunks=[
        types.SimpleNamespace(text="Pressure"),
        types.SimpleNamespace(text="88 psi"),
        types.SimpleNamespace(text="noon"),
    ]
)
dummy_spacy.load = lambda *a, **k: lambda text: dummy_doc
sys.modules["spacy"] = dummy_spacy

from interpret_service.interpret_worker import extract_noun_phrases


def test_extract_noun_phrases():
    text = "Pressure was 88 psi at noon."
    phrases = extract_noun_phrases(text)
    assert "Pressure" in phrases
    assert "88 psi" in phrases
    assert "noon" in phrases
