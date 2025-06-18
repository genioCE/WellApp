import sys
import os
from fastapi.middleware.cors import CORSMiddleware

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from now_file_ingestor.main import app


def test_cors_middleware_present():
    assert any(isinstance(m.cls, type) and m.cls is CORSMiddleware for m in app.user_middleware)
