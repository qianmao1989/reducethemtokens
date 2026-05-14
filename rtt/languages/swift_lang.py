SYMBOLS_QUERY = ""  # Swift support is best-effort
IMPORTS_QUERY = ""


def extract_fn_signature(source: bytes, name_node, params_node, return_node=None) -> str:
    name = source[name_node.start_byte:name_node.end_byte].decode()
    return f"func {name}(...)"
