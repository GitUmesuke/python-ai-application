"""画面に並べる機能の一覧。

機能を増やすときに編集するのは、このファイルの ITEMS だけです。
ここに1行足すと、上部のメニューとホーム画面のリンクの両方に反映されます。

タイトル・アイコン・説明文は tools/ の ToolSpec から取ります。
同じ内容を2か所に書かないので、片方だけ古くなることがありません。
"""

from dataclasses import dataclass

from tools import blog, email_reply, rewrite, social, summarize
from tools.base import ToolSpec


@dataclass
class MenuItem:
    """メニュー1つ分。"""

    page: str       # app_pages/ の中のファイル（app.py から見た相対パス）
    spec: ToolSpec  # 機能の定義


ITEMS: list[MenuItem] = [
    MenuItem("app_pages/blog.py", blog.SPEC),
    MenuItem("app_pages/email_reply.py", email_reply.SPEC),
    MenuItem("app_pages/summarize.py", summarize.SPEC),
    MenuItem("app_pages/rewrite.py", rewrite.SPEC),
    MenuItem("app_pages/social.py", social.SPEC),
]
