SYMBOLS_QUERY = """
(function_declaration
  name: (identifier) @fn_name
  parameters: (parameter_list) @fn_params
  result: (_)? @fn_return) @function

(method_declaration
  name: (field_identifier) @method_name
  parameters: (parameter_list) @method_params
  result: (_)? @method_return) @method

(type_declaration
  (type_spec
    name: (type_identifier) @type_name)) @type_decl
"""

IMPORTS_QUERY = """
(import_spec
  path: (interpreted_string_literal) @import_path)
"""


def extract_fn_signature(source: bytes, name_node, params_node, return_node=None) -> str:
    name = source[name_node.start_byte:name_node.end_byte].decode()
    params = source[params_node.start_byte:params_node.end_byte].decode()
    ret = ""
    if return_node:
        ret = " " + source[return_node.start_byte:return_node.end_byte].decode()
    return f"func {name}{params}{ret}"
