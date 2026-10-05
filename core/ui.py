"""画面を描く共通部品。

ToolSpec を渡すと「入力フォーム → 生成 → 結果表示」までを一通り行います。
見た目や共通の挙動を変えたいときは、このファイルを直せば全機能に反映されます。
"""

from typing import Any

import streamlit as st

from core import config, llm
from core.llm import Image
from tools.base import Field, ToolSpec


# ------------------------------------------------------------------
# サイドバー（AIの設定）
# ------------------------------------------------------------------

def sidebar_settings() -> dict[str, Any]:
    """モデルと創造性を選ぶ欄を描き、選ばれた値を返す。"""
    with st.sidebar:
        st.markdown("### :material/tune: AIの設定")

        model_keys = list(config.MODELS.keys())
        default_index = (
            model_keys.index(config.DEFAULT_MODEL)
            if config.DEFAULT_MODEL in model_keys
            else 0
        )
        model = st.selectbox(
            "モデル",
            model_keys,
            index=default_index,
            key="shared_model",
            help="迷ったら既定のままで問題ありません。",
        )
        st.caption(config.MODELS.get(model, ""))

        temperature = st.slider(
            "創造性",
            min_value=0.0,
            max_value=1.5,
            value=config.DEFAULT_TEMPERATURE,
            step=0.1,
            key="shared_temperature",
            help="低いほど堅実で安定、高いほど発想が広がります。",
        )

        st.divider()

        status = config.api_key_status()
        if status == config.KEY_NOT_REQUIRED:
            st.info("ダミー動作中（APIキー不要）")
        elif status == config.KEY_MISSING:
            st.error("APIキー未設定")
        else:
            st.success("APIキー設定済み")

    return {"model": model, "temperature": temperature}


# ------------------------------------------------------------------
# エラー表示
# ------------------------------------------------------------------

def show_error(exc: llm.LLMError) -> None:
    """「何が起きたか」と「次にどうするか」の2点に分けて見せる。

    エラーコードや英語のメッセージは折りたたみの中にだけ置きます。
    必要な人だけが開ければよく、主要部に出すと不安をあおるだけなので。
    """
    st.error(f"**{exc.message}**")

    if exc.is_retryable:
        st.caption("一時的な問題と思われます。もう一度試す価値があります。")

    if exc.hint:
        st.info(exc.hint)

    if exc.detail:
        with st.expander("技術的な詳細（開発者向け）"):
            st.code(exc.detail, language="text", wrap_lines=True)


# ------------------------------------------------------------------
# 入力フォーム
# ------------------------------------------------------------------

def _render_field(f: Field) -> Any:
    """Field の定義どおりに入力欄を1つ描く。"""
    label = f"{f.label} *" if f.required else f.label
    key = f"input_{f.key}"
    help_text = f.help or None

    if f.type == "textarea":
        return st.text_area(
            label,
            value=f.default or "",
            placeholder=f.placeholder,
            help=help_text,
            height=f.height,
            max_chars=f.max_chars,
            key=key,
        )

    if f.type == "select":
        index = f.options.index(f.default) if f.default in f.options else 0
        return st.selectbox(label, f.options, index=index, help=help_text, key=key)

    if f.type == "choice":
        return st.segmented_control(
            label,
            f.options,
            default=f.default if f.default in f.options else f.options[0],
            required=True,
            help=help_text,
            key=key,
        )

    if f.type == "multiselect":
        return st.multiselect(
            label, f.options, default=f.default or [], help=help_text, key=key
        )

    if f.type == "slider":
        return st.slider(
            label,
            min_value=f.min_value,
            max_value=f.max_value,
            value=f.default if f.default is not None else f.min_value,
            step=f.step,
            help=help_text,
            key=key,
        )

    if f.type == "checkbox":
        return st.checkbox(label, value=bool(f.default), help=help_text, key=key)

    if f.type == "image":
        uploaded = st.file_uploader(
            label,
            type=["png", "jpg", "jpeg", "webp", "gif"],
            accept_multiple_files=True,
            help=help_text,
            key=key,
        )
        # 画面に出た順にそのまま使う。上限を超えた分は切り捨てる
        return [
            Image(data=u.getvalue(), mime_type=u.type or "image/png", name=u.name)
            for u in (uploaded or [])[: f.max_files]
        ]

    return st.text_input(
        label,
        value=f.default or "",
        placeholder=f.placeholder,
        help=help_text,
        max_chars=f.max_chars,
        key=key,
    )


