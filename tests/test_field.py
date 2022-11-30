from utype import Field, Schema, exc, Options
import pytest


class TestField:
    def test_field_default_required(self):
        class T(Schema):
            f1: str = Field(required=True)
            f2: str
            f3: str = Field(required=False)
            f4: str = Field(default=str)
            f5: int = Field(default=0)
        assert dict(T(f1=1, f2=2)) == {
            'f1': '1',
            'f2': '2',
            'f4': '',
            'f5': 0
        }

        with pytest.raises(exc.AbsenceError):
            T(f1=1)

        with pytest.raises(exc.AbsenceError):
            T(f2=1)

    def test_field_alias_from(self):
        class T(Schema):
            f1: str = Field(alias_from=['@f1', '_f1'])
            f2: str = Field(alias='_f2')

        assert dict(T(_f1=1, f2=2)) == {'f1': '1', '_f2': '2'}
        assert dict(T(f1=1, _f2=2)) == {'f1': '1', '_f2': '2'}

        with pytest.raises(Exception):
            class T(Schema):        # noqa
                f1: str = Field(alias_from=['@f1', 'f2'])
                f2: str

        with pytest.raises(Exception):
            class T(Schema):  # noqa
                f1: str = Field(alias_from=['@f1', '_f1'])
                f2: str = Field(alias_from=['@f1', '_f2'])

        with pytest.raises(Exception):
            class T(Schema):  # noqa
                f1: str = Field(alias_from=['@f1', '_f1'])
                f2: str = Field(alias='@f1')

        with pytest.raises(Exception):
            class T(Schema):        # noqa
                f1: str = Field(alias='f2')
                f2: str

    def test_field_case_insensitive(self):
        class T(Schema):
            some_field: str = Field(case_insensitive=True)

        assert T(soMe_FiEld=1).some_field == 1

        with pytest.raises(Exception):
            class T(Schema):     # noqa
                some_field: str = Field(case_insensitive=True)
                soMe_Field: int

        with pytest.raises(Exception):
            class T(Schema):     # noqa
                some_field: str = Field(case_insensitive=True)
                f2: int = Field(alias_from=['some_FIELD', '_f2'])

        with pytest.raises(Exception):
            class T(Schema):     # noqa
                some_field: str = Field(case_insensitive=True)
                f2: int = Field(alias='some_FIELD')

    def test_field_mode(self):
        class T(Schema):
            ro: str = Field(readonly=True)
            wo: str = Field(writeonly=True)
            ra: str = Field(mode='ra')
            wa: str = Field(mode='wa')

        assert dict(T(__options__=Options(mode='r'), ro=1, wo=1, ra=1, wa=1)) == {
            'ro': '1',
            'ra': '1'
        }
        assert dict(T(__options__=Options(mode='w'), ro=1, wo=1, ra=1, wa=1)) == {
            'wo': '1',
            'wa': '1'
        }
        assert dict(T(__options__=Options(mode='a'), ro=1, wo=1, ra=1, wa=1)) == {
            'ra': '1',
            'wa': '1'
        }
        assert dict(T(__options__=Options(mode='ra'), ro=1, wo=1, ra=1, wa=1)) == {
            'ra': '1',
        }

        with pytest.raises(Exception):
            class T(Schema):        # noqa
                rwo: str = Field(readonly=True, writeonly=True)

        with pytest.raises(Exception):
            class T(Schema):         # noqa
                rwo: str = Field(readonly=True, mode='rw')

        with pytest.raises(Exception):
            class T(Schema):         # noqa
                rwo: str = Field(writeonly=True, mode='rw')

    def test_field_no_input_output(self):
        class T(Schema):
            noi: str = Field(no_input=True)
            noir: str = Field(no_input='r', no_output='a')
            noiwa: str = Field(no_input='wa', no_output='a')

        with pytest.raises(Exception):
            class T(Schema):
                # no input does not in mode
                noi: str = Field(mode='r', no_input='wa')

        with pytest.raises(Exception):
            class T(Schema):
                # no input does not in mode
                noi: str = Field(mode='r', no_output='ra')

    def test_field_on_error(self):
        pass

    def test_field_unprovided(self):
        pass

    def test_field_constraints(self):
        class T(Schema):
            st: str = Field(max_length=3, min_length=1)
            num: int = Field(ge=0, le=10)

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
                num: list = Field(max_contains=3)

    def test_field_dependencies(self):
        pass

    def test_field_immutable(self):
        pass

    def test_field_discriminator(self):
        pass

    def test_deprecated(self):
        class T(Schema):
            de: str = Field(deprecated=True)
            det: str = Field(deprecated='prefer')
            prefer: str = ''

        with pytest.warns(DeprecationWarning):
            T(de=1)

        with pytest.warns(DeprecationWarning, match='prefer'):
            T(det=1)

        with pytest.raises(Exception):
            class T(Schema):
                det: str = Field(deprecated='not_exists')
