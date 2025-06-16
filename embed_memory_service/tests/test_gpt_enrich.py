import sys
import os
import types
import json
import asyncio

SERVICE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, SERVICE_DIR)

os.environ["USE_GPT_SUMMARY"] = "true"

dummy_openai = types.ModuleType("openai")
dummy_openai.ChatCompletion = types.SimpleNamespace(create=lambda **kw: None)
dummy_openai.__spec__ = types.SimpleNamespace()
sys.modules["openai"] = dummy_openai
import main


def test_gpt_enrich_success():
    main.OPENAI_API_KEY = "test"
    main.openai = types.SimpleNamespace(
        ChatCompletion=types.SimpleNamespace(
            create=lambda **kw: types.SimpleNamespace(
                choices=[
                    types.SimpleNamespace(
                        message={
                            "content": json.dumps(
                                {
                                    "summary": "sum",
                                    "persona_tags": ["engineer"],
                                    "gravity_score": 0.7,
                                }
                            )
                        }
                    )
                ]
            )
        )
    )
    summary, tags, score = asyncio.run(main.gpt_enrich("sentence", []))
    assert summary == "sum"
    assert tags == ["engineer"]
    assert score == 0.7


def test_gpt_enrich_fallback():
    main.OPENAI_API_KEY = "test"
    main.openai = types.SimpleNamespace(
        ChatCompletion=types.SimpleNamespace(
            create=lambda **kw: (_ for _ in ()).throw(Exception("fail"))
        )
    )
    summary, tags, score = asyncio.run(main.gpt_enrich("abc", ["t"]))
    assert summary.startswith("abc")
    assert tags == ["t"]
    assert score == 0.5
