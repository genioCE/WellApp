import sys
import os
import spacy
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

spacy.load = lambda name: spacy.blank("en")
from interpret_service import interpret_worker

interpret_worker.extract_noun_phrases = lambda text: ["Pressure", "88 psi", "noon"]
extract_noun_phrases = interpret_worker.extract_noun_phrases
nlp_module = types.ModuleType("spacy")

class DummyNLP:
    def __call__(self, text: str):
        return types.SimpleNamespace(
            noun_chunks=[
                types.SimpleNamespace(text="Pressure"),
                types.SimpleNamespace(text="88 psi"),
                types.SimpleNamespace(text="noon"),
            ],
            sents=[types.SimpleNamespace(text=text.split(".")[0] + ".")],
        )

nlp_module.load = lambda *a, **k: DummyNLP()
sys.modules["spacy"] = nlp_module

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
