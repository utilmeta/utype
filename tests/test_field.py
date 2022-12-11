from utype import Field, Schema, DataClass, exc, Options, parse, dataclass
import pytest
import warnings
from typing import Union, Literal, Final
from utype.utils.style import AliasGenerator


class TestField:
    def test_field_default_required(self):
        class T(Schema):
            f1: str = Field(required=True)
            f2: str
            f3: str = Field(required=False)
            f4: str = Field(default_factory=str)
            f5: int = Field(default=0)
            f6: str = ''
            df: dict = Field(default_factory=dict, defer_default=True)

        assert dict(T(f1=1, f2=2)) == {"f1": "1", "f2": "2", "f4": "", "f5": 0, 'f6': ''}

        with pytest.raises(exc.AbsenceError):
            T(f1=1)

        with pytest.raises(exc.AbsenceError):
            T(f2=1)

        t = T(f1=1, f2=2)
        assert 'df' not in t
        assert t.df == {}
        t.df.update(info=[])
        assert t.df == {}       # won't affect, because a new one is generated

        with pytest.raises(AttributeError):
            _ = t.f3

        with pytest.raises(KeyError):
            _ = t['f3']

    def test_field_default_required_function(self):
        # @parse
        # def func(
        #     f1: str,
        #     f2: str = Field(required=True),
        #     f3: str = Field(required=False),
        #     f4: str = Field(default_factory=str),
        #     f5: int = Field(default=0),
        #     f6: str = ''
        # ):
        #     return locals()

        with pytest.raises(Exception):
            # not accept a not required field with no default
            @parse
            def func(f1: str = Field(required=False)):
                return f1

        @parse
        def func(f1: str = Field(required=False)): pass
        # a passed function can declare not-always-provided param

        with pytest.warns():
            @parse
            def func(
                f1: str = Field(required=False, default=''),
                f2: str = Field(required=True),
            ):
                return f1, f2

            # required param is after the optional param
            # in not-keyword-only (can be positional passed) function

        with pytest.raises(SyntaxError):
            @parse
            def func3(
                f0: str,
                f1: str = Field(required=False, default=''),
                f2: str = Field(required=True),
                _p1: int = 0,
                # positional only
                /,
                # positional or keyword
                f3: str = Field(required=True),
            ):
                return locals()
            # required param is after the optional param
            # in not-keyword-only (can be positional passed) function

        with pytest.warns():
            @parse
            def func3(
                f0: str,
                f1: str = Field(required=False, default=''),
                f2: str = Field(required=True),
            ):
                return locals()
            # required param is after the optional param
            # in not-keyword-only (can be positional passed) function

        with warnings.catch_warnings():
            warnings.simplefilter("error")

            @parse
            def func(
                *,  # if we add a key-word-only sign, it
                f1: str = Field(default=''),
                f2: str = Field(required=True),
            ):
                return f1, f2

        with pytest.warns():
            # defer default means nothing to
            @parse
            def func(f1: str = Field(default=0, defer_default=True)):
                return f1

    def test_field_alias(self):
        class T(Schema):
            f1: str = Field(alias_from=["@f1", "_f1"], required=False)
            f2: str = Field(alias="_f2", required=False)

            CAP_ATTR_NAME: str = Field(
                alias_from=[
                    AliasGenerator.camel,
                    AliasGenerator.kebab,
                    lambda x: "@" + x
                ],
                alias=AliasGenerator.cap_kebab,
                required=False
            )

        assert dict(T(_f1=1, f2=2)) == {"f1": "1", "_f2": "2"}
        assert dict(T(f1=1, _f2=2)) == {"f1": "1", "_f2": "2"}

        cap_attr_name_vars = ['CAP_ATTR_NAME', '@CAP_ATTR_NAME', 'cap-attr-name', 'capAttrName', 'CAP-ATTR-NAME']
        for var in cap_attr_name_vars:
            t = T(**{var: 123})
            assert t.CAP_ATTR_NAME == '123'
            assert dict(t) == {'CAP-ATTR-NAME': '123'}

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
        class T(DataClass):
            some_field: str = Field(case_insensitive=True, alias_from=['field1'])

        assert T(soMe_FiEld=1).some_field == "1"

        t = T(FIELD1=1)
        assert t.some_field == "1"

        assert 'some_FIELD' in t    # case insensitive contains

        @dataclass
        class T:
            some_field: str = Field(case_insensitive=True, alias_from=['field1'])

        t = T(soMe_FiEld=1)
        assert t.some_field == "1"

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

        test.nooc = 'some value'
        assert 'nooc' in test       # fill a value that dissatisfy the no_output, so field is back in the data
        test.nooc = ''
        assert 'nooc' not in test   # fill empty value again

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

        with pytest.warns():
            # no_output has no meanings for function
            @parse
            def func(f: str = Field(no_output=True)): pass

    def test_field_on_error(self):
        class T(Schema):
            default: str = Field(on_error=None, required=False, length=3)
            throw: str = Field(on_error='throw', min_length=2, required=False)
            exclude: str = Field(on_error='exclude', max_length=3, required=False)
            preserve: int = Field(on_error='preserve', ge=0, required=False)

        with pytest.raises(exc.ParseError):
            t = T(default='1234')

        with pytest.raises(exc.ParseError):
            t = T(throw='1')

        t = T(exclude='1234')
        assert 'exclude' not in t

        with pytest.warns():
            t = T(preserve=-10)
            assert 'preserve' in t

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
        class T(DataClass):
            immutable: str = Field(immutable=True, default='')

        class T2(Schema):
            immutable: str = Field(immutable=True, default='')
            final: Final[str] = '123'
            mutable: int = 0

        a = T()
        a2 = T2()
        assert a.immutable == ''
        a2.update({
            'mutable': 2,
        })

        with pytest.raises(exc.UpdateError):
            a.immutable = 2

        with pytest.raises(exc.UpdateError):
            a2.immutable = 2

        with pytest.raises(exc.UpdateError):
            a2.final = '321'

        with pytest.raises(exc.UpdateError):
            a2['immutable'] = 2

        with pytest.raises(exc.UpdateError):
            a2['final'] = 2

        with pytest.raises(exc.DeleteError):
            a2.pop('immutable')

        with pytest.raises(exc.DeleteError):
            a2.pop('final')

        with pytest.raises(exc.DeleteError):
            a2.clear()

        with pytest.raises(exc.UpdateError):
            a2.update({
                'immutable': 2,
                'mutable': 3,
            })

        with pytest.raises(exc.UpdateError):
            a2.update({
                'final': 2,
                'mutable': 3,
            })

    def test_field_secret(self):
        pass

    def test_field_discriminator(self):
        @dataclass
        class Video:
            name: Literal['video']
            suffix: str = 'mp4'
            path: str = ''
            resolution: str = None

        class Audio(Schema):
            name: Literal['audio']
            suffix: str = 'mp3'
            path: str = ''
            tone: str = None

        class Other(Schema):
            name = 'other'
            suffix: str
            path: str

        class FileSchema(Schema):
            file: Video | Audio = Field(discriminator=Audio.name)

        video = FileSchema(file=b'{"name": "video", "path": "/file"}')
        assert isinstance(video.file, Video)
        assert video.file.path == '/file'
        assert video.file.suffix == 'mp4'

        audio = FileSchema(file=b'{"name": "audio", "tone": 1}')
        assert isinstance(audio.file, Audio)
        assert audio.file.tone == '1'
        assert audio.file.suffix == 'mp3'

        @parse
        def func(cls, file: Video | Audio = Field(discriminator='name')):
            assert isinstance(file, cls)
            return file.name, file.suffix

        assert func(Audio, b'{"name": "audio", "tone": 1}') == ('audio', 'mp3')
        assert func(Video, b'{"name": "video", "path": "/file"}') == ('video', 'mp4')

        class FileSchema2(Schema):
            file: Video ^ Audio = Field(discriminator='name')

        video = FileSchema2(file=b'{"name": "video", "path": "/file"}')
        assert isinstance(video.file, Video)

        class FileSchema3(Schema):
            file: Union[Video, Audio, None] = Field(discriminator='name')

        video = FileSchema3(file=b'{"name": "video", "path": "/file"}')
        assert isinstance(video.file, Video)

        none = FileSchema3(file=None)
        assert none.file is None

        with pytest.raises(Exception):
            class FileSchema_(Schema):  # noqa
                file: Video = Field(discriminator='name')

        with pytest.raises(Exception):
            class FileSchema_(Schema):  # noqa
                file: str = Field(discriminator='name')

        with pytest.raises(Exception):
            class FileSchema_(Schema):  # noqa
                file: Video | Other = Field(discriminator='name')

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

        class RequestSchema(Schema):
            url: str

            query: dict = Field(default=None)
            querystring: dict = Field(
                default=None,
                deprecated=True,
                description='"query" is prefered'
            )

            data: bytes = Field(default=None)
            body: bytes = Field(default=None, deprecated='data')

            def __validate__(self):
                if self.querystring:
                    self.query = self.querystring
                    del self.querystring
                if self.body:
                    self.data = self.body
                    del self.body

        old_data = {
            'url': 'https://test.com',
            'querystring': {'key': 'value'},
            'body': b'binary'
        }
        request = RequestSchema(**old_data)