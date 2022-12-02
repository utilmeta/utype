from utype import Field, Schema, exc, Options
import pytest


class TestField:
    def test_field_default_required(self):
        class T(Schema):
            f1: str = Field(required=True)
            f2: str
            f3: str = Field(required=False)
            f4: str = Field(default_factory=str)
            f5: int = Field(default=0)

        assert dict(T(f1=1, f2=2)) == {"f1": "1", "f2": "2", "f4": "", "f5": 0}

        with pytest.raises(exc.AbsenceError):
            T(f1=1)

        with pytest.raises(exc.AbsenceError):
            T(f2=1)

    def test_field_alias_from(self):
        class T(Schema):
            f1: str = Field(alias_from=["@f1", "_f1"])
            f2: str = Field(alias="_f2")

        assert dict(T(_f1=1, f2=2)) == {"f1": "1", "_f2": "2"}
        assert dict(T(f1=1, _f2=2)) == {"f1": "1", "_f2": "2"}

        with pytest.raises(Exception):

            class T(Schema):  # noqa
                f1: str = Field(alias_from=["@f1", "f2"])
                f2: str

        with pytest.raises(Exception):

            class T(Schema):  # noqa
                f1: str = Field(alias_from=["@f1", "_f1"])
                f2: str = Field(alias_from=["@f1", "_f2"])

        with pytest.raises(Exception):

            class T(Schema):  # noqa
                f1: str = Field(alias_from=["@f1", "_f1"])
                f2: str = Field(alias="@f1")

        with pytest.raises(Exception):

            class T(Schema):  # noqa
                f1: str = Field(alias="f2")
                f2: str

    def test_field_case_insensitive(self):
        class T(Schema):
            some_field: str = Field(case_insensitive=True)

        assert T(soMe_FiEld=1).some_field == "1"

        with pytest.raises(Exception):

            class T(Schema):  # noqa
                some_field: str = Field(case_insensitive=True)
                soMe_Field: int

        with pytest.raises(Exception):

            class T(Schema):  # noqa
                some_field: str = Field(case_insensitive=True)
                f2: int = Field(alias_from=["some_FIELD", "_f2"])

        with pytest.raises(Exception):

            class T(Schema):  # noqa
                some_field: str = Field(case_insensitive=True)
                f2: int = Field(alias="some_FIELD")

    def test_field_mode(self):
        class T(Schema):
            ro: str = Field(readonly=True)
            wo: str = Field(writeonly=True)
            ra: str = Field(mode="ra")
            wa: str = Field(mode="wa")

        class Tr(T):
            __options__ = Options(mode="r")

        class Twa(T):
            __options__ = Options(mode="wa")

        assert dict(T(__options__=Options(mode="r"), ro=1, wo=1, ra=1, wa=1)) == {
            "ro": "1",
            "ra": "1",
        }
        assert dict(Tr(ro=1, wo=1, ra=1, wa=1)) == {"ro": "1", "ra": "1"}
        assert dict(Twa(ro=1, wo=1, ra=1, wa=1)) == {"wa": "1"}
        # test no mode
        assert dict(T(ro=1, wo=1, ra=1, wa=1)) == {
            "ro": "1",
            "ra": "1",
            "wo": "1",
            "wa": "1",
        }
        assert dict(T(__options__=Options(mode="w"), ro=1, wo=1, ra=1, wa=1)) == {
            "wo": "1",
            "wa": "1",
        }
        assert dict(T(__options__=Options(mode="a"), ro=1, wo=1, ra=1, wa=1)) == {
            "ra": "1",
            "wa": "1",
        }
        assert dict(T(__options__=Options(mode="ra"), ro=1, wo=1, ra=1, wa=1)) == {
            "ra": "1",
        }

        with pytest.raises(Exception):

            class T(Schema):  # noqa
                rwo: str = Field(readonly=True, writeonly=True)

        with pytest.raises(Exception):

            class T(Schema):  # noqa
                rwo: str = Field(readonly=True, mode="rw")

        with pytest.raises(Exception):

            class T(Schema):  # noqa
                rwo: str = Field(writeonly=True, mode="rw")

    def test_field_no_input_output(self):
        class T(Schema):
            noi: str = Field(no_input=True)
            noo: str = Field(no_output=True)
            noic: str = Field(no_input=lambda v: not v)
            nooc: str = Field(no_output=lambda v: not v)
            noir: str = Field(no_input="r", no_output="a")
            noiwa: str = Field(no_input="wa", no_output="a")

        test = T(
            noi="123",
            noo="noo",
            noic="v",
            nooc="",
            noir="noir",
            noiwa="noiwa",
        )
        with pytest.raises(AttributeError):
            _ = test.noi
        assert "noi" not in test
        assert (
            "nooc" not in test
        )  # not included in dict, but can access through attribute
        assert test.nooc == ""
        assert test.noic == "v"
        assert dict(test) == {"noic": "v", "noir": "noir", "noiwa": "noiwa"}
        test.noi = 1
        assert test.noi == "1"
        assert "noi" in test

        test2 = T(**test, noo="noo", nooc="", __options__=Options(mode="r"))
        with pytest.raises(AttributeError):
            _ = test2.noir

        assert dict(test2) == {"noic": "v", "noiwa": "noiwa"}

        test3 = T(**test, noo="noo", nooc="", __options__=Options(mode="wa"))
        with pytest.raises(AttributeError):
            _ = test3.noiwa
        assert dict(test3) == {
            "noic": "v",
            "noir": "noir",
        }

        with pytest.raises(Exception):

            class T(Schema):  # noqa
                # no input does not in mode
                noi: str = Field(mode="r", no_input="wa")

        with pytest.raises(Exception):

            class T(Schema):  # noqa
                # no input does not in mode
                noi: str = Field(mode="r", no_output="ra")

    def test_field_on_error(self):
        pass

    def test_field_unprovided(self):
        pass

    def test_field_constraints(self):
        class T(Schema):
            st: str = Field(max_length=3, min_length=1)
            num: int = Field(ge=0, le=10)

        assert dict(T(st=123, num=b"5")) == {"st": "123", "num": 5}

        with pytest.raises(exc.ParseError):
            T(st="", num="1")

        with pytest.raises(exc.ParseError):
            T(st=1234, num=20)

        with pytest.raises(Exception):

            class T(Schema):
                num: int = Field(ge=10, le=5)

        with pytest.raises(Exception):

            class T(Schema):
                num: bool = Field(max_digits=10)

        with pytest.raises(Exception):

            class T(Schema):
                num: int = Field(unique_items=True)

        with pytest.raises(Exception):

            class T(Schema):
                num: str = Field(max_contains=3, contains=int)

        with pytest.raises(Exception):

            class T(Schema):
                num: list = Field(max_contains=3)

        with pytest.raises(Exception):

            class T(Schema):
                num: list = Field(max_contains=3, min_contains=10, contains=int)

    def test_field_dependencies(self):
        pass

    def test_field_immutable(self):
        pass

    def test_field_discriminator(self):
        pass

    def test_deprecated(self):
        class T(Schema):
            de: str = Field(deprecated=True)
            det: str = Field(deprecated="prefer")
            prefer: str = ""

        with pytest.warns():
            T(de=1)

        with pytest.warns(match="prefer"):
            T(det=1)

        with pytest.raises(Exception):

            class T(Schema):
                det: str = Field(deprecated="not_exists")
