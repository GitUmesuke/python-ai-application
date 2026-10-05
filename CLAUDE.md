# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## このプロジェクトについて

個人用のAIライティングツール（Streamlit製）。DB・認証なし、1人用、ローカル実行のみ。
`C:\ClaudeDev\06-python-ai-application` にある同等品を、**練習としてゼロから作り直したもの**。
重複はユーザーが承知の上で選択している。改めて問題として持ち出さないこと。

使うAIは **Gemini**（`core/providers/gemini.py`、`google-genai`）。キーは `.env` の `GEMINI_API_KEY`。
`core/providers/stub.py`（ダミー）も残してある。`core/config.py` の `PROVIDER` を `"stub"` にすると、
キー無しで画面の全動作を確認できる（入力から組み立てたプロンプトをそのまま返す）。

**モデルは混雑（503）で失敗することがある。** `LLMError.kind` が `transient` になるので、
設定不備として扱わないこと。`core/llm.py` が、1文字も届いていない場合に限り1回だけ自動で試し直す。
既定を `gemini-3.6-flash` にしているのは実測の結果（2026-10-05 時点で `gemini-3.8-flash` は
11回中6回が混雑で失敗、3.6 と 3.5-lite は失敗なし）。モデルを足すときは実際に数回呼んで確かめる。

**無料枠はモデルごとに1日20リクエスト**（`generate_content_free_tier_requests`, limit: 20）。
使い切ると `kind` が `quota` になり、翌日まで戻らない。モデルを変えれば別枠が使える。
**検証でAPIを何度も呼ぶと、ユーザーが実際に使う分を食いつぶす。**
動作確認は `PROVIDER="stub"` で済ませ、本物のAPIを使うのは最後の1〜2回にとどめること。

UI・コード内コメント・README はすべて日本語。
Git管理はしていない。変更履歴も取り消しも無いので、既存ファイルを大きく書き換える前に確認を取る。

## コマンド

依存は `.venv` の中にある（`python` / `pip` をそのまま打っても動くが、それはPC共通の方を指す）。

```
起動      .venv\Scripts\streamlit.exe run app.py      → http://localhost:8501
診断      .venv\Scripts\python.exe check.py           → 問題があれば終了コード 1
環境構築  py -m venv .venv
          .venv\Scripts\python.exe -m pip install -r requirements.txt
API確認   .venv\Scripts\streamlit.exe docs st.<command>
```

`check.py` は ライブラリ → PROVIDER設定 → APIキー → 実際に1回生成、の順に点検して
「次にすること」を日本語で出す。アプリが動かないときの切り分けはまずこれ。

## 動作確認のしかた

テストフレームワークは入れていない。確認は Streamlit 同梱の `AppTest` を直接使う
（描画だけでなく、フォーム送信から生成までを実際に通す）。

```bash
PYTHONIOENCODING=utf-8 PYTHONPATH=. ./.venv/Scripts/python.exe - <<'PY'
from streamlit.testing.v1 import AppTest
at = AppTest.from_file('app_pages/blog.py', default_timeout=90).run()
at.text_area[0].set_value('テーマ')   # ここで .run() を挟まないこと
at.button[0].click().run()            # 値の設定と送信は同じ run にまとめる
print([str(e.value) for e in at.exception])
PY
```

- **フォーム内の入力は `set_value()` の直後に `.run()` を挟むと値が捨てられる。**
  `st.form` は送信時にまとめて確定するため。上の順序を守る
- `app_pages/*.py` を単体で動かすには `PYTHONPATH=.` が要る。ただし `home.py` は
  `st.page_link` を含み `st.navigation` が無いと失敗するので、`app.py` 経由で確認する
- `PYTHONIOENCODING=utf-8` が無いと、日本語の出力が cp932 で化けて読めない
- エラー表示の確認は `.env` に `STUB_FORCE_ERROR=1` を置く（ダミーがわざと失敗する）
- `st.page_link` のクリックは AppTest では再現できない。リンクの結び付きは
  「未登録ページへのリンクは Streamlit が例外を出す」ことを利用して確認する

