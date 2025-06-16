import sys
import os
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

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

from interpret_service.interpret_worker import extract_noun_phrases


def test_extract_noun_phrases():
    text = "Pressure was 88 psi at noon."
    phrases = extract_noun_phrases(text)
    assert "Pressure" in phrases
    assert "88 psi" in phrases
    assert "noon" in phrases
