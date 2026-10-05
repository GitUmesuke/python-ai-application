"""AI呼び出しの窓口。

各機能（tools/）と画面（core/ui.py）は、このファイルの generate_stream() だけを
呼びます。どのAIを使っているか、APIをどう叩くかは知りません。

そのおかげで、使うAIを変えるときに直すのは
    ・core/providers/ にファイルを1つ追加
    ・core/config.py の PROVIDER を書き換え
の2か所だけで済みます。
"""

import importlib
import time
from collections.abc import Iterator
from dataclasses import dataclass

from core import config

# 一時的な失敗（混雑・通信断）のときに、黙って試し直す回数と待ち時間。
# 増やしても混雑は解消しないので、1回にとどめています。
RETRY_LIMIT = 1
RETRY_WAIT_SECONDS = 2.0


@dataclass(frozen=True)
class Image:
    """AIに見せる画像1枚。

    プロンプト（文字）には混ぜず、generate_stream の images 引数で渡します。
    文字と画像は性質が違うので、同じ経路に押し込まないための型です。
    """

    data: bytes
    mime_type: str
    name: str = ""


class LLMError(RuntimeError):
    """利用者に見せるエラー。

    message … 何が起きたか（日本語で1〜2文）
    hint    … 次にどうすればよいか（日本語・箇条書き可）
    detail  … 元のエラー文。英語やエラーコードはここに閉じ込め、
              画面では折りたたみの中にだけ出す
    kind    … 原因の種別（下の KIND_* ）。一時的な障害を
              「設定ミス」と誤って案内しないために分けている
    """

    KIND_TRANSIENT = "transient"  # 待てば直る（混雑・通信断・相手側の不具合）
    KIND_QUOTA = "quota"          # 料金プラン・利用量の制約。設定ミスではない
    KIND_CONFIG = "config"        # 設定を直さないと直らない（キー誤り等）
    KIND_INPUT = "input"          # 入力内容に起因する（長すぎ・安全フィルタ）
    KIND_UNKNOWN = "unknown"      # 原因不明

    def __init__(
        self,
        message: str,
        *,
        hint: str = "",
        detail: str = "",
        kind: str = KIND_UNKNOWN,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.detail = detail
        self.kind = kind

    @property
    def is_retryable(self) -> bool:
        """もう一度試す価値があるか。"""
        return self.kind == self.KIND_TRANSIENT


def _provider():
    """core/config.py の PROVIDER に書かれたAI接続ファイルを読み込む。"""
    name = config.PROVIDER
    module_path = f"core.providers.{name}"

    try:
        return importlib.import_module(module_path)
    except ModuleNotFoundError as exc:
        detail = f"{type(exc).__name__}: {exc}"

        # 接続ファイル自体が無い場合と、その中で import している
        # ライブラリが無い場合を、区別して案内する
        if exc.name == module_path:
            raise LLMError(
                f"「{name}」用のAI接続ファイルが見つかりません。",
                hint=(
                    f"・`core/providers/{name}.py` があるか確認する\n"
                    "・`core/config.py` の `PROVIDER` のつづりを確認する"
                ),
                detail=detail,
                kind=LLMError.KIND_CONFIG,
            ) from exc

        raise LLMError(
            f"AIを使うためのライブラリ（{exc.name}）が入っていません。",
            hint=(
                "ターミナルで次を実行してください:\n"
                "`.venv\\Scripts\\python.exe -m pip install -r requirements.txt`"
            ),
            detail=detail,
            kind=LLMError.KIND_CONFIG,
        ) from exc


def generate_stream(
    prompt: str,
    *,
    model: str,
    system_instruction: str = "",
    temperature: float = 0.8,
    images: list[Image] | None = None,
) -> Iterator[str]:
    """文章を生成し、少しずつ返す（画面にじわじわ表示するため）。

    images を渡すと、その画像を見たうえで文章を書きます
    （画像を読めないAIに渡した場合は、接続ファイル側で無視されます）。

    失敗したときは LLMError を投げます。
    """
    provider = _provider()

    # 混雑（503）などの一時的な失敗は、1回だけ黙って試し直します。
    # ただし**1文字でも画面に出したあとは再試行しません**。
    # やり直すと、途中まで表示された文章の続きに別の文章がつながってしまうためです。
    attempt = 0
    while True:
        attempt += 1
        delivered = False

        # LLMError はそのまま通し、それ以外の想定外の例外だけ言い換える。
        # 各AIに固有のエラー（キー誤り・混雑など）の言い換えは、
        # そのAIの事情を知っている core/providers/ の側で行います。
        try:
            for chunk in provider.generate_stream(
                prompt,
                model=model,
                system_instruction=system_instruction,
                temperature=temperature,
                images=images or [],
            ):
                delivered = True
                yield chunk
            return
        except LLMError as exc:
            if exc.is_retryable and not delivered and attempt <= RETRY_LIMIT:
                time.sleep(RETRY_WAIT_SECONDS)
                continue
            raise
        except Exception as exc:
            raise LLMError(
                "予期しない問題が起きて、文章を生成できませんでした。",
                hint=(
                    "・もう一度試す\n"
                    "・サイドバーで別のモデルに切り替える\n"
                    "・`.venv\\Scripts\\python.exe check.py` を実行して、設定を確認する\n\n"
                    "繰り返し起きる場合は、下の「技術的な詳細」が原因究明の手がかりになります。"
                ),
                detail=f"{type(exc).__name__}: {exc}",
                kind=LLMError.KIND_UNKNOWN,
            ) from exc
