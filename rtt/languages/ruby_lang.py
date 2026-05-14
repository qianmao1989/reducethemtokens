SYMBOLS_QUERY = """
(method
  name: (identifier) @method_name
  parameters: (method_parameters)? @method_params) @method

(class
  name: (constant) @class_name) @class

(module
  name: (constant) @module_name) @module
"""

IMPORTS_QUERY = """
(call
  method: (identifier) @require_call
  arguments: (argument_list
    (string) @require_path)
  (#eq? @require_call "require"))
"""


def extract_fn_signature(source: bytes, name_node, params_node, return_node=None) -> str:
    name = source[name_node.start_byte:name_node.end_byte].decode()
    params = ""
    if params_node:
        params = source[params_node.start_byte:params_node.end_byte].decode()
    return f"def {name}{params}"
