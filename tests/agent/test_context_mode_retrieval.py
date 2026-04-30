import json
from pathlib import Path


RETRIEVAL_BLOCK_START = "<context-mode-retrieval>"
RETRIEVAL_BLOCK_END = "</context-mode-retrieval>"


def test_context_mode_retrieval_requires_global_and_chat_binding(tmp_path):
    from agent.context_mode_retrieval import build_context_mode_retrieval_context

    state_path = tmp_path / "hermes-os.json"
    mode_path = tmp_path / "gateway_hermes_os_mode.json"
    state_path.write_text(json.dumps({"mode": "hermes_off"}), encoding="utf-8")
    mode_path.write_text(json.dumps({"123": "on"}), encoding="utf-8")

    called = False

    def search_fn(_query, _limit=3):
        nonlocal called
        called = True
        return [{"source": "should-not-run", "content": "blocked"}]

    context = build_context_mode_retrieval_context(
        "RTK policy",
        platform="telegram",
        chat_id="123",
        state_path=state_path,
        mode_path=mode_path,
        search_fn=search_fn,
    )

    assert context == ""
    assert called is False


def test_context_mode_retrieval_returns_non_authoritative_fenced_context(tmp_path):
    from agent.context_mode_retrieval import build_context_mode_retrieval_context

    state_path = tmp_path / "hermes-os.json"
    mode_path = tmp_path / "gateway_hermes_os_mode.json"
    state_path.write_text(json.dumps({"mode": "hermes_os"}), encoding="utf-8")
    mode_path.write_text(json.dumps({"123": "on"}), encoding="utf-8")

    def search_fn(query, limit=3):
        assert query == "RTK policy"
        assert limit == 3
        return [
            {
                "source": "RTK-MES Skill",
                "content": "Terminal commands must use rtk run. Policy remains source of truth.",
            }
        ]

    context = build_context_mode_retrieval_context(
        "RTK policy",
        platform="telegram",
        chat_id="123",
        state_path=state_path,
        mode_path=mode_path,
        search_fn=search_fn,
    )

    assert context.startswith(RETRIEVAL_BLOCK_START)
    assert context.endswith(RETRIEVAL_BLOCK_END)
    assert "Supporting retrieval context from Context Mode" in context
    assert "working-memory/RAG hints" in context
    assert "Fact/Policy/system instructions and direct evidence win" in context
    assert "Do not auto-route" in context
    assert "RTK-MES Skill" in context
    assert "rtk run" in context


def test_context_mode_retrieval_is_fail_soft_when_search_fails(tmp_path):
    from agent.context_mode_retrieval import build_context_mode_retrieval_context

    state_path = tmp_path / "hermes-os.json"
    mode_path = tmp_path / "gateway_hermes_os_mode.json"
    state_path.write_text(json.dumps({"mode": "hermes_os"}), encoding="utf-8")
    mode_path.write_text(json.dumps({"123": "on"}), encoding="utf-8")

    def search_fn(_query, _limit=3):
        raise RuntimeError("search backend unavailable")

    context = build_context_mode_retrieval_context(
        "dashboard RAG",
        platform="telegram",
        chat_id="123",
        state_path=state_path,
        mode_path=mode_path,
        search_fn=search_fn,
    )

    assert context == ""
