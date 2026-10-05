"""ブログ記事執筆。

このファイルがやることは2つだけです。
  1. どんな入力欄を出すか（fields）
  2. その入力から、AIへのお願いの文章をどう組み立てるか（build_prompt）
"""

from tools.base import Field, ToolSpec, optional_line

# AIに与える「役割」。毎回の指示とは別に、常に効いている前提です。
SYSTEM = """あなたは日本語のWebライティングに長けた編集者兼ライターです。
読者が最後まで読み通せる、具体的で中身のある記事を書きます。

守ること:
- 一般論の繰り返しや、内容のない前置きを書かない
- 抽象論で終わらせず、具体例・手順・数値を入れる
- 事実が不確かな点は断定せず、その旨を示す
- 出力はMarkdown形式（見出しは ## から始める）
- 「承知しました」などの前置きや、記事以外のコメントを付けない"""


def build_prompt(v: dict) -> str:
    outline_only = v.get("outline_only")

    if outline_only:
        task = (
            "次の条件で、ブログ記事の構成案（見出しと、各セクションで書く要点）を"
            "作ってください。本文は書かないでください。"
        )
    else:
        task = "次の条件で、ブログ記事の本文を書いてください。"

    return f"""{task}

# 条件
テーマ: {v['theme']}
{optional_line("想定読者", v.get("audience"))}{optional_line("記事の目的", v.get("goal"))}{optional_line("文体・トーン", v.get("tone"))}{optional_line("目安の文字数", None if outline_only else f"{v['length']}字程度")}{optional_line("盛り込みたいキーワード", v.get("keywords"))}{optional_line("補足・参考情報", v.get("notes"))}
# 書き方の指示
- 冒頭で読者の関心を引き、この記事で何が得られるかを明確にする
- 見出しだけを追っても内容が分かるようにする
- 最後は、読者が次に取る行動につながるまとめで締める
"""


SPEC = ToolSpec(
    key="blog",
    title="ブログ記事",
    icon=":material/article:",
    description="テーマと読者を指定すると、記事の本文または構成案を作ります。",
    system_instruction=SYSTEM,
    submit_label="記事を生成する",
    result_label="生成された記事",
    fields=[
        Field(
            key="theme",
            max_chars=2000,
            label="テーマ・書きたいこと",
            type="textarea",
            height=100,
            required=True,
            placeholder="例）在宅勤務で集中力を保つための具体的な工夫",
            help="一言でなく、誰に何を伝えたいかまで書くと精度が上がります。",
        ),
        Field(
            key="notes",
            max_chars=2000,
            label="補足・盛り込みたい情報",
            type="textarea",
            height=100,
            placeholder=(
                "例）自分の体験として、25分タイマーが効果的だった。"
                "専門用語は避けたい。精神論には寄せないでほしい。"
            ),
            help="入れてほしいエピソードや、避けたい表現を自由に書いてください。",
        ),
        Field(
            key="audience",
            max_chars=200,
            label="想定読者",
            full_width=False,
            placeholder="例）在宅勤務を始めて半年の会社員",
        ),
        Field(
            key="keywords",
            max_chars=200,
            label="キーワード",
            full_width=False,
            placeholder="例）集中力, 在宅勤務, 時間管理",
        ),
        Field(
            key="goal",
            label="記事の目的",
            type="select",
            full_width=False,
            options=[
                "読者の悩みを解決する",
                "ノウハウを共有する",
                "自分の考えを伝える",
                "商品・サービスを紹介する",
                "出来事を報告する",
            ],
        ),
        Field(
            key="tone",
            label="文体・トーン",
            type="select",
            full_width=False,
            options=[
                "親しみやすい敬体（です・ます）",
                "落ち着いた常体（だ・である）",
                "ビジネス向けの丁寧な敬体",
                "カジュアルで口語的",
            ],
        ),
        Field(
            key="length",
            label="目安の文字数",
            type="slider",
            full_width=False,
            min_value=500,
            max_value=5000,
            step=500,
            default=2000,
        ),
        Field(
            key="outline_only",
            label="まず構成案だけを作る",
            type="checkbox",
            full_width=False,
            help="先に骨組みを確認してから本文を書かせると、やり直しが減ります。",
        ),
    ],
    build_prompt=build_prompt,
)
