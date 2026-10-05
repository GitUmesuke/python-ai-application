"""SNS投稿文。"""

from tools.base import Field, ToolSpec, optional_line

SYSTEM = """あなたは各SNSの作法を理解している書き手です。
媒体ごとの長さ・雰囲気・読まれ方の違いをふまえて投稿文を書きます。

守ること:
- 最初の1行で読み手の手を止める。空疎な煽りは使わない
- 事実として確認できないことを断定しない
- 誇大な表現（「必ず」「絶対」「誰でも簡単に」）を使わない
- 案ごとに `## 案1` のような見出しを付けて区切る
- 投稿文そのものだけを出力し、解説や前置きを付けない"""

# 媒体ごとの事情を、そのままAIへの指示にする
PLATFORMS = {
    "X（旧Twitter）": "1投稿140字以内。改行を使って読みやすく。ハッシュタグは2個までに絞る。",
    "Instagram": "最初の2行で引きを作る。本文は200〜400字。ハッシュタグは本文の最後にまとめて10個程度。",
    "Facebook": "やや長め（300〜500字）で、語りかける文体。ハッシュタグはほぼ使わない。",
    "LinkedIn": "ビジネス向け。300〜500字。実績・学び・示唆を中心に、落ち着いた文体で。",
    "Threads": "会話の口火を切る短文（150字程度）。問いかけで終えると反応が付きやすい。",
}


def build_prompt(v: dict) -> str:
    platform = v["platform"]
    rule = PLATFORMS.get(platform, "")
    count = v["count"]

    # 画像が選ばれていたら、それを踏まえて書くよう指示を足す。
    # 画像そのものは core/ui.py がAIへ直接渡すので、ここでは枚数しか見ない。
    photos = v.get("photos") or []
    photo_note = ""
    if photos:
        photo_note = (
            f"\n# 添付する画像について\n"
            f"この投稿には画像を{len(photos)}枚添付します。画像はこの指示より前に渡してあります。\n"
            "- 画像の内容を踏まえて書く\n"
            "- 見れば分かることを、そのまま言葉で説明し直さない\n"
            "- 画像に写っていないことを、写っているかのように書かない\n"
        )

    requests = "- 案ごとに切り口（入り方・訴え方）を変えること\n"
    if v.get("hashtags"):
        requests += "- 媒体の作法に合わせてハッシュタグを付ける\n"
    else:
        requests += "- ハッシュタグは付けない\n"
    if v.get("emoji"):
        requests += "- 絵文字を適度に使う\n"
    else:
        requests += "- 絵文字は使わない\n"

    return f"""次の内容で、{platform} 向けの投稿文を{count}案書いてください。

# 媒体の条件
{rule}

# 投稿の内容
伝えたいこと: {v['topic']}
{optional_line("雰囲気・トーン", v.get("tone"))}{optional_line("読んでほしい相手", v.get("audience"))}{optional_line("最後に促したい行動", v.get("cta"))}
# 書き方の指示
{requests}{photo_note}"""


SPEC = ToolSpec(
    key="social",
    title="SNS投稿文",
    icon=":material/campaign:",
    description="媒体ごとの長さと雰囲気に合わせて、投稿文を複数案つくります。",
    system_instruction=SYSTEM,
    submit_label="投稿文を生成する",
    result_label="投稿文の案",
    temperature=1.0,  # SNSは案の幅が欲しいので、少し高めにする
    fields=[
        Field(
            key="topic",
            max_chars=2000,
            label="伝えたいこと",
            type="textarea",
            height=120,
            required=True,
            placeholder="例）在宅勤務の集中力について書いたブログ記事を公開したので知らせたい",
        ),
        Field(
            key="photos",
            label="投稿に使う画像",
            type="image",
            help=(
                "AIが中身を見て、写真に合った文章を書きます（最大4枚）。"
                "SNSへの添付そのものは、投稿するときにご自身で行ってください。"
            ),
        ),
        Field(
            key="platform",
            label="投稿する媒体",
            type="choice",
            options=list(PLATFORMS.keys()),
            default="X（旧Twitter）",
        ),
        Field(
            key="count",
            label="案の数",
            type="slider",
            full_width=False,
            min_value=1,
            max_value=5,
            default=3,
        ),
        Field(
            key="tone",
            label="雰囲気・トーン",
            type="select",
            full_width=False,
            options=[
                "親しみやすく気軽に",
                "落ち着いて誠実に",
                "熱量を込めて",
                "淡々と事実中心に",
                "ユーモアを交えて",
            ],
        ),
        Field(
            key="audience",
            max_chars=200,
            label="読んでほしい相手",
            full_width=False,
            placeholder="例）在宅勤務に慣れない人",
        ),
        Field(
            key="cta",
            max_chars=200,
            label="最後に促したい行動",
            full_width=False,
            placeholder="例）プロフィールのリンクから記事を読んでほしい",
        ),
        Field(
            key="hashtags",
            label="ハッシュタグを付ける",
            type="checkbox",
            full_width=False,
            default=True,
        ),
        Field(
            key="emoji",
            label="絵文字を使う",
            type="checkbox",
            full_width=False,
        ),
    ],
    build_prompt=build_prompt,
)
