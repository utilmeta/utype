import inspect
from typing import Callable, Optional


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
