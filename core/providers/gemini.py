"""Gemini API との接続。

core/llm.py から呼ばれる。用意しているのは generate_stream() ひとつだけ。

【エラーの言い換えについて】
Gemini に固有のエラー（キーの誤り、混雑、モデルの提供終了など）を、
利用者向けの日本語に直すのはこのファイルの仕事。
新しいエラーに出くわしたら、下の _translate に1項目足せば画面の文言が変わる。
"""

import logging
from collections.abc import Iterator
from functools import lru_cache

from google import genai
from google.genai import types

from core import config
from core.llm import Image, LLMError

# SDKが毎回出す助言メッセージ（この用途では無関係）を黙らせる
logging.getLogger("google_genai").setLevel(logging.ERROR)
logging.getLogger("google_genai.models").setLevel(logging.ERROR)


@lru_cache(maxsize=4)
def _client_for(api_key: str) -> genai.Client:
    """接続の入口は作り直さない（画面が再描画されるたびに作ると無駄なため）。"""
    return genai.Client(api_key=api_key)


def _client() -> genai.Client:
    api_key = config.get_api_key()
    if api_key is None:
        raise LLMError(
            "APIキーが設定されていないため、AIに接続できません。",
            hint=(
                "1. https://aistudio.google.com/apikey でキーを取得する\n"
                "2. `.env.example` を複製して `.env` という名前にする\n"
                "3. `GEMINI_API_KEY=` の右側にキーを貼り付けて保存する\n"
                "4. このページを再読み込みする\n\n"
                "※ Windowsは拡張子が隠れています。`.env.txt` になっていないか確認してください。"
            ),
            kind=LLMError.KIND_CONFIG,
        )
    return _client_for(api_key)


def generate_stream(
    prompt: str,
    *,
    model: str,
    system_instruction: str = "",
    temperature: float = 0.8,
    images: list[Image] | None = None,
) -> Iterator[str]:
    """文章を生成し、届いた端から少しずつ返す。

    images があれば、その画像を見たうえで書きます。
    """
    cfg = types.GenerateContentConfig(temperature=temperature)
    if system_instruction:
        cfg.system_instruction = system_instruction

    # 画像を先に、文章を後に並べます（どの画像についての指示かが伝わりやすいため）
    contents: list = [
        types.Part.from_bytes(data=img.data, mime_type=img.mime_type)
        for img in (images or [])
    ]
    contents.append(prompt)

    try:
        for chunk in _client().models.generate_content_stream(
            model=model, contents=contents, config=cfg
        ):
            if chunk.text:
                yield chunk.text
    except LLMError:
        raise
    except Exception as exc:
        raise _translate(exc, model) from exc


def list_model_names() -> list[str]:
    """アカウントで使えることになっているモデル名を返す。

    注意: ここに並ぶモデルが必ず使えるとは限らない。
    提供が終了したモデルも一覧には残るため、確認には check.py で実際に生成を試す。
    """
    try:
        names = []
        for m in _client().models.list():
            actions = list(getattr(m, "supported_actions", None) or [])
            name = (m.name or "").removeprefix("models/")
            if name and (not actions or "generateContent" in actions):
                names.append(name)
        return sorted(set(names))
    except LLMError:
        raise
    except Exception as exc:
        raise _translate(exc, "") from exc


# --- エラーの言い換え ------------------------------------------------------

