"""機械的に判定できるセキュリティ点検を行い、結果をJSONで出す。

判断が要る項目（プロンプトインジェクションの危険度など）はここでは扱わない。
「ファイルがあるか」「この文字列が含まれるか」のように、
誰が何度やっても同じ答えになるものだけを見る。

使い方:
    python scan.py [プロジェクトのパス]
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# 調べないフォルダ（自動生成物・大量の依存ファイル）
SKIP_DIRS = {".venv", "venv", "node_modules", "__pycache__", ".git", "dist", "build", ".next"}

# 中身を読むファイルの種類
SOURCE_EXT = {".py", ".js", ".mjs", ".ts", ".jsx", ".tsx", ".html",
              ".toml", ".json", ".md", ".txt", ".yml", ".yaml"}

# 本物のキーらしき文字列の形。誤検出を減らすため、各社の実際の接頭辞に絞る
KEY_PATTERNS = [
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI系のキー"),
    (r"AIza[A-Za-z0-9_\-]{30,}", "Google系のキー（従来の形式）"),
    (r"AQ\.[A-Za-z0-9_\-]{30,}", "Google AI Studio のキー（新しい形式）"),
    (r"gh[pousr]_[A-Za-z0-9]{30,}", "GitHubのトークン"),
    (r"xox[baprs]-[A-Za-z0-9-]{10,}", "Slackのトークン"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "秘密鍵の中身"),
    (r"AKIA[0-9A-Z]{16}", "AWSのアクセスキー"),
]

# 秘匿情報が入りがちなファイル名
SECRET_FILES = re.compile(
    r"(^|/)(\.env($|\..*)|[^/]*SK\.txt|[^/]*secret[^/]*|[^/]*credential[^/]*|\.dev\.vars|secrets\.toml)$",
    re.I,
)

findings = []


def add(level, category, title, detail="", action=""):
    """見つかったことを1件記録する。

    level: high（すぐ直す）/ medium（直したほうがよい）/ low（知っておく）/ ok（確認できた）
    """
    findings.append({
        "level": level,
        "category": category,
        "title": title,
        "detail": detail,
        "action": action,
    })


def run_git(root, *args):
    try:
        r = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


# 点検の道具そのものは対象外にする。
# 検出に使うパターン（0.0.0.0 など）を文字列として持っているため、
# 除外しないと自分自身を「問題あり」と報告してしまう。
SKIP_PATH_PARTS = (".claude/skills/",)


def source_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            p = Path(dirpath) / name
            try:
                rel = p.relative_to(root).as_posix()
            except ValueError:
                continue
            if any(part in rel for part in SKIP_PATH_PARTS):
                continue
            if p.suffix.lower() in SOURCE_EXT or name.startswith("."):
                try:
                    if p.is_file() and p.stat().st_size <= 2_000_000:
                        yield p
                except OSError:
                    pass


def read(p):
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


# ------------------------------------------------------------------

def check_secrets(root):
    """秘密情報の置き場所と、漏れていないか。"""
    gitignore = root / ".gitignore"
    ignore_text = read(gitignore) if gitignore.exists() else ""
    is_git = (root / ".git").exists()

    env_files = [p for p in root.glob(".env*") if p.name != ".env.example"]
    if env_files:
        names = ", ".join(p.name for p in env_files)
        if not gitignore.exists():
            add("high", "秘密情報", ".gitignore がない",
                names + " があるのに .gitignore がありません。",
                ".gitignore を作り、.env の行を加える。")
        elif not re.search(r"^\s*\.env\s*$", ignore_text, re.M):
            add("high", "秘密情報", ".env が .gitignore に入っていない",
                ".env が無視されない設定です。Gitに上げるとキーが公開されます。",
                ".gitignore に .env の1行を加える。")
        else:
            add("ok", "秘密情報", ".env は .gitignore で守られている")

    if is_git:
        tracked = run_git(root, "ls-files") or ""
        leaked = [f for f in tracked.splitlines()
                  if SECRET_FILES.search(f) and not f.endswith(".env.example")]
        if leaked:
            add("high", "秘密情報", "秘匿ファイルがGitの管理下にある",
                "追跡されているファイル: " + ", ".join(leaked),
                "git rm --cached <ファイル> で外し、.gitignore に加える。キーは作り直す。")

        hist = run_git(root, "log", "--all", "--pretty=format:", "--name-only") or ""
        past = sorted({f for f in hist.splitlines()
                       if f and SECRET_FILES.search(f) and not f.endswith(".env.example")})
        if past:
            add("high", "秘密情報", "過去に秘匿ファイルがコミットされている",
                "履歴に残っているファイル: " + ", ".join(past) +
                "。削除しても履歴からは消えず、公開リポジトリなら誰でも取り出せます。",
                "そのキーを無効化して作り直す。履歴の書き換えだけでは不十分。")
        elif tracked:
            add("ok", "秘密情報", "Git履歴に秘匿ファイルは見つからなかった")
    else:
        add("low", "秘密情報", "まだGit管理していない",
            ".gitignore は書いてあっても、Gitを使い始めるまで何も守っていません。",
            "git init した直後に git status で .env が出ないことを一度だけ確認する。")

    # 本物のキーらしき文字列が、本来置くべきでない場所に書かれていないか
    for p in source_files(root):
        rel = p.relative_to(root).as_posix()
        if rel == ".env" or (rel.startswith(".env.") and rel != ".env.example"):
            continue  # 本物を置く場所なので対象外
        text = read(p)
        for pattern, label in KEY_PATTERNS:
            if re.search(pattern, text):
                where = ".env.example（Gitに上がるファイル）" if rel.endswith(".example") else rel
                add("high", "秘密情報", "キーらしき文字列が " + where + " に書かれている",
                    label + " の形をした文字列が含まれています。",
                    "その値を .env に移し、コードからは環境変数として読む。値は作り直す。")
                break


def check_exposure(root):
    """外から触れる状態になっていないか。"""
    uses_streamlit = "streamlit" in read(root / "requirements.txt").lower()
    cfg = root / ".streamlit" / "config.toml"

    if cfg.exists():
        text = read(cfg)
        m = re.search(r"^\s*address\s*=\s*[\"']([^\"']+)", text, re.M)
        if not m:
            add("medium", "公開範囲", "Streamlit の待ち受け先が既定のまま",
                "既定では同じネットワークの他の端末からアクセスできます。",
                '.streamlit/config.toml の [server] に address = "localhost" を書く。')
        elif m.group(1) in ("0.0.0.0", "*"):
            add("high", "公開範囲", "Streamlit が全ネットワークに公開されている",
                'address = "' + m.group(1) + '" になっています。',
                '1人で使うなら address = "localhost" にする。')
        else:
            add("ok", "公開範囲", "Streamlit は " + m.group(1) + " からのみ受け付ける")
    elif uses_streamlit:
        add("medium", "公開範囲", "Streamlit の設定ファイルがない",
            "既定では同じネットワークの他の端末からアクセスできます。",
            '.streamlit/config.toml を作り、[server] に address = "localhost" を書く。')

    for p in source_files(root):
        if p.suffix not in (".py", ".js", ".mjs", ".ts"):
            continue
        if re.search(r"0\.0\.0\.0", read(p)):
            add("medium", "公開範囲",
                "全ネットワークで待ち受ける記述がある（" + p.relative_to(root).as_posix() + "）",
                "0.0.0.0 は「どこからの接続も受ける」という意味です。",
                "1人で使うなら localhost か 127.0.0.1 にする。")


def check_output(root):
    """画面やログに、出してはいけないものが出ていないか。"""
    for p in source_files(root):
        if p.suffix not in (".py", ".js", ".mjs", ".ts", ".jsx", ".tsx"):
            continue
        rel = p.relative_to(root).as_posix()
        text = read(p)

        if "unsafe_allow_html=True" in text or "dangerouslySetInnerHTML" in text:
            add("high", "画面に出る情報",
                "入力やAIの出力がHTMLとして描画されうる（" + rel + "）",
                "AIの出力や貼り付けた文章にHTMLが混ざっていると、そのまま実行されます。",
                "HTMLを使わず標準の表示部品にする。必要ならその箇所だけ内容を検査する。")

        if re.search(r"st\.exception\s*\(|traceback\.print_exc\s*\(", text):
            add("medium", "画面に出る情報",
                "内部のエラー情報を画面にそのまま出している（" + rel + "）",
                "ファイルパスや内部構造が利用者に見えます。",
                "「何が起きたか＋次にどうするか」に言い換え、詳細は折りたたみに入れる。")

        if re.search(r"(print|console\.log|st\.(write|text|code))\s*\([^)]*\b(api_key|API_KEY|token|secret)\b",
                     text, re.I):
            add("high", "画面に出る情報", "キーを表示している箇所がある（" + rel + "）",
                "ログや画面にキーが出ると、画面共有や録画で漏れます。",
                "表示するなら設定済みかどうかだけにする。値そのものは出さない。")


def check_uploads(root):
    """受け取るファイルに歯止めがあるか。"""
    for p in source_files(root):
        if p.suffix != ".py":
            continue
        rel = p.relative_to(root).as_posix()
        text = read(p)
        for m in re.finditer(r"st\.file_uploader\s*\(", text):
            chunk = text[m.start():m.start() + 500]
            if "type=" not in chunk:
                add("medium", "入力の扱い",
                    "受け取るファイルの種類を制限していない（" + rel + "）",
                    "どんな形式でも受け取れる状態です。",
                    'type=["png", "jpg"] のように、想定する形式だけに絞る。')


def check_dependencies(root):
    """依存パッケージの固定状況。脆弱性の有無は別途オンラインで確認する。"""
    req = root / "requirements.txt"
    if req.exists():
        lines = [l.strip() for l in read(req).splitlines()
                 if l.strip() and not l.strip().startswith("#")]
        loose = [l for l in lines if "==" not in l]
        if loose:
            add("low", "依存パッケージ", "バージョンが固定されていない",
                "固定されていない指定: " + ", ".join(loose) +
                "。別のPCや将来の再構築で、違うバージョンが入る可能性があります。",
                "動作が安定したら pip freeze の結果で固定することを検討する。")
        add("ok", "依存パッケージ", "requirements.txt に " + str(len(lines)) + " 件")

    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(read(pkg))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            add("ok", "依存パッケージ", "package.json に " + str(len(deps)) + " 件")
        except Exception:
            pass


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    for fn in (check_secrets, check_exposure, check_output, check_uploads, check_dependencies):
        try:
            fn(root)
        except Exception as exc:
            add("low", "点検スクリプト", fn.__name__ + " が途中で止まった", str(exc),
                "この項目は手で確認してください。")

    print(json.dumps({"project": str(root), "findings": findings},
                     ensure_ascii=False, indent=2))


main()
