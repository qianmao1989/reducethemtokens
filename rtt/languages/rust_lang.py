SYMBOLS_QUERY = """
(function_item
  name: (identifier) @fn_name
  parameters: (parameters) @fn_params
  return_type: (_)? @fn_return) @function

(impl_item
  type: (type_identifier) @impl_type
  body: (declaration_list
    (function_item
      name: (identifier) @method_name
      parameters: (parameters) @method_params
      return_type: (_)? @method_return) @method)) @impl

(struct_item
  name: (type_identifier) @struct_name) @struct

(enum_item
  name: (type_identifier) @enum_name) @enum

(trait_item
  name: (type_identifier) @trait_name) @trait
"""

IMPORTS_QUERY = """
(use_declaration
  argument: (_) @use_path) @use
"""


def extract_fn_signature(source: bytes, name_node, params_node, return_node=None) -> str:
    name = source[name_node.start_byte:name_node.end_byte].decode()
    params = source[params_node.start_byte:params_node.end_byte].decode()
    ret = ""
    if return_node:
        ret = " -> " + source[return_node.start_byte:return_node.end_byte].decode()
    return f"fn {name}{params}{ret}"
