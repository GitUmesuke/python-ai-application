"""ホーム画面。

ページのファイルは「上から下に実行されるだけの台本」として書きます。
関数で包まないのがStreamlitの作法です。
"""

import streamlit as st

from core import config, menu

st.title("✍️ AIライティングツール")
st.caption("ブログ・メール・要約・リライト・SNSを、ひとつの画面から。機能名を押すと移動します。")

st.subheader("できること")

# 並べる機能は core/menu.py にまとめてあります。
# 機能名は st.page_link でリンクにしてあるので、押すとそのページへ移動します
# （上部のメニューから選ぶのと同じ動きです）。
for item in menu.ITEMS:
    with st.container(border=True):
        st.page_link(
            item.page,
            label=f"**{item.spec.title}**",
            icon=item.spec.icon,
        )
        st.caption(item.spec.description)

st.subheader("今の状態")

status = config.api_key_status()

if status == config.KEY_NOT_REQUIRED:
    st.info(
        "**いまは「ダミー動作」です。** 使うAIがまだ決まっていないため、"
        "生成ボタンを押すとAIの代わりに確認用の文章が返ります。\n\n"
        "画面の操作・入力欄・結果の表示は本番と同じなので、"
        "この状態でひととおり触って確かめられます。"
    )
    st.caption(
        "使うAIを決めたら、`core/providers/` にそのAI用のファイルを1つ追加し、"
        "`core/config.py` の `PROVIDER` を書き換えれば本物の生成に切り替わります。"
    )
elif status == config.KEY_MISSING:
    st.error("**APIキーが設定されていないため、文章を生成できません。**")
    st.info(
        "1. `.env.example` を複製して `.env` という名前にする\n"
        f"2. `{config.API_KEY_ENV}=` の右側にキーを貼り付けて保存する\n"
        "3. このページを再読み込みする\n\n"
        "※ Windowsは拡張子が隠れています。`.env.txt` になっていないか確認してください。"
    )
else:
    st.success(f"APIキーは設定済みです。使用中のAI: `{config.PROVIDER}`")

with st.expander("使い方のコツ"):
    st.markdown(
        """
- **入力は具体的なほど結果が良くなります。** 「集中力の記事」より
  「在宅勤務で集中が切れる人向けに、タイマーを使った具体策を紹介する記事」。
- **一度で完成させようとしないこと。** ブログ記事なら、まず「構成案だけ作る」で
  骨組みを確認してから本文を書かせると、やり直しが減ります。
- **サイドバーの「創造性」**は、低いほど堅実で安定、高いほど発想が広がります。
  メールや要約は低め、SNSやアイデア出しは高めが向いています。
- 結果が気に入らないときは、同じ内容でもう一度押すと別の文章が返ります。
"""
    )
