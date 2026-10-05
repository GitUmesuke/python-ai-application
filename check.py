"""設定とAI接続を点検する。

実行方法（プロジェクト直下で）:
    .venv\\Scripts\\python.exe check.py

アプリが動かないとき、原因が「環境」「設定」「AI側」のどこにあるかを
切り分けるために使います。画面を開かずに確認できます。
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# 失敗の詳細（英語のエラー文など）はここに集め、最後にまとめて出す。
# 画面と同じ方針で、主要部には「何が起きたか」と「次にどうするか」だけを出す。
_details: list[str] = []
_todo: list[str] = []


def ok(message: str) -> None:
    print(f"  [ OK ] {message}")


def ng(message: str, *, todo: str = "", detail: str = "") -> None:
    print(f"  [ NG ] {message}")
    if todo:
        print(f"         → {todo}")
        _todo.append(todo)
    if detail:
        _details.append(detail)


def note(message: str) -> None:
    print(f"  [ -- ] {message}")


def section(title: str) -> None:
    print(f"\n{title}")


# ------------------------------------------------------------------
print("=" * 60)
print(" AIライティングツール 設定の点検")
print("=" * 60)

section("1. Python と必要なライブラリ")

print(f"  使用中のPython: {sys.executable}")
print(f"  バージョン    : {sys.version.split()[0]}")

if ".venv" not in sys.executable:
    note(
        "仮想環境(.venv)のPythonではありません。"
        "`.venv\\Scripts\\python.exe check.py` で実行するのが確実です。"
    )

missing_libs = []
for lib, package in [("dotenv", "python-dotenv"), ("streamlit", "streamlit")]:
    try:
        __import__(lib)
        ok(f"{package} は入っています")
    except ImportError as exc:
        missing_libs.append(package)
        ng(
            f"{package} が入っていません",
            todo=".venv\\Scripts\\python.exe -m pip install -r requirements.txt を実行する",
            detail=f"{type(exc).__name__}: {exc}",
        )

if missing_libs:
    print("\n必要なライブラリが足りないため、ここで中断します。")
    print("次にすること:")
    for item in dict.fromkeys(_todo):
        print(f"  ・{item}")
    raise SystemExit(1)


from core import config  # noqa: E402  （ライブラリの確認後に読み込む）
from core import llm  # noqa: E402

# ------------------------------------------------------------------
section("2. 使うAIの設定")

print(f"  core/config.py の PROVIDER: {config.PROVIDER}")

provider_file = PROJECT_ROOT / "core" / "providers" / f"{config.PROVIDER}.py"
if provider_file.exists():
    ok(f"接続ファイルがあります（core/providers/{config.PROVIDER}.py）")
else:
    ng(
        f"接続ファイルが見つかりません（core/providers/{config.PROVIDER}.py）",
        todo="core/config.py の PROVIDER のつづりを確認する",
    )

if config.PROVIDER == "stub":
    note("現在はダミー動作です。本物のAIにはつながっていません。")
    note("AIを決めたら、core/providers/ にファイルを追加し PROVIDER を書き換えてください。")

# ------------------------------------------------------------------
section("3. APIキー")

status = config.api_key_status()

if status == config.KEY_NOT_REQUIRED:
    note("今の設定ではAPIキーは不要です（ダミー動作中）。")
elif status == config.KEY_OK:
    ok(f".env の {config.API_KEY_ENV} は設定されています")
else:
    exists = config.ENV_PATH.exists()
    ng(
        f".env の {config.API_KEY_ENV} が設定されていません",
        todo=(
            f".env を作り、{config.API_KEY_ENV}= の右側にキーを貼り付ける"
            if not exists
            else f".env の {config.API_KEY_ENV} の行にキーが入っているか確認する"
        ),
    )
    if not exists:
        note(".env がまだありません（.env.example を複製して作ります）")
        note("※ Windowsは拡張子が隠れます。.env.txt になっていないか確認してください。")

# ------------------------------------------------------------------
section("4. 実際に1回生成してみる")

models = list(config.MODELS.keys())
if not models:
    ng(
        "core/config.py の MODELS が空です",
        todo="使えるモデル名を MODELS に1つ以上書く",
    )
else:
    model = config.DEFAULT_MODEL if config.DEFAULT_MODEL in models else models[0]
    print(f"  試すモデル: {model}")

    try:
        chunks = list(
            llm.generate_stream(
                "「設定の点検に成功しました」とだけ返してください。",
                model=model,
                system_instruction="あなたは動作確認用の応答をする助手です。",
                temperature=0.0,
            )
        )
        text = "".join(chunks)

        if text.strip():
            ok(f"生成できました（{len(text)}文字）")
            preview = text.strip().replace("\n", " ")[:60]
            print(f"         返ってきた文章の先頭: {preview}...")
        else:
            ng(
                "生成は通りましたが、中身が空でした",
                todo="別のモデルで試す、または入力の表現を変える",
            )
    except llm.LLMError as exc:
        kind_label = {
            llm.LLMError.KIND_TRANSIENT: "一時的な問題（待てば直ります）",
            llm.LLMError.KIND_QUOTA: "利用量・料金プランの制約（設定ミスではありません）",
            llm.LLMError.KIND_CONFIG: "設定の問題",
            llm.LLMError.KIND_INPUT: "入力内容の問題",
            llm.LLMError.KIND_UNKNOWN: "原因不明",
        }.get(exc.kind, exc.kind)

        ng(exc.message, detail=exc.detail)
        print(f"         種別: {kind_label}")
        if exc.hint:
            for line in exc.hint.splitlines():
                if line.strip():
                    print(f"         → {line}")
            _todo.append(exc.hint.splitlines()[0])

# ------------------------------------------------------------------
print("\n" + "=" * 60)

if _todo:
    print(" 次にすること")
    print("=" * 60)
    for item in dict.fromkeys(_todo):
        print(f"  ・{item}")
else:
    print(" 問題は見つかりませんでした。")
    print("=" * 60)
    print("  起動: .venv\\Scripts\\streamlit.exe run app.py")

if _details:
    print("\n" + "-" * 60)
    print(" 技術的な詳細（原因究明が必要なときだけ見てください）")
    print("-" * 60)
    for detail in _details:
        print(f"  {detail}")

raise SystemExit(1 if _todo else 0)
