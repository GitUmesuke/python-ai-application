"""画面の入口。中身は tools/email_reply.py にあります。"""

from core.ui import render_tool
from tools.email_reply import SPEC

render_tool(SPEC)
