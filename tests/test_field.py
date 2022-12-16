import warnings
from datetime import datetime
from typing import Union

import pytest

from utype import DataClass, Field, Options, Schema, dataclass, exc, parse
from utype.utils.compat import Final, Literal
from utype.utils.style import AliasGenerator


@pytest.fixture(params=(False, True))
def dfs(request):
    return request.param


# @pytest.mark.parametrize(argnames='dfs', argvalues=(False, True))
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

    def test_field_alias(self, dfs):
        class T(Schema):
            __options__ = Options(data_first_search=dfs)

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

    def test_field_case_insensitive(self, dfs):
        class T(DataClass):
            __options__ = Options(data_first_search=dfs)
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

        class CAP(Schema):
            __options__ = Options(data_first_search=dfs)
            FIELD: str = Field(case_insensitive=True)

        cap = CAP(field=1)
        assert 'FielD' in cap
        assert 'field' in cap
        assert dict(cap) == {'FIELD': '1'}
        cap['field'] = 4
        assert dict(cap) == {'FIELD': '4'}

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

    def test_field_mode(self, dfs):
        class T(Schema):
            __options__ = Options(data_first_search=dfs)

            ro: str = Field(readonly=True)
            wo: str = Field(writeonly=True)
            ra: str = Field(mode="ra")
            wa: str = Field(mode="wa")

        class Tr(T):
            __options__ = Options(mode="r")

        class Twa(T):
            __options__ = Options(mode="wa")

        assert dict(T.__from__(dict(ro=1, wo=1, ra=1, wa=1), options=Options(mode="r"))) == {
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
        assert dict(T.__from__(dict(ro=1, wo=1, ra=1, wa=1), options=Options(mode="w"))) == {
            "wo": "1",
            "wa": "1",
        }
        assert dict(T.__from__(dict(ro=1, wo=1, ra=1, wa=1), options=Options(mode="a"))) == {
            "ra": "1",
            "wa": "1",
        }
        assert dict(T.__from__(dict(ro=1, wo=1, ra=1, wa=1), options=Options(mode="ra"))) == {
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

        class UserSchema(Schema):
            __options__ = Options(data_first_search=dfs)

            username: str
            password: str = Field(mode='wa')
            followers_num: int = Field(readonly=True)  # or mode='r'
            signup_time: datetime = Field(
                mode='ra',
                no_input='a',
                default_factory=datetime.now
            )

        new_user_form = 'username=new-user&password=123456'
        new_user = UserSchema.__from__(new_user_form, options=Options(mode='a'))

        assert isinstance(new_user['signup_time'], datetime)
        assert 'followers_num' not in new_user
        assert new_user.password == '123456'

        user_query_result = {
            'username': 'new-user',
            'followers_num': '3',
            'signup_time': '2022-03-04 10:11:12',
        }
        queried_user = UserSchema.__from__(user_query_result, options=Options(mode='r'))

        assert isinstance(queried_user['signup_time'], datetime)
        assert 'followers_num' in queried_user
        assert queried_user['username'] == 'new-user'

        with pytest.raises(AttributeError):
            _ = queried_user.password

        @parse(options=Options(mode='w', override=True, data_first_search=dfs))
        def update_user(user: UserSchema):
            return dict(user)

        @parse(options=Options(mode='a', override=True, data_first_search=dfs))
        def create_user(user: UserSchema):
            return dict(user)

        dic = create_user(new_user_form)
        assert isinstance(dic['signup_time'], datetime)
        assert dic['username'] == 'new-user'

        class UserRead(UserSchema):
            __options__ = Options(mode='r')

        class UserUpdate(UserSchema):
            __options__ = Options(mode='w')

        class UserCreate(UserSchema):
            __options__ = Options(mode='a')

        user_updated_data = {
            'username': 'new-username',
            'password': 'new-password',
            'followers_num': '3',
            'signup_time': '2022-03-04 10:11:12',
        }
        updated_user = UserUpdate(**user_updated_data)
        assert 'followers_num' not in updated_user
        assert 'signup_time' not in updated_user
        assert updated_user['username'] == 'new-username'

        updated_user.followers_num = 3  # test
        assert 'followers_num' not in updated_user  # still not in

        class Article(Schema):
            __options__ = Options(data_first_search=dfs)

            slug: str = Field(no_input='wa')
            title: str
            created_at: datetime = Field(
                mode='ra',
                no_input='a',
                default_factory=datetime.now
            )

            def __validate__(self):
                if 'slug' not in self:
                    self.slug = '-'.join([''.join(filter(str.isalnum, v))
                                          for v in self.title.split()]).lower()

        new_article_json = b'{"title": "My Awesome Article!", "created_at": "ignored"}'
        new_article = Article.__from__(new_article_json, options=Options(mode='a'))
        assert new_article.slug == 'my-awesome-article'
        assert isinstance(new_article.created_at, datetime)

    def test_field_no_input_output(self, dfs):
        class T(Schema):
            __options__ = Options(data_first_search=dfs)

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

        test2 = T.__from__(dict(**test, noo="noo", nooc=""), options=Options(mode="r"))
        with pytest.raises(AttributeError):
            _ = test2.noir

        assert dict(test2) == {"noic": "v", "noiwa": "noiwa"}

        test3 = T.__from__(dict(**test, noo="noo", nooc=""), options=Options(mode="wa"))
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
            def func(f: str = Field(no_output=True)):
                return f

    def test_field_on_error(self, dfs):
        class T(Schema):
            __options__ = Options(data_first_search=dfs)

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

    def test_field_constraints(self, dfs):
        class T(Schema):
            __options__ = Options(data_first_search=dfs)

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
                num: int = Field(max_contains=3, contains=int)

        with pytest.raises(Exception):

            class T(Schema):
                num: list = Field(max_contains=3)

        with pytest.raises(Exception):

            class T(Schema):
                num: list = Field(max_contains=3, min_contains=10, contains=int)

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

    def test_field_repr(self, dfs):
        class AccessInfo(Schema):
            __options__ = Options(data_first_search=dfs)

            access_key: str = Field(repr=lambda v: repr(v[:3] + '*' * (len(v) - 3)))
            secret_key: str = Field(repr='<secret key>')
            last_activity: datetime = Field(default_factory=datetime.now, repr=False)

        access = AccessInfo(access_key='ABCDEFG', secret_key='qwertyu')
        # even in the locals, we deprecate the __qualname__ to use __name__
        assert repr(access) == str(access) == "AccessInfo(access_key='ABC****', secret_key=<secret key>)"

    def test_field_discriminator(self, dfs):
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
            __options__ = Options(data_first_search=dfs)

            file: Video | Audio = Field(discriminator=Audio.name)

        video = FileSchema(file=b'{"name": "video", "path": "/file"}')
        assert isinstance(video.file, Video)
        assert video.file.path == '/file'
        assert video.file.suffix == 'mp4'

        audio = FileSchema(file=b'{"name": "audio", "tone": 1}')
        assert isinstance(audio.file, Audio)
        assert audio.file.tone == '1'
        assert audio.file.suffix == 'mp3'

        @parse(options=Options(data_first_search=dfs))
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

    def test_field_dependencies(self, dfs):
        class Account(Schema):
            __options__ = Options(data_first_search=dfs)

            name: str
            billing_address: str = Field(alias='billing', default=None)  # test with default
            credit_card: str = Field(required=False, dependencies=['billing_address'])

        Account(name='bill')

        account = Account(name='alice', billing_address='some city, some street', credit_card=123456)
        assert account.credit_card == '123456'

        with pytest.raises(exc.DependenciesAbsenceError):
            Account(name='alice', credit_card=123456)

        class UserSchema(Schema):
            __options__ = Options(data_first_search=dfs)

            username: str
            signup_time: datetime = Field(required=False)

            @property
            @Field(dependencies=['signup_time'])
            def signup_days(self) -> int:
                return (datetime.now() - self.signup_time).total_seconds() / (3600 * 24)

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            new_user = UserSchema(username='test')
            assert 'signup_days' not in new_user
            # False

        signup_user = UserSchema(username='test', signup_time='2021-10-11 11:22:33')
        assert 'signup_days' in signup_user
        assert isinstance(signup_user.signup_days, int)
