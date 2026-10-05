"""メール返信。"""

from tools.base import Field, ToolSpec, optional_line

SYSTEM = """あなたは日本語のビジネスメールに精通した書き手です。
相手との関係と用件に合った、簡潔で失礼のない返信文を書きます。

守ること:
- 用件を先に、理由や背景は後に置く
- 事実として確認できないことを約束しない
- 空疎な定型句を並べず、相手が次に何をすればよいかが分かる文にする
- 件名・宛名・署名が必要な場合は含め、本文だけで足りる場合は本文のみにする
- 返信文そのものだけを出力し、解説や前置きを付けない"""


def build_prompt(v: dict) -> str:
    return f"""次の受信メールに対する返信文を書いてください。

# 受信したメール
```
{v['received']}
```

# 返信の条件
返信の方向性: {v['direction']}
{optional_line("相手との関係", v.get("relationship"))}{optional_line("丁寧さ", v.get("politeness"))}{optional_line("長さ", v.get("length"))}{optional_line("差出人（自分）の名乗り", v.get("sender"))}{optional_line("必ず伝えたいこと", v.get("points"))}
# 書き方の指示
- 受信メールの内容に具体的に応答する（一般的な返事で済ませない）
- 日時・金額・固有名詞は、受信メールに書かれているものをそのまま使う
- 受信メールに書かれていない情報を勝手に作らない。
  必要なのに不明な箇所は [ ] で囲んで、あとで埋められるようにする
"""


SPEC = ToolSpec(
    key="email_reply",
    title="メール返信",
    icon=":material/reply:",
    description="受信したメールを貼り付け、返信の方向性を選ぶだけで返信文を作ります。",
    system_instruction=SYSTEM,
    submit_label="返信文を生成する",
    result_label="生成された返信文",
    file_extension="txt",
    temperature=0.4,  # メールは発想より堅実さを優先する
    fields=[
        Field(
            key="received",
            max_chars=10000,
            label="受信したメール",
            type="textarea",
            height=240,
            required=True,
            placeholder="受信したメールの本文をそのまま貼り付けてください。",
            help="宛名や署名が入っていても構いません。そのまま貼るのが一番精度が出ます。",
        ),
        Field(
            key="direction",
            label="返信の方向性",
            type="choice",
            options=["承諾する", "断る", "日程を調整する", "確認・質問する", "お礼を伝える", "謝罪する"],
            default="承諾する",
        ),
        Field(
            key="points",
            max_chars=2000,
            label="必ず伝えたいこと",
            type="textarea",
            height=100,
            placeholder="例）来週の水曜以降なら対応可能。見積りは別途メールで送る。",
            help="ここに書いた内容は必ず文面に含まれます。箇条書きで構いません。",
        ),
        Field(
            key="relationship",
            label="相手との関係",
            type="select",
            full_width=False,
            options=[
                "社外の取引先",
                "初めて連絡する相手",
                "顧客・お客様",
                "社内の上司",
                "社内の同僚",
            ],
        ),
        Field(
            key="politeness",
            label="丁寧さ",
            type="select",
            full_width=False,
            options=["標準的なビジネス敬語", "かなり丁寧・格式高め", "やわらかめ・親しみを込めて"],
        ),
        Field(
            key="length",
            label="長さ",
            type="select",
            full_width=False,
            options=["簡潔に（3〜5行）", "標準（5〜10行）", "丁寧に詳しく"],
            default="標準（5〜10行）",
        ),
        Field(
            key="sender",
            max_chars=100,
            label="自分の名乗り",
            full_width=False,
            placeholder="例）株式会社○○ 山田",
            help="署名に使われます。空欄なら [ ] で埋める形になります。",
        ),
    ],
    build_prompt=build_prompt,
)
