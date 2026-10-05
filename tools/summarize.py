"""文章要約。"""

from tools.base import Field, ToolSpec, optional_line

SYSTEM = """あなたは長い文章から要点を取り出すことに長けた編集者です。

守ること:
- 元の文章に書かれていないことを足さない
- 筆者の主張と、単なる例示・補足を区別する
- 数値・固有名詞・日付は、元の文章のまま正確に写す
- 元の文章の立場を勝手に評価したり、意見を加えたりしない
- 要約そのものだけを出力し、前置きや感想を付けない"""

# 指定された形式ごとに、具体的な指示へ言い換える
STYLES = {
    "3行でまとめる": "全体を3行（各行50字程度）にまとめてください。",
    "箇条書き": "要点を5〜7個の箇条書きにしてください。各項目は1文で簡潔に。",
    "要点と結論": "「要点」を箇条書きにし、その後に「結論」を2〜3文で示してください。",
    "Q&A形式": "この文章が答えている問いを3〜5個立て、それぞれに本文に基づいて答えてください。",
    "ひとつの段落": "改行を使わず、ひとつの段落（200〜300字）にまとめてください。",
    "見出し付き": "内容を3〜5個のテーマに分け、それぞれに見出しを付けてまとめてください。",
}


def build_prompt(v: dict) -> str:
    style = v["style"]
    instruction = STYLES.get(style, STYLES["3行でまとめる"])

    extra = ""
    if v.get("keep_numbers"):
        extra += "- 本文に出てくる数値・固有名詞は省略せず残す\n"
    if v.get("keep_terms"):
        extra += "- 専門用語はやさしい言葉に言い換える\n"

    return f"""次の文章を要約してください。

# 要約の形式
{instruction}
{optional_line("要約の用途", v.get("purpose"))}
# 書き方の指示
- 元の文章の順序にこだわらず、重要な順に並べ替えてよい
{extra}
# 要約する文章
```
{v['text']}
```
"""


SPEC = ToolSpec(
    key="summarize",
    title="文章要約",
    icon=":material/compress:",
    description="長い文章を、目的に合った形に短くします。",
    system_instruction=SYSTEM,
    submit_label="要約する",
    result_label="要約",
    temperature=0.3,  # 要約は創造性より正確さを優先する
    fields=[
        Field(
            key="text",
            max_chars=30000,
            label="要約したい文章",
            type="textarea",
            height=300,
            required=True,
            placeholder="記事・議事録・メール・論文などを貼り付けてください。",
            help="長すぎて失敗する場合は、半分くらいに分けて2回実行してください。",
        ),
        Field(
            key="style",
            label="要約の形式",
            type="select",
            options=list(STYLES.keys()),
            default="3行でまとめる",
        ),
        Field(
            key="purpose",
            max_chars=200,
            label="何のために読むか",
            full_width=False,
            placeholder="例）会議に出られなかった人への共有用",
            help="用途を書くと、残す情報の選び方が変わります。",
        ),
        Field(
            key="keep_numbers",
            label="数値・固有名詞を残す",
            type="checkbox",
            full_width=False,
            default=True,
        ),
        Field(
            key="keep_terms",
            label="専門用語をやさしく言い換える",
            type="checkbox",
            full_width=False,
        ),
    ],
    build_prompt=build_prompt,
)
