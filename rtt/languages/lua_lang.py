SYMBOLS_QUERY = """
(function_declaration
  (function)
  name: [(identifier) @fn_name
         (dot_index_expression) @fn_name
         (method_index_expression) @fn_name]
  parameters: (parameters) @fn_params) @function

(variable_declaration
  (assignment_statement
    variable_list: (variable_list
      (identifier) @var_name)
    expression_list: (expression_list
      (table_constructor) @table))) @table_decl
"""

IMPORTS_QUERY = """
(function_call
  (identifier) @require_name
  arguments: (arguments
    (string) @require_arg))
"""


def extract_fn_signature(source: bytes, name_node, params_node, return_node=None) -> str:
    name = source[name_node.start_byte:name_node.end_byte].decode()
    params = source[params_node.start_byte:params_node.end_byte].decode()
    return f"function {name}{params}"
