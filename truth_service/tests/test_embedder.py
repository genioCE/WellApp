import sys
import os
import types
import importlib.machinery

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)


# Stub sentence_transformers to avoid network downloads
class DummyVector(list):
    def tolist(self):
        return list(self)


class DummyModel:
    def encode(self, text):
        return DummyVector([0.0] * 384)


dummy_st = types.ModuleType("sentence_transformers")
dummy_st.SentenceTransformer = lambda *args, **kwargs: DummyModel()
sys.modules["sentence_transformers"] = dummy_st

# Stub pandas for transformers import
module = types.ModuleType("pandas")
module.__spec__ = importlib.machinery.ModuleSpec("pandas", loader=None)
module.Series = dict
sys.modules["pandas"] = module

from truth_service.main import embed_text


def test_embed_text_dimension():
    vec = embed_text("hello world")
    assert isinstance(vec, list)
    assert len(vec) == 384
