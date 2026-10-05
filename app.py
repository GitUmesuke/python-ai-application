"""アプリの入口。

起動方法（プロジェクト直下で）:
    .venv\\Scripts\\streamlit.exe run app.py

このファイルの役割は「ページの一覧を登録すること」だけです。

【機能を1つ増やす手順】
1. tools/ に新しいファイルを作り、SPEC という名前で ToolSpec を定義する
   （tools/blog.py をコピーして中身を書き換えるのが早いです）
2. app_pages/ に同じ名前のファイルを作る（中身は3行。既存のものをコピーで可）
3. core/menu.py の ITEMS に1行足す
"""

import streamlit as st

from core.config import APP_ICON, APP_TITLE
from core.menu import ITEMS

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="centered",  # 文章を読む道具なので、横幅を広げすぎない
    initial_sidebar_state="expanded",
)

# ホームだけここで直接指定し、各機能は core/menu.py の一覧から組み立てます。
# アイコン名は Material Symbols から選びます（無い名前を書くとエラーになります）。
PAGES = [
    st.Page("app_pages/home.py", title="ホーム", icon=":material/home:", default=True),
]
PAGES += [
    st.Page(item.page, title=item.spec.title, icon=item.spec.icon) for item in ITEMS
]

# position="top" で、ページの切り替えを画面上部に横並びで出します。
# サイドバーは「AIの設定」専用になります。
st.navigation(PAGES, position="top").run()
