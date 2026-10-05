"""画面の入口。中身は tools/summarize.py にあります。"""

from core.ui import render_tool
from tools.summarize import SPEC

render_tool(SPEC)
