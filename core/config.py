"""アプリ全体の設定。

「使うAIを変えたい」「モデルを増やしたい」「既定値を変えたい」ときは、
このファイルだけを編集すれば済むようにしてあります。
"""

import os
from pathlib import Path

from dotenv import dotenv_values

# このファイル（core/config.py）から2つ上がプロジェクトの直下
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

APP_TITLE = "AIライティングツール"
APP_ICON = "✍️"


# ------------------------------------------------------------------
# 使うAI
# ------------------------------------------------------------------
# core/providers/ にあるファイル名をそのまま書きます。
# 例）"gemini" と書くと core/providers/gemini.py が使われます。
#
# 別のAIに替えたくなったら、
#   1. core/providers/ にそのAI用のファイルを1つ作る
#   2. 下の PROVIDER / API_KEY_ENV / MODELS を書き換える
# の2手順で切り替わります。他のファイルは直す必要がありません。
# （キー無しで画面を確認したいときは "stub" に戻せます）
PROVIDER = "gemini"

# APIキーを書く .env の項目名。
# 空文字のときは「キーは不要」として扱います（ダミー動作のとき）。
API_KEY_ENV = "GEMINI_API_KEY"

# サイドバーに出すモデルの選択肢。
#
# ここに並べているのは、2026-10-05 に実際に1回ずつ生成を通して
# 「使えた」ことを確認したものだけです。
# 一覧APIの戻り値をそのまま書かないこと（gemini-2.5 系は一覧に残っていましたが、
# 実際に呼ぶと「提供終了」で失敗しました）。
#
# ※ Pro 系（gemini-3.1-pro-preview など）は無料枠では使えません。
#   有料プランに移行したら、ここに1行足すと選べるようになります。
MODELS: dict[str, str] = {
    "gemini-3.6-flash": "既定。品質と安定性のバランスが良い",
    "gemini-3.8-flash": "最新。品質は期待できるが、混雑で失敗しやすい",
    "gemini-3.5-flash-lite": "最速・最安。短い文章の下書き向け",
    "gemini-3.1-flash-lite": "上が混み合っているときの控え",
}
DEFAULT_MODEL = "gemini-3.6-flash"

# 0.0 に近いほど堅実で安定、高いほど発想が広がります
DEFAULT_TEMPERATURE = 0.8


# ------------------------------------------------------------------
# .env の読み込み
# ------------------------------------------------------------------
# 注意: load_dotenv() は使いません。あれは一度 os.environ に値を書き込むため、
# アプリを起動したあとに .env を直しても古い値が残り続けます。
# dotenv_values() ならファイルの「今の中身」だけを読むので、
# .env を書き換えてブラウザを再読み込みすれば反映されます。

def env_value(name: str) -> str:
    """.env の項目をひとつ読む。無ければ空文字を返す。"""
    if not name:
        return ""

    from_file = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}
    value = from_file.get(name) or ""

    # .env が無い場合に限り、OSの環境変数も見る（別PCでの運用に備えて）
    if not ENV_PATH.exists():
        value = os.getenv(name, "")

    # 前後の空白・改行、貼り付け時に付きがちな引用符を取り除く
    return (value or "").strip().strip('"').strip("'").strip()


def flag_enabled(name: str) -> bool:
    """.env の項目が「オン」かどうか。動作確認用のスイッチに使う。"""
    return env_value(name).lower() in {"1", "true", "on", "yes"}


# APIキーの状態。サイドバーの表示に使う
KEY_NOT_REQUIRED = "not_required"  # そもそもキーが要らない（ダミー動作中）
KEY_OK = "ok"                      # 設定済み
KEY_MISSING = "missing"            # 要るのに無い


def get_api_key() -> str | None:
    """APIキーを取得する。未設定・キー不要のときは None。"""
    if not API_KEY_ENV:
        return None

    key = env_value(API_KEY_ENV)

    # .env.example の見本のまま保存されている場合も未設定として扱う
    if not key or key.startswith("ここに"):
        return None
    return key


def api_key_status() -> str:
    """APIキーの状態を KEY_* のいずれかで返す。"""
    if not API_KEY_ENV:
        return KEY_NOT_REQUIRED
    return KEY_OK if get_api_key() else KEY_MISSING
