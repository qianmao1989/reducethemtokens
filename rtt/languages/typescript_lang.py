SYMBOLS_QUERY = """
(function_declaration
  name: (identifier) @fn_name
  parameters: (formal_parameters) @fn_params
  return_type: (type_annotation)? @fn_return) @function

(class_declaration
  name: (type_identifier) @class_name) @class

(method_definition
  name: (property_identifier) @method_name
  parameters: (formal_parameters) @method_params
  return_type: (type_annotation)? @method_return) @method

(interface_declaration
  name: (type_identifier) @interface_name) @interface
"""

IMPORTS_QUERY = """
(import_statement
  source: (string) @import_source)
"""


def extract_fn_signature(source: bytes, name_node, params_node, return_node=None) -> str:
    name = source[name_node.start_byte:name_node.end_byte].decode()
    params = source[params_node.start_byte:params_node.end_byte].decode()
    ret = ""
    if return_node:
        ret = ": " + source[return_node.start_byte:return_node.end_byte].decode().lstrip(": ")
    return f"function {name}{params}{ret}"
