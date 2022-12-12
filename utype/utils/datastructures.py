
class Unprovided:
    def __bool__(self):
        return False

    def __eq__(self, other):
        return self(other)

    def __call__(self, v):
        return isinstance(v, Unprovided)

    def __repr__(self):
        return '<unprovided>'


unprovided = Unprovided()
