SYMBOLS_QUERY = """
(class_declaration
  name: (identifier) @class_name) @class

(method_declaration
  type: (_) @return_type
  name: (identifier) @method_name
  parameters: (formal_parameters) @method_params) @method

(interface_declaration
  name: (identifier) @interface_name) @interface
"""

IMPORTS_QUERY = """
(import_declaration
  (scoped_identifier) @import_path)
"""


def extract_fn_signature(source: bytes, name_node, params_node, return_node=None) -> str:
    name = source[name_node.start_byte:name_node.end_byte].decode()
    params = source[params_node.start_byte:params_node.end_byte].decode()
    ret = source[return_node.start_byte:return_node.end_byte].decode() if return_node else "void"
    return f"{ret} {name}{params}"
