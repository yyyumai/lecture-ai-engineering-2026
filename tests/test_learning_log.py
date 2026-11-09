"""承認前・承認後・拒否時の保存動作を、APIなしで確認する。"""

import pytest
from pydantic_ai import DeferredToolRequests, DeferredToolResults
from pydantic_ai.messages import ToolReturnPart
from pydantic_ai.models.test import TestModel

from app import tools
from app.agent import agent, main, run_with_approval


@pytest.fixture
def log_dir(tmp_path, monkeypatch):
    path = tmp_path / "learning_log"
    monkeypatch.setattr(tools, "LEARNING_LOG_DIR", path)
    return path


def test_save_learning_log_preserves_content_and_existing_records(log_dir):
    tools.save_learning_log("第3回：ツールの実行前に承認を挟む。")
    tools.save_learning_log("次回はTestModelの使い方を復習する。")
    paths = list(log_dir.glob("*.md"))
    assert len(paths) == 2
    assert {p.read_text(encoding="utf-8") for p in paths} == {
        "第3回：ツールの実行前に承認を挟む。\n",
        "次回はTestModelの使い方を復習する。\n",
    }


def test_empty_content_is_not_saved(log_dir):
    assert "空です" in tools.save_learning_log(" \n")
    assert not log_dir.exists()


@pytest.mark.parametrize("approved", [True, False])
def test_agent_defers_save_until_approved(log_dir, approved):
    model = TestModel(call_tools=["save_learning_log"])
    result = agent.run_sync("学習内容を保存して", model=model)
    assert isinstance(result.output, DeferredToolRequests)
    assert not log_dir.exists()
    calls = result.output.approvals
    assert len(calls) == 1
    call = calls[0]
    assert call.tool_name == "save_learning_log"

    resumed = agent.run_sync(
        message_history=result.all_messages(),
        deferred_tool_results=DeferredToolResults(
            approvals={call.tool_call_id: approved}
        ),
        model=model,
    )
    assert isinstance(resumed.output, str)
    returns = [
        part for message in resumed.all_messages() for part in message.parts
        if isinstance(part, ToolReturnPart) and part.tool_name == "save_learning_log"
    ]
    assert returns
    if approved:
        paths = list(log_dir.glob("*.md"))
        assert len(paths) == 1
        assert paths[0].read_text(encoding="utf-8") == call.args_as_dict()["content"] + "\n"
        assert "保存しました" in str(returns[-1].content)
    else:
        assert not log_dir.exists()
        assert "denied" in str(returns[-1].content).lower()


@pytest.mark.parametrize("answer", ["y", "N", "", "yes"])
def test_cli_prompts_before_saving(log_dir, monkeypatch, capsys, answer):
    def respond(prompt):
        # 確認画面に保存する内容が出ており、まだ保存されていない。
        output = capsys.readouterr().out
        assert "save_learning_log" in output
        assert '"content"' in output
        assert not log_dir.exists()
        assert "[y/N]" in prompt
        return answer

    monkeypatch.setattr("builtins.input", respond)
    result = run_with_approval(
        agent, "学習内容を保存して", model=TestModel(call_tools=["save_learning_log"])
    )
    assert isinstance(result.output, str)
    assert log_dir.exists() == (answer == "y")
    # 再開前後の使用量を合計して表示できる。
    assert result.usage.requests >= 2


def test_cli_eof_denies_save(log_dir, monkeypatch):
    def eof(prompt):
        raise EOFError

    monkeypatch.setattr("builtins.input", eof)
    result = run_with_approval(
        agent, "学習内容を保存して", model=TestModel(call_tools=["save_learning_log"])
    )
    assert isinstance(result.output, str)
    assert not log_dir.exists()


def test_main_handles_approval_and_prints_trace(log_dir, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["app.agent", "--trace", "学習内容を保存して"])
    monkeypatch.setattr(
        "app.agent.build_model", lambda: TestModel(call_tools=["save_learning_log"])
    )
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    main()
    output = capsys.readouterr().out
    assert "[承認待ち] save_learning_log" in output
    assert "[tool call]" in output
    assert "[tool return]" in output
    assert "[usage]" in output
    assert len(list(log_dir.glob("*.md"))) == 1
