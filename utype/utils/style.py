import warnings
from typing import Union, List, Callable
from .functional import multi


class CaseStyle:
    camelCase = 'camel'
    PascalCase = 'pascal'
    snake_case = 'snake'
    kebab_case = 'kebab'
    CAP_KEBAB_CASE = 'cap_kebab'
    CAP_SNAKE_CASE = 'cap_snake'


CASE_STYLES = [
    CaseStyle.camelCase,
    CaseStyle.PascalCase,
    CaseStyle.snake_case,
    CaseStyle.kebab_case,
    CaseStyle.CAP_KEBAB_CASE,
    CaseStyle.CAP_SNAKE_CASE
]


class AliasGenerator:
    @classmethod
    def guess_style(cls, style: Union[str, Callable]):
        if callable(style):
            return style
        if not isinstance(style, str) or not style:
            return None
        style = style.lower()
        if CaseStyle.camelCase in style:
            return CaseStyle.camelCase
        if CaseStyle.snake_case in style:
            if 'cap' in style:
                return CaseStyle.CAP_SNAKE_CASE
            return CaseStyle.snake_case
        if CaseStyle.kebab_case in style:
            if 'cap' in style:
                return CaseStyle.CAP_KEBAB_CASE
            return CaseStyle.kebab_case
        if CaseStyle.PascalCase in style:
            return CaseStyle.PascalCase
        # guess val
        ans = ''.join(filter(str.isalnum, style))
        if '_' in style:
            if ans.isupper():
                return CaseStyle.CAP_SNAKE_CASE
            return CaseStyle.snake_case
        if '-' in style:
            if ans.isupper():
                return CaseStyle.CAP_KEBAB_CASE
            return CaseStyle.kebab_case
        if ans.isupper():
            return CaseStyle.CAP_SNAKE_CASE
        if ans.islower():
            return CaseStyle.snake_case
        if ans[0].islower():
            return CaseStyle.camelCase
        return CaseStyle.PascalCase

    def __init__(self, generator: Union[str, Callable], allow_conflict: bool = False):
        self.generator = self.guess_style(generator)
        if not self.generator:
            raise ValueError(f'Invalid case style: {generator}')
        self.allow_conflict = allow_conflict
        self.func = None
        if callable(self.generator):
            self.func = self.generator
        elif isinstance(self.generator, str):
            self.func = getattr(self.__class__, self.generator, None)
        if not self.func:
            raise ValueError(f'Invalid case style: {generator}')

    def __call__(self, data):
        if not self.generator or not data:
            return data
        if multi(data):
            return [self(d) for d in data]
        elif isinstance(data, dict):
            result = {}
            if data.get('@'):
                return data
            for key, val in data.items():
                k = self(key)
                if not self.allow_conflict and k in result:
                    raise ValueError(f'Duplicate data key: {k}')
                if multi(k) and k:
                    k = list(k)[0]
                if not isinstance(k, str):
                    # invalid key, ignore
                    continue
                result[k] = val
            return result
        elif isinstance(data, str):
            try:
                return self.func(data)
            except Exception as e:
                warnings.warn(f'apply field transformer failed with error: {e}, ignoring...')
                return data
        return data

    @classmethod
    def pascal(cls, val: str):
        if not val:
            return ''
        split = None
        if '_' in val:
            # guess type: snake / cap_snake
            split = '_'
        elif '-' in val:
            split = '-'
        if split:
            val = "".join(
                word.capitalize() for word in val.split(split)
            )
        if not val.isalnum():
            return val
        # val = ''.join(filter(str.isalnum, val))
        if split:
            return val
        if val.islower():
            return val.capitalize()
        if val.isupper():
            return val.capitalize()
        if val[0].islower():
            # guess is PascalCase
            return val[0].upper() + val[1:]
        return val

    @classmethod
    def snake(cls, val: str):
        if not val:
            return ''
        if '_' in val:
            # guess type: snake / cap_snake
            return val.lower()
        elif '-' in val:
            return val.replace('-', '_').lower()

        if not val.isalnum():
            return val

        # val = ''.join(filter(str.isalnum, val))

        if val.islower():
            return val
        if val.isupper():
            return val.lower()

        s = ''
        for i, c in enumerate(val):
            if c.isupper():
                if i:
                    # not for first upper case
                    s += '_'
                c = c.lower()
            s += c

        return s

    @classmethod
    def camel(cls, val: str):
        val = cls.pascal(val)
        return val[0].lower() + val[1:]

    @classmethod
    def cap_snake(cls, val: str):
        return cls.snake(val).upper()

    @classmethod
    def kebab(cls, val: str):
        return cls.snake(val).replace('_', '-')

    @classmethod
    def cap_kebab(cls, val: str):
        return cls.cap_snake(val).replace('_', '-')

    @classmethod
    def generate_aliases(cls, val: str, generator: Union[str, Callable, List[str], bool] = '*'):
        if not generator:
            return []
        if generator == '*' or generator is True:
            generator = CASE_STYLES
        elif not multi(generator):
            generator = [generator]
        aliases = []

        def _validator(v):
            return isinstance(v, str) and v and v != val

        for g in generator:
            res = cls(generator=g)(val)
            if multi(res):
                for r in res:
                    if _validator(r):
                        aliases.append(r)
            elif _validator(res):
                aliases.append(res)
        return aliases
