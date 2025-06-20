import sys
import os
import types
import importlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

# ensure psycopg2 has expected attributes even if stubbed by other tests
if "psycopg2" not in sys.modules:
    sys.modules["psycopg2"] = types.ModuleType("psycopg2")
if not hasattr(sys.modules["psycopg2"], "extensions"):
    sys.modules["psycopg2"].extensions = types.SimpleNamespace(
        cursor=object, connection=object
    )


# stub sentence_transformers
class DummyVector(list):
    def tolist(self):
        return list(self)


class DummyModel:
    def encode(self, text):
        return DummyVector([0.0] * 384)


dummy_st = types.ModuleType("sentence_transformers")
dummy_st.SentenceTransformer = lambda *args, **kwargs: DummyModel()
sys.modules["sentence_transformers"] = dummy_st

dummy_psycopg2 = types.ModuleType("psycopg2")
dummy_psycopg2.extensions = types.SimpleNamespace(connection=object, cursor=object)
sys.modules["psycopg2"] = dummy_psycopg2
# stub pandas for transformers dependency
module = types.SimpleNamespace()
module.__spec__ = importlib.machinery.ModuleSpec("pandas", loader=None)
module.Series = dict
sys.modules["pandas"] = module


def reload_truth():
    if "truth_service.main" in sys.modules:
        del sys.modules["truth_service.main"]
    return importlib.import_module("truth_service.main")
# Stub psycopg2 to avoid postgres dependency
dummy_psycopg2 = types.ModuleType("psycopg2")
dummy_psycopg2.extensions = types.SimpleNamespace(cursor=object, connection=object)
sys.modules["psycopg2"] = dummy_psycopg2

# Stub psycopg2 extensions
dummy_pg = types.ModuleType("psycopg2")
dummy_pg.extensions = types.SimpleNamespace(cursor=object, connection=object)
sys.modules["psycopg2"] = dummy_pg

from truth_service.main import embed_text
sys.modules.pop("pandas", None)

def test_embed_text_dimension():
    mod = reload_truth()
    vec = mod.embed_text("hello world")
    assert isinstance(vec, list)
    assert len(vec) == 384


def test_openai_embedding(monkeypatch):
    os.environ["USE_OPENAI_EMBEDDING"] = "true"
    sys.modules["openai"] = types.SimpleNamespace(
        Embedding=types.SimpleNamespace(
            create=lambda **kw: {"data": [{"embedding": [0.0] * 1536}]}
        )
    )
    mod = reload_truth()
    mod.qdrant = types.SimpleNamespace(upsert=lambda **kw: None)
    uid = mod.store_sentence(
        "hello",
        {"well_id": "w", "source": "s", "tags": [], "timestamp": "t"},
    )
    assert isinstance(uid, str)
    vec = mod.embed_text("hi")
    assert len(vec) == 1536
    os.environ.pop("USE_OPENAI_EMBEDDING")
