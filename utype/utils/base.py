import inspect
from typing import Callable, Optional, Dict, Any, TypeVar, List
from .datastructures import ImmutableDict
from .functional import represent, multi, distinct_add

T = TypeVar('T')
SEG = '__'


class TypeRegistry:
    def __init__(self,
                 name: str = 'default',
                 base: 'TypeRegistry' = None,
                 validator: Callable = callable,
                 cache: bool = False,
                 default=None,
                 shortcut: str = None
                 ):
        self._registry = []
        self._cache = {}

        self.name = name
        self.cache = cache
        self.default = default
        self.shortcut = shortcut
        self.base = base
        self.validator = validator

    def register(
        self,
        *classes,
        attr=None,
        detector=None,
        metaclass=None,
        # to=None,  # register to a specific type transformer class
        allow_subclasses: bool = True,
        priority: int = 0,
    ):
        # detect class by issubclass or hasattr
        # this method can override
        # the latest function will have the final effect
        # signature = (*classes, attr, detector)

        if not detector:
            if not classes and not attr and not metaclass:
                raise ValueError(
                    f"register_transformer must provide any of classes, metaclass, attr, detector"
                )

            for c in classes:
                assert inspect.isclass(
                    c
                ), f"register_transformer classes must be class, got {c}"

            if attr:
                assert isinstance(
                    attr, str
                ), f"register_transformer classes must be str, got {attr}"

            def detector(_cls):
                if classes:
                    if allow_subclasses:
                        if not issubclass(_cls, classes):
                            return False
                    else:
                        if _cls not in classes:
                            return False
                if metaclass:
                    if not isinstance(_cls, metaclass):
                        return False
                if attr and not hasattr(_cls, attr):
                    return False
                return True

        def decorator(f):
            if not self.validator(f):
                raise TypeError(f'Invalid register target: {f}, must pass <{self.validator}> validate')
            self._registry.insert(0, (detector, f, priority))
            if priority:
                self._registry.sort(key=lambda v: -v[2])
            return f

        # before runtime, type will be compiled and applied
        # if transformer is defined after the validator compiled
        # it will not take effect
        return decorator

    def resolve(self, t: type) -> Optional[Callable]:
        # resolve to it's subclass if both subclass and baseclass is provided
        # like Schema type will not resolve to dict
        if self.shortcut and hasattr(t, self.shortcut) and self.validator(getattr(t, self.shortcut)):
            # this type already got a callable transformer, do not resolve then
            return getattr(t, self.shortcut)
        if self.cache and t in self._cache:
            return self._cache[t]
        for detector, trans, priority in self._registry:
            try:
                if detector(t):
                    if self.cache:
                        self._cache[t] = trans
                    return trans
            except (TypeError, ValueError):
                continue
        if self.base:
            # default to base
            return self.base.resolve(t)
        return self.default


class ParamsCollectorMeta(type):
    def __init__(cls, name, bases: tuple, attrs: dict, **kwargs):
        super().__init__(name, bases, attrs)

        __init = attrs.get('__init__')   # only track current init

        cls._kwargs = kwargs
        cls._pos_var = None
        cls._key_var = None
        cls._pos_keys = []
        cls._kw_keys = []
        cls._defaults = {}
        cls._requires = set()

        if not bases:
            return

        defaults = {}
        requires = set()
        for base in bases:
            if isinstance(base, ParamsCollectorMeta):
                defaults.update(base._defaults)
                requires.update(base._requires)
                distinct_add(cls._pos_keys, base._pos_keys)
                distinct_add(cls._kw_keys, base._kw_keys)
                if base._key_var:
                    cls._key_var = base._key_var
                if base._pos_var:
                    cls._pos_var = base._pos_var

        if __init:
            _self, *parameters = inspect.signature(__init).parameters.items()
            for k, v in parameters:
                v: inspect.Parameter
                if k.startswith(SEG) and k.endswith(SEG):
                    continue
                if v.default is not v.empty:
                    defaults[k] = v.default
                    if k in requires:
                        # if base is required but subclass not
                        requires.remove(k)
                elif v.kind not in (v.VAR_KEYWORD, v.VAR_POSITIONAL):
                    requires.add(k)

                if v.kind == v.VAR_POSITIONAL:
                    cls._pos_var = k
                elif v.kind == v.POSITIONAL_ONLY:
                    if k not in cls._pos_keys:
                        cls._pos_keys.append(k)
                elif v.kind == v.VAR_KEYWORD:
                    cls._key_var = k
                else:
                    if k not in cls._kw_keys:
                        cls._kw_keys.append(k)

        cls._defaults = ImmutableDict(defaults)
        cls._requires = requires
        cls._attr_names = [a for a in attrs if not a.startswith('_')]

    @property
    def cls_path(cls):
        return f'{cls.__module__}.{cls.__name__}'

    @property
    def kw_keys(cls):
        return cls._kw_keys

    @property
    def pos_slice(cls) -> slice:
        if cls._pos_var:
            return slice(0, None)
        return slice(0, len(cls._pos_keys))

    @property
    def cls_name(cls):
        try:
            return cls.__qualname__
        except AttributeError:
            return cls.__name__


