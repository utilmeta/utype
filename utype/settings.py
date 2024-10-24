import warnings


class WarningSettings:
    disabled: bool = False
    parse_ignore_both_params_and_result: bool = True
    dataclass_setattr_delattr_not_effect: bool = True
    globals_name_conflict: bool = True
    field_unresolved_types_with_throw_options: bool = True
    field_alias_on_positional_args: bool = True
    field_case_sensitive_on_positional_args: bool = True
    field_invalid_params_in_function: bool = True

    function_kwargs_With_no_addition: bool = True
    function_invalid_options: bool = True
    function_invalid_return_annotation: bool = True
    function_invalid_params_annotation: bool = True
    function_non_default_follows_default_args: bool = True

    options_max_errors_with_no_collect_errors: bool = True

    rule_length_constraints_on_unsupported_types: bool = True
    rule_no_origin_transformer: bool = True
    rule_no_arg_transformer: bool = True
    rule_arg_parser_unresolved: bool = True
    rule_none_arg_in_unsupported_origin: bool = True
    rule_args_in_any: bool = True

    def warn(self, message: str, type: str = None):
        if self.disabled:
            return
        if type is False:
            return
        if isinstance(type, str):
            if not getattr(self, type, None):
                return
        warnings.warn(message)


warning_settings = WarningSettings()
