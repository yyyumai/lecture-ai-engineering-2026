from types import SimpleNamespace

from app import ask as ask_module


def test_main_reuses_chat_for_follow_up_questions(monkeypatch):
    class FakeChat:
        def __init__(self):
            self.questions = []

        def send_message(self, question):
            self.questions.append(question)
            return SimpleNamespace(text=f"answer to {question}", usage_metadata=None)

    class FakeChats:
        def __init__(self):
            self.chat = FakeChat()
            self.created = 0

        def create(self, model):
            self.created += 1
            return self.chat

    class FakeClient:
        def __init__(self):
            self.chats = FakeChats()

    fake_client = FakeClient()
    follow_up = iter(["Why?", "exit"])
    monkeypatch.setattr(ask_module.genai, "Client", lambda api_key: fake_client)
    monkeypatch.setattr(ask_module, "get_api_key", lambda: "test-key")
    monkeypatch.setattr("builtins.input", lambda prompt: next(follow_up))
    monkeypatch.setattr("sys.argv", ["app.ask", "First question"])

    ask_module.main()

    assert fake_client.chats.created == 1
    assert fake_client.chats.chat.questions == ["First question", "Why?"]