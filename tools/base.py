"""各機能を「データ」として定義するための型。

機能を1つ増やすとは、このファイルの ToolSpec を1つ作ることです。
画面の描き方やAPIの呼び方を書く必要はありません（core/ui.py が引き受けます）。
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

# 入力欄の種類
#   text        1行の文字入力
#   textarea    複数行の文字入力（長文を貼る欄）
#   select      ドロップダウンから1つ選ぶ（選択肢が多いとき）
#   choice      横並びのボタンから1つ選ぶ（選択肢が3〜5個のとき）
#   multiselect 複数選べる
#   slider      数値をつまみで選ぶ
#   checkbox    オン・オフ
#   image       画像を選ぶ（AIに見せる。対応しているAIでのみ有効）
FieldType = Literal[
    "text", "textarea", "select", "choice", "multiselect", "slider", "checkbox", "image"
]


@dataclass
class Field:
    """入力欄1つ分の定義。"""

    key: str                      # build_prompt で values[key] として受け取る名前
    label: str                    # 画面に出す見出し
    type: FieldType = "text"
    options: list[str] = field(default_factory=list)  # select / choice / multiselect 用
    default: Any = None
    placeholder: str = ""         # 空欄のときに薄く出る例文
    help: str = ""                # ラベル横の「?」に出る説明
    required: bool = False        # 空のまま送信されたら警告を出す
    height: int = 160             # textarea の高さ
    max_chars: int | None = None  # 入れられる文字数の上限（None なら無制限）
    min_value: int = 0            # slider 用
    max_value: int = 100
    step: int = 1
    max_files: int = 4            # image 用。選べる枚数の上限
    full_width: bool = True       # False にすると他の欄と横に並ぶ


@dataclass
class ToolSpec:
    """機能1つ分の定義。"""

    key: str                      # 内部的な識別子（履歴や保存ファイル名に使う）
    title: str                    # 画面タイトル
    icon: str                     # Material Symbols のアイコン名
    description: str              # タイトル下の一言説明
    system_instruction: str       # AIに与える役割（どんな書き手として振る舞うか）
    fields: list[Field]
    build_prompt: Callable[[dict[str, Any]], str]  # 入力値から「お願いの文章」を作る
    submit_label: str = "生成する"
    result_label: str = "生成結果"
    file_extension: str = "md"    # ダウンロードするときの拡張子
    temperature: float | None = None  # この機能だけ既定値を変えたいときに指定


# --- プロンプトを組み立てるときの小道具 ------------------------------------

def optional_line(label: str, value: Any) -> str:
    """値が入っているときだけ「ラベル: 値」の1行を返す。

    入力されなかった項目を「指定なし」としてAIに送ると、
    かえって気を取られて品質が落ちるため、行そのものを省きます。
    """
    if value is None:
        return ""

    text = "・".join(str(v) for v in value) if isinstance(value, list) else str(value)
    text = text.strip()
    return f"{label}: {text}\n" if text else ""


def joined(values: dict[str, Any], key: str) -> str:
    """複数選択の値を「A・B・C」の形にする。"""
    items = values.get(key) or []
    return "・".join(str(v) for v in items)
