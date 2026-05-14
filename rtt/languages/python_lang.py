SYMBOLS_QUERY = """
(function_definition
  name: (identifier) @fn_name
  parameters: (parameters) @fn_params
  return_type: (type)? @fn_return) @function

(class_definition
  name: (identifier) @class_name
  body: (block
    (function_definition
      name: (identifier) @method_name
      parameters: (parameters) @method_params
      return_type: (type)? @method_return) @method)) @class
"""

IMPORTS_QUERY = """
(import_statement
  name: [(dotted_name) (aliased_import)] @import)
(import_from_statement
  module_name: (dotted_name)? @from_module)
"""


def extract_fn_signature(source: bytes, name_node, params_node, return_node=None) -> str:
    name = source[name_node.start_byte:name_node.end_byte].decode()
    params = source[params_node.start_byte:params_node.end_byte].decode()
    ret = ""
    if return_node:
        ret = " -> " + source[return_node.start_byte:return_node.end_byte].decode()
    return f"def {name}{params}{ret}"
