"""リライト・校正。"""

from tools.base import Field, ToolSpec, optional_line

SYSTEM = """あなたは日本語の校正・編集に長けた編集者です。

守ること:
- 書き手の意図と主張を変えない
- 必要以上に書き換えない。直す理由のない部分はそのまま残す
- 元の文章にない情報・主張を足さない
- 書き換えた文章そのものだけを出力し、前置きを付けない"""

# 指定された作業ごとに、具体的な指示へ言い換える
MODES = {
    "誤字脱字・文法を直す": (
        "誤字脱字、送り仮名、句読点、文法の誤り、表記の揺れだけを直してください。"
        "文章のスタイルや言い回しは変えないでください。"
    ),
    "読みやすく整える": (
        "意味を変えずに読みやすくしてください。長い文を分け、"
        "重複する表現を削り、語順を整えてください。"
    ),
    "トーンを変える": "意味を保ったまま、指定されたトーンに書き換えてください。",
    "短くする": "意味を保ったまま、指定された分量まで削ってください。重要度の低い部分から削ります。",
    "詳しく膨らませる": (
        "元の主張を保ったまま、説明・具体例・理由を補って指定された分量まで膨らませてください。"
        "事実を創作しないこと。例が必要な箇所は一般的な例にとどめること。"
    ),
}


def build_prompt(v: dict) -> str:
    mode = v["mode"]
    instruction = MODES.get(mode, MODES["読みやすく整える"])

    conditions = ""
    if mode == "トーンを変える":
        conditions += optional_line("変更後のトーン", v.get("tone"))
    if mode in ("短くする", "詳しく膨らませる"):
        conditions += optional_line("目安の分量", f"{v['length']}字程度")

    report = ""
    if v.get("show_changes"):
        report = (
            "\n# 追加の出力\n"
            "書き換えた文章のあとに `---` で区切り、"
            "「主な変更点」として、何をなぜ直したかを3〜5個の箇条書きで示してください。\n"
        )

    return f"""次の文章を書き換えてください。

# 作業の内容
{instruction}
{conditions}{optional_line("気をつけてほしいこと", v.get("notes"))}{report}
# 元の文章
```
{v['text']}
```
"""


SPEC = ToolSpec(
    key="rewrite",
    title="リライト・校正",
    icon=":material/spellcheck:",
    description="誤字の修正、読みやすさの改善、トーンの変換、長さの調整を行います。",
    system_instruction=SYSTEM,
    submit_label="書き換える",
    result_label="書き換えた文章",
    temperature=0.4,
    fields=[
        Field(
            key="text",
            max_chars=30000,
            label="元の文章",
            type="textarea",
            height=260,
            required=True,
            placeholder="直したい文章を貼り付けてください。",
        ),
        Field(
            key="mode",
            label="何をしますか",
            type="choice",
            options=list(MODES.keys()),
            default="読みやすく整える",
        ),
        Field(
            key="notes",
            max_chars=2000,
            label="気をつけてほしいこと",
            type="textarea",
            height=80,
            placeholder="例）「させていただく」を減らしたい。社名は正式名称のままにする。",
        ),
        Field(
            key="tone",
            label="変更後のトーン",
            type="select",
            full_width=False,
            options=[
                "丁寧なビジネス文書",
                "親しみやすい敬体（です・ます）",
                "落ち着いた常体（だ・である）",
                "カジュアルで口語的",
                "やわらかく丁寧に",
            ],
            help="「トーンを変える」を選んだときだけ使われます。",
        ),
        Field(
            key="length",
            label="目安の分量",
            type="slider",
            full_width=False,
            min_value=100,
            max_value=3000,
            step=100,
            default=600,
            help="「短くする」「詳しく膨らませる」を選んだときだけ使われます。",
        ),
        Field(
            key="show_changes",
            label="変更点の説明も付ける",
            type="checkbox",
            full_width=False,
            help="何をなぜ直したかが分かるので、自分で書き直すときの参考になります。",
        ),
    ],
    build_prompt=build_prompt,
)