class ParamsCollector(metaclass=ParamsCollectorMeta):
    def __init__(self, __params__: Dict[str, Any]):
        args = []
        kwargs = {}
        spec = {}

        for key, val in __params__.items():
            if key.startswith(SEG) and key.endswith(SEG):
                continue
            if val is self:
                continue
            if key == self._pos_var:
                args += list(val)
                continue
            elif key == self._key_var:
                if isinstance(val, dict):
                    _kwargs = {k: v for k, v in val.items() if not k.startswith(SEG)}
                    kwargs.update(_kwargs)
                    spec.update(_kwargs)    # also update spec
                continue
            elif key in self._pos_keys:
                args.append(key)
            elif key in self._kw_keys:
                kwargs[key] = val
            else:
                continue
            if val != self._defaults.get(key):   # for key_var or pos_var the default is None
                spec[key] = val

        self.__args__ = tuple(args)
        self.__kwargs__ = kwargs
        self.__spec_kwargs__ = ImmutableDict(spec)
        self.__name__ = self._get_cls_name()

    def __hash__(self):
        return hash(repr(self))

    def __eq__(self, other: 'ParamsCollector'):
        if inspect.isclass(self):
            return super().__eq__(other)
        if not isinstance(other, self.__class__):
            return False
        return self.__spec_kwargs__ == other.__spec_kwargs__ and self.__args__ == other.__args__

    def __bool__(self):
        # !! return not self.vacuum
        # prevent use <not self.vacuum> as bool (causing lots of recessive errors)
        # let sub utils define there own way of bool
        return True

    def __str__(self):
        return self._repr()

    def __repr__(self):
        return self._repr()

    @classmethod
    def __copy(cls, data, copy_class: bool = False):
        if multi(data):
            return type(data)([cls.__copy(d) for d in data])
        if isinstance(data, dict):
            return {key: cls.__copy(val) for key, val in data.items()}
        if inspect.isclass(data) and not copy_class:
            # prevent class util that carry other utils cause RecursiveError
            return data
        if isinstance(data, ParamsCollector):
            return data.__copy__()
        return data

    def __deepcopy__(self, memo):
        return self.__copy__()

    def __copy__(self):
        # use copied version of sub utils
        # return self.__class__(*self._args, **self._kwargs)
        if inspect.isclass(self):
            bases = getattr(self, '__bases__', ())
            attrs = dict(self.__dict__)
            # pop(attrs, Attr.LOCK)       # pop __lock__
            return self.__class__(self.__name__, bases, self.__copy(attrs))
        return self.__class__(*self.__copy(self.__args__), **self.__copy(self.__spec_kwargs__))

    def _get_cls_name(self):
        if inspect.isclass(self):
            cls = self
        else:
            cls = self.__class__
        try:
            return cls.__qualname__
        except AttributeError:
            return cls.__name__

    def _repr(self, name: str = None,
              includes: List[str] = None,
              excludes: List[str] = None,
              addition: dict = None
              ):
        name = name or self.__name__
        if inspect.isclass(self):
            return f'<{name} class "{self.__module__}.{name}">'
        attrs = []

        for k, v in self.__spec_kwargs__.items():
            # if not isinstance(v, bool) and any([s in str(k).lower() for s in self._secret_names]) and v:
            #     v = SECRET
            if k.startswith('_'):
                continue
            if includes is not None and k not in includes:
                continue
            if excludes is not None and k in excludes:
                continue
            attrs.append(k + '=' + represent(v))     # str(self.display(v)))
        if addition:
            for k, v in addition.items():
                if k not in self.__spec_kwargs__:
                    attrs.append(k + '=' + represent(v))
        s = ', '.join([represent(v) for v in self.__args__] + attrs)
        return f'{name}({s})'
