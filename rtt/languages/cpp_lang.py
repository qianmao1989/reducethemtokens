SYMBOLS_QUERY = """
(function_definition
  declarator: (function_declarator
    declarator: [(identifier)(field_identifier)] @fn_name
    parameters: (parameter_list) @fn_params)) @function

(class_specifier
  name: (type_identifier) @class_name) @class

(struct_specifier
  name: (type_identifier) @struct_name) @struct
"""

IMPORTS_QUERY = """
(preproc_include
  path: [(string_literal) (system_lib_string)] @include_path)
"""


def extract_fn_signature(source: bytes, name_node, params_node, return_node=None) -> str:
    name = source[name_node.start_byte:name_node.end_byte].decode()
    params = source[params_node.start_byte:params_node.end_byte].decode()
    return f"{name}{params}"
