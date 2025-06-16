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

# Stub psycopg2 to avoid postgres dependency
dummy_psycopg2 = types.ModuleType("psycopg2")
dummy_psycopg2.extensions = types.SimpleNamespace(cursor=object, connection=object)
sys.modules["psycopg2"] = dummy_psycopg2

from truth_service.main import embed_text


def test_embed_text_dimension():
    vec = embed_text("hello world")
    assert isinstance(vec, list)
    assert len(vec) == 384
