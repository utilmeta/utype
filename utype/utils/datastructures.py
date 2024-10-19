class Unprovided:
    def __bool__(self):
        return False

    def __eq__(self, other):
        return self(other)

    def __call__(self, v):
        return isinstance(v, Unprovided)

    def __repr__(self):
        return "<unprovided>"


unprovided = Unprovided()


try:
    from functools import cached_property
except ImportError:
    class cached_property:
        """
        Decorator that converts a method with a single self argument into a
        property cached on the instance.

        A cached property can be made out of an existing method:
        (e.g. ``url = cached_property(get_absolute_url)``).
        The optional ``name`` argument is obsolete as of Python 3.6 and will be
        deprecated in Django 4.0 (#30127).
        """
        name = None

        @staticmethod
        def func(instance):
            raise TypeError(
                'Cannot use cached_property instance without calling '
                '__set_name__() on it.'
            )

        def __init__(self, func, name=None):
            self.real_func = func
            self.__doc__ = getattr(func, '__doc__')

        def __set_name__(self, owner, name):
            if self.name is None:
                self.name = name
                self.func = self.real_func
            elif name != self.name:
                raise TypeError(
                    "Cannot assign the same cached_property to two different names "
                    "(%r and %r)." % (self.name, name)
                )

        def __get__(self, instance, cls=None):
            """
            Call the function and put the return value in instance.__dict__ so that
            subsequent attribute access on the instance returns the cached value
            instead of calling cached_property.__get__().
            """
            if instance is None:
                return self
            res = instance.__dict__[self.name] = self.func(instance)
            return res


class ImmutableDict(dict):
    def __error__(self, *args, **kwargs):
        raise AttributeError("ImmutableDict can not modify value")

    __delitem__ = __error__
    __setitem__ = __error__

    def __str__(self):
        return f'{self.__class__.__name__}({super().__repr__()})'

    def __repr__(self):
        return f'{self.__class__.__name__}({super().__repr__()})'

    setdefault = __error__
    pop = __error__
    popitem = __error__
    clear = __error__
    update = __error__


class ImmutableList(list):
    def error(self, *args, **kwargs):
        raise AttributeError("ImmutableList can not modify value")

    def __str__(self):
        return f'{self.__class__.__name__}({super().__repr__()})'

    def __repr__(self):
        return f'{self.__class__.__name__}({super().__repr__()})'

    append = error
    clear = error
    extend = error
    insert = error
    pop = error
    remove = error
    reverse = error
    sort = error
    __iadd__ = error
    __imul__ = error
    __setitem__ = error
    __delitem__ = error