def _render_form(spec: ToolSpec) -> tuple[dict[str, Any], bool]:
    """入力フォームを描き、入力値と「送信されたか」を返す。

    st.form で囲むと、入力中は画面が作り直されず、
    ボタンを押したときにまとめて処理されます。
    """
    values: dict[str, Any] = {}

    with st.form(key=f"form_{spec.key}"):
        wide = [f for f in spec.fields if f.full_width]
        narrow = [f for f in spec.fields if not f.full_width]

        for f in wide:
            values[f.key] = _render_field(f)

        # 短い項目は2列に並べて、縦に長くなりすぎないようにする
        if narrow:
            columns = st.columns(2)
            for i, f in enumerate(narrow):
                with columns[i % 2]:
                    values[f.key] = _render_field(f)

        submitted = st.form_submit_button(
            spec.submit_label, type="primary", width="stretch"
        )

    return values, submitted


def _collect_images(spec: ToolSpec, values: dict[str, Any]) -> list[Image]:
    """入力値のうち、画像の欄だけを取り出してまとめる。

    画像はプロンプト（文字）には混ぜず、AI呼び出しへ別の経路で渡します。
    """
    images: list[Image] = []
    for f in spec.fields:
        if f.type == "image":
            images.extend(values.get(f.key) or [])
    return images


def _missing_required(spec: ToolSpec, values: dict[str, Any]) -> list[str]:
    """必須なのに空のままの項目名を返す。"""
    missing = []
    for f in spec.fields:
        if not f.required:
            continue
        value = values.get(f.key)
        if value is None or (isinstance(value, (str, list)) and not str(value).strip()):
            missing.append(f.label)
    return missing


# ------------------------------------------------------------------
# 生成と結果表示
# ------------------------------------------------------------------

def _generate(
    spec: ToolSpec,
    prompt: str,
    settings: dict[str, Any],
    images: list[Image] | None = None,
) -> tuple[str, llm.LLMError | None]:
    """AIを呼び、届いた文章を画面に流しながら全文を返す。

    途中で失敗しても、そこまでに届いた分は画面に残したいので、
    例外は生成の内側で受け止めて error に入れて返します。
    """
    error: list[llm.LLMError] = []
    temperature = (
        spec.temperature if spec.temperature is not None else settings["temperature"]
    )

    def stream():
        try:
            yield from llm.generate_stream(
                prompt,
                model=settings["model"],
                system_instruction=spec.system_instruction,
                temperature=temperature,
                images=images,
            )
        except llm.LLMError as exc:
            error.append(exc)

    with st.spinner("生成中..."):
        written = st.write_stream(stream, cursor="▌")

    # 文字だけを流しているので通常は文字列が返るが、念のため結合しておく
    text = written if isinstance(written, str) else "".join(str(w) for w in written)
    return text, error[0] if error else None


def _render_result_actions(spec: ToolSpec, text: str, prompt: str) -> None:
    """コピー・保存・送った指示の確認。"""
    st.divider()

    with st.expander(":material/content_copy: コピー用（右上のアイコンで全文コピー）"):
        st.code(text, language="markdown", wrap_lines=True)

    st.download_button(
        ":material/download: ファイルに保存",
        data=text,
        file_name=f"{spec.key}.{spec.file_extension}",
        mime="text/markdown",
        key=f"download_{spec.key}",
    )

    with st.expander(":material/search: AIに送った指示を見る"):
        st.text(prompt)


def _history(spec_key: str) -> list[dict[str, str]]:
    """この機能の生成履歴。ブラウザを閉じると消えます。"""
    store = st.session_state.setdefault("history", {})
    return store.setdefault(spec_key, [])


def _render_history(spec: ToolSpec) -> None:
    """同じページ内での過去の結果を下に並べる。"""
    history = _history(spec.key)
    if len(history) <= 1:
        return

    st.divider()
    st.subheader("これまでの生成")
    st.caption("ブラウザを閉じると消えます。残したいものはファイルに保存してください。")

    for i, item in enumerate(history[1:], start=2):
        preview = item["result"][:40].strip().replace("\n", " ")
        with st.expander(f"{i}回前: {preview}..."):
            st.markdown(item["result"])


# ------------------------------------------------------------------
# ここが入口。各ページはこの関数を呼ぶだけ
# ------------------------------------------------------------------

def render_tool(spec: ToolSpec) -> None:
    """ToolSpec 1つ分の画面をまるごと描く。"""
    settings = sidebar_settings()

    st.title(f"{spec.icon} {spec.title}")
    st.caption(spec.description)

    values, submitted = _render_form(spec)

    if submitted:
        missing = _missing_required(spec, values)
        if missing:
            st.warning(f"次の項目を入力してください: {'、'.join(missing)}")
        else:
            prompt = spec.build_prompt(values)

            st.subheader(spec.result_label)
            images = _collect_images(spec, values)
            text, error = _generate(spec, prompt, settings, images)

            if error is not None:
                show_error(error)
            elif not text.strip():
                st.warning(
                    "**AIから空の回答が返ってきました。**\n\n"
                    "入力の表現を少し変えるか、サイドバーで別のモデルに"
                    "切り替えてお試しください。"
                )
            else:
                _history(spec.key).insert(0, {"prompt": prompt, "result": text})
                _render_result_actions(spec, text, prompt)

    _render_history(spec)
