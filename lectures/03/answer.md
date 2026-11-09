# 第3回 解答

## 演習

- 第1回（素のLLM）とエージェントの回答の違い：
第1回の素のLLMは「AIE2026に関する情報は持っていない」と答えて、講座固有の質問に答えられなかった。エージェントは用語集を検索してから答えるので、「宿題は基礎・実装・発展の3レベルで、どれか1つに取り組めば完了」と用語集どおりに答え、最後に「関係する回：第1回」も示した。
- `--trace` で見えたツール呼び出し（ツール名と引数）：
「LoRAとQLoRAの違いは？」では、`search_glossary({'query': 'LoRA'})` と `search_glossary({'query': 'QLoRA'})` の2回。docstring の「query には調べたい用語を1つだけ入れる」に従い、用語を1つずつ検索していた。
- 1つの質問での LLM 呼び出し回数（`requests`）：
2回（`requests=2, tool_calls=2`）。1回目でツールを呼ぶと決め、ツールの結果を受け取った2回目で回答を作った。2つの検索は1回目のリクエストでまとめて（並列に）呼ばれていた。
- 追加したツールと、docstring に書いた説明：
`make_quiz(lecture: int) -> str`。docstring は「指定した回の用語から1つを選び、確認問題と答えを返す。『第2回の確認問題を出して』のように、復習用の問題を求められたときに使う。lecture には対象の回番号（1始まり）を入れる。指定した回に用語がなければ、どの回に何があるかを分かりやすく示して返す。」と書いた。`INSTRUCTIONS` にも「確認問題を求められたら make_quiz を使う」を足した。
「第2回の内容から確認問題を1問出して」で `make_quiz({'lecture': 2})` が呼ばれ、「事前学習」の問題が出題された（`requests=2, tool_calls=1`）。`uv run pytest -q` は 16 passed。

## 宿題

- 取り組んだレベル：実装
- やったこと：
  - `app/tools.py` に `save_learning_log(content: str)` を追加した。UTF-8のMarkdownファイルを `learning_log/` に保存する。ファイル名はUUIDで生成し、既存ファイルを上書きしない。空の内容は保存しない。
  - `app/agent.py` で `requires_approval=True` を指定して登録し、`output_type` に `DeferredToolRequests` を加えた。
  - CLIでツール名と保存内容を表示する。`y` を入力した場合だけ承認し、会話履歴と `DeferredToolResults` を渡して処理を再開する。それ以外の入力やEOFでは拒否する。
  - `tests/test_learning_log.py` に保存と承認処理のテストを追加した。エージェントのテストにはAPIキー不要のTestModelを使った。
- 結果：
  - `.venv/bin/uv --cache-dir /tmp/aie2026-uv-cache run --frozen pytest -q --tb=short`：全22件成功。
  - 承認待ちではフォルダも作られず、承認後にファイルが1つ作られ、要求された内容と一致することを確認した。拒否時には保存されないことも確認した。
  - CLIの確認処理、入力終了時の拒否、`--trace` のツール呼び出し・戻り値・使用量の表示もTestModelで確認した。
  - `--list-tools` で `save_learning_log` が公開されていることを確認した。
  - 実際のGeminiモデルによるツール選択と応答は未確認。試すコマンド：`.venv/bin/uv run --frozen python -m app.agent --trace "第3回で、ツールの実行前に利用者の承認を挟む仕組みを学んだ、と学習記録に保存して"`。
- 気づき・疑問：コードと実行結果を一緒に確認した後、自分の言葉で追記する。