def _translate(exc: Exception, model: str) -> LLMError:
    text = str(exc)
    upper = text.upper()
    name = f"「{model}」" if model else "選択中のモデル"
    detail = f"{type(exc).__name__}: {text}"

    def has(*needles: str) -> bool:
        return any(n.upper() in upper for n in needles)

    # --- 通信できていない ---
    if has("getaddrinfo", "Name or service not known", "Temporary failure in name resolution"):
        return LLMError(
            "インターネットに接続できていないようです。",
            hint="ネットワーク接続を確認してから、もう一度お試しください。",
            detail=detail,
            kind=LLMError.KIND_TRANSIENT,
        )
    if has("SSL", "CERTIFICATE"):
        return LLMError(
            "通信の暗号化の検証に失敗しました。",
            hint=(
                "社内ネットワークやセキュリティソフトが通信を中継している場合に起こります。\n"
                "別のネットワーク（スマートフォンのテザリングなど）で試すと切り分けられます。"
            ),
            detail=detail,
            kind=LLMError.KIND_CONFIG,
        )
    if has("timeout", "timed out", "DEADLINE_EXCEEDED"):
        return LLMError(
            "AIからの応答が時間内に返ってきませんでした。",
            hint=(
                "入力した文章が長いときに起こりやすくなります。\n"
                "・もう一度試す\n"
                "・入力を短く分けて試す\n"
                "・サイドバーで Lite 系の軽いモデルに切り替える"
            ),
            detail=detail,
            kind=LLMError.KIND_TRANSIENT,
        )
    if has("ConnectionError", "Connection aborted", "Connection reset"):
        return LLMError(
            "通信が途中で切れました。",
            hint="一時的なものの可能性が高いです。もう一度お試しください。",
            detail=detail,
            kind=LLMError.KIND_TRANSIENT,
        )

    # --- APIキーの問題 ---
    if has("API_KEY", "API key not valid", "PERMISSION_DENIED", "UNAUTHENTICATED", "401", "403"):
        return LLMError(
            "APIキーが受け付けられませんでした。",
            hint=(
                "・`.env` の `GEMINI_API_KEY` に、余分な空白や引用符が入っていないか確認する\n"
                "・https://aistudio.google.com/apikey でキーが有効か確認する\n"
                "・キーを作り直した場合は `.env` を更新してページを再読み込みする"
            ),
            detail=detail,
            kind=LLMError.KIND_CONFIG,
        )

    # --- 利用量・モデルの問題 ---
    if has("RESOURCE_EXHAUSTED", "quota", "429"):
        return LLMError(
            f"{name}の利用量の上限に達しました。",
            hint=(
                "・しばらく時間をおいて試す（無料枠の上限は時間で回復します）\n"
                "・サイドバーで別のモデルに切り替える\n\n"
                "※ Pro 系のモデルは無料枠では使えません。有料プランが必要です。"
            ),
            detail=detail,
            kind=LLMError.KIND_QUOTA,
        )
    if has("UNAVAILABLE", "overloaded", "503"):
        return LLMError(
            f"{name}が今混み合っています。",
            hint=(
                "一時的なものです。\n"
                "・少し待ってもう一度試す\n"
                "・サイドバーで別のモデルに切り替える"
            ),
            detail=detail,
            kind=LLMError.KIND_TRANSIENT,
        )
    if has("NOT_FOUND", "404", "no longer available", "is not supported"):
        return LLMError(
            f"{name}は現在利用できません。提供が終了した可能性があります。",
            hint=(
                "・サイドバーで別のモデルを選ぶ\n"
                "・`.venv\\Scripts\\python.exe check.py` を実行すると、今どれが使えるか確認できます\n"
                "・結果に合わせて `core/config.py` の `MODELS` を更新してください"
            ),
            detail=detail,
            kind=LLMError.KIND_CONFIG,
        )

    # --- 入力内容の問題 ---
    if has("exceeds the maximum", "too long", "token count", "INVALID_ARGUMENT", "400"):
        return LLMError(
            "入力した内容をAIが受け取れませんでした。文章が長すぎる可能性があります。",
            hint=(
                "・入力を半分くらいに分けて、何回かに分けて実行する\n"
                "・不要な部分を削ってから試す"
            ),
            detail=detail,
            kind=LLMError.KIND_INPUT,
        )
    if has("SAFETY", "blocked", "PROHIBITED_CONTENT", "RECITATION"):
        return LLMError(
            "AIの安全フィルタにより、この内容への回答が止められました。",
            hint=(
                "入力に、センシティブと判断される表現が含まれている可能性があります。\n"
                "表現を変えて試すと通ることがあります。"
            ),
            detail=detail,
            kind=LLMError.KIND_INPUT,
        )

    # --- 相手側の不具合 ---
    if has("INTERNAL", "500", "502", "504"):
        return LLMError(
            "AI側で一時的な不具合が起きています。",
            hint="こちらの設定の問題ではありません。少し待ってからもう一度お試しください。",
            detail=detail,
            kind=LLMError.KIND_TRANSIENT,
        )

    return LLMError(
        "予期しない問題が起きて、生成できませんでした。",
        hint=(
            "・もう一度試す\n"
            "・サイドバーで別のモデルに切り替える\n"
            "・`.venv\\Scripts\\python.exe check.py` を実行して、設定に問題がないか確認する"
        ),
        detail=detail,
        kind=LLMError.KIND_UNKNOWN,
    )
