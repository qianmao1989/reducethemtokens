SYMBOLS_QUERY = """
(function_declaration
  name: (identifier) @fn_name
  parameters: (formal_parameters) @fn_params) @function

(class_declaration
  name: (identifier) @class_name) @class

(method_definition
  name: (property_identifier) @method_name
  parameters: (formal_parameters) @method_params) @method

(lexical_declaration
  (variable_declarator
    name: (identifier) @const_name
    value: (arrow_function
      parameters: (formal_parameters) @arrow_params))) @arrow_fn
"""

IMPORTS_QUERY = """
(import_statement
  source: (string) @import_source)
"""


def extract_fn_signature(source: bytes, name_node, params_node, return_node=None) -> str:
    name = source[name_node.start_byte:name_node.end_byte].decode()
    params = source[params_node.start_byte:params_node.end_byte].decode()
    return f"function {name}{params}"
