"""AIごとの接続ファイルを置く場所。

ここに1ファイル作り、core/config.py の PROVIDER にファイル名を書くと、
そのAIが使われます。各ファイルが用意すべきものは1つだけです:

    def generate_stream(prompt, *, model, system_instruction, temperature) -> Iterator[str]

失敗したときは core.llm.LLMError を投げます（利用者向けの日本語を添えて）。
"""
