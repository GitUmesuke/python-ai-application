"""ダミーのAI（使うAIが決まるまでの仮実装）。

本物のAIの代わりに、AIへ渡される指示文をそのまま少しずつ返します。
APIキーが無くても、入力 → 生成 → 逐次表示 → コピー・保存・履歴 までを
実際に動かして確かめられるようにするためのものです。

おまけに「AIにどんな文章が送られるのか」が目で見えるので、
プロンプトを書く練習にもなります。

使うAIを決めたら、このファイルは削除してかまいません。
"""

import time
from collections.abc import Iterator

from core import config
from core.llm import Image, LLMError

NOTICE = (
    "> ⚠️ **これはダミーの出力です。** 本物のAIはまだつながっていません。\n"
    "> 下に出ているのは、AIへ送られる予定の指示文そのものです。\n\n"
    "---\n\n"
)


def _chunks(text: str, size: int = 40) -> Iterator[str]:
    """文章を少しずつに切り分ける（本物のAIの返り方をまねるため）。"""
    for i in range(0, len(text), size):
        yield text[i : i + size]


def generate_stream(
    prompt: str,
    *,
    model: str,
    system_instruction: str = "",
    temperature: float = 0.8,
    images: list[Image] | None = None,
) -> Iterator[str]:
    # .env に STUB_FORCE_ERROR=1 を書くと、わざと失敗します。
    # エラー画面の出かたを確認したいときに使ってください。
    if config.flag_enabled("STUB_FORCE_ERROR"):
        raise LLMError(
            "動作確認のため、わざと失敗させました。実際の不具合ではありません。",
            hint=(
                "元に戻すには、`.env` の `STUB_FORCE_ERROR` の行を消す"
                "（または `0` にする）→ このページを再読み込み。"
            ),
            detail="StubForcedError: STUB_FORCE_ERROR=1 が .env に設定されています",
            kind=LLMError.KIND_CONFIG,
        )

    # 画像が渡っているかどうかも、確認できるように出しておく
    attached = images or []
    photo_line = (
        "**AIに見せる画像**: "
        + "、".join(i.name or "(名前なし)" for i in attached)
        + "\n\n"
        if attached
        else ""
    )

    body = (
        f"**選んだモデル**: {model}　／　**創造性**: {temperature}\n\n"
        f"{photo_line}"
        "## AIに渡す「役割」の指示\n\n"
        f"{system_instruction.strip() or '（指定なし）'}\n\n"
        "## AIに渡す「お願い」の文章\n\n"
        f"{prompt.strip()}\n"
    )

    for chunk in _chunks(NOTICE + body):
        time.sleep(0.01)  # 少しずつ届く様子を再現する
        yield chunk