## 構造

1画面ぶんの流れ:

```
app.py ─→ core/menu.py (ITEMS) ─→ app_pages/<機能>.py ─→ core.ui.render_tool(SPEC)
                                                            │
                                      tools/<機能>.py の SPEC ┘
                                                            ↓
                                               core.llm.generate_stream
                                                            ↓
                                        core/providers/<PROVIDER>.py
```

- **1機能 = `tools/<名前>.py` の `SPEC`（`ToolSpec`）1つ。** 書くのは入力欄の定義（`Field`）と
  プロンプトの組み立て（`build_prompt`）だけ。画面の描画もAPIの呼び方も書かない
- `core/ui.py` が `ToolSpec` から フォーム → 生成 → 逐次表示 → コピー／保存／履歴 までを描く。
  見た目や共通の挙動の変更は、このファイル1か所で全機能に効く
- `app_pages/*.py` は3行（`SPEC` を `render_tool` に渡すだけ）
- **画像はプロンプトに混ぜない。** `Field(type="image")` を置くと `core/ui.py` が
  `tools.base.Image` の一覧にまとめ、`llm.generate_stream(..., images=[...])` として
  AIへ直接渡す。`build_prompt` が受け取るのは文字だけ（枚数を見て指示文を足すのは可）。
  画像を読めないAIの接続ファイルは、この引数を無視してよい
- `core/menu.py` の `ITEMS` が、上部メニューとホーム画面のリンクの**唯一の出典**。
  タイトル・アイコン・説明文は `SPEC` から取るので、同じ内容を2か所に書かない

**機能を1つ増やす**: `tools/` に SPEC を作る → `app_pages/` に3行のファイル → `core/menu.py` の `ITEMS` に1行

**使うAIを差し替える**: `core/providers/` に
`generate_stream(prompt, *, model, system_instruction, temperature) -> Iterator[str]` を持つ
ファイルを1つ作り、`core/config.py` の `PROVIDER` / `API_KEY_ENV` / `MODELS` を書き換える。
それ以外は触らない。`MODELS` には、実際に1回生成を通して使えたモデルだけを書く。

## このリポジトリの決めごと

- エラーは `core.llm.LLMError` に統一する。`message`（何が起きたか／1〜2文）、
  `hint`（次にどうすればよいか）、`detail`（英語の原文）、
  `kind`（`transient` / `quota` / `config` / `input` / `unknown`）。
  画面でも `check.py` でも `detail` は折りたたみ・末尾にだけ出す。
  AI固有のエラー（キー誤り・混雑など）の日本語への言い換えは `core/providers/` 側の責任
- `.env` は `dotenv_values()` で**毎回読み直す**。`load_dotenv()` は使わない
  （一度 `os.environ` に書き込むため、起動後の変更やキー削除が反映されなくなる）
- ページ用フォルダは `app_pages/`。`pages/` は Streamlit の旧機能と衝突するので使わない
- CSS は書かない。見た目は Streamlit の標準要素と `.streamlit/config.toml` で済ませる。
  アイコンは Material Symbols（`:material/...:`）
- `.streamlit/config.toml` の `address = "localhost"` は意図的。既定のままだと
  同一ネットワークの他端末からアクセスできてしまうため
- 生成結果の自動保存は入れない（ダウンロードボタンのみ）。履歴はセッション内だけで、
  ブラウザを閉じれば消える

## 変更したあと、ユーザー側で必要なこと

報告に含める。Claude 側では代われない操作がある。

- **コードを直してもブラウザは自動で更新されない。** `runOnSave` は既定で無効なので、
  画面右上に出る `Rerun` を押してもらう（`Always rerun` を選べば以降は自動になる）
- `.env` を変えたとき: ブラウザの**再読み込み**だけでよい（値は呼び出しのたびに読み直すので
  アプリの再起動は不要）
- `requirements.txt` を変えたとき: インストールし直し → アプリの**再起動**
- **アプリはユーザー自身が別のターミナルで起動していることがある。** その場合 Claude 側からは
  止められないので、再起動が必要なときはその旨を伝えて依頼する
