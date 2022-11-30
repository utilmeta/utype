from utype import Schema, Field, Options
import pydantic
from typing import Tuple, List, Dict
from datetime import datetime


def pydantic_convert():
    class schema(pydantic.BaseModel):
        name: str = pydantic.Field('test', const=True)
        views: int = pydantic.Field(..., ge=0, multiple_of=3)
        dt: datetime = pydantic.Field(..., alias='_dt')
        tuple: Tuple[float, List[str]]
        indexes: List[int] = pydantic.Field(..., max_items=3, min_items=1)
        dicts: Dict[str, List[int]]

    errors = 0
    for i in range(0, 1000):
        try:
            schema(
                name="test",
                _dt='2022-02-02 02:02:34',
                views=str(i),
                tuple=['3.3', [1, 2, b'ff']],
                indexes=[i + 0.003, str(i + 1).encode()],
                dicts={"test1": [i], "test2": [str(i + 1).encode()]},
            )
        except Exception as e:
            errors += 1
    print('errors:', errors)


def utilmeta_convert():
    class schema(Schema):
        name: str = Field(const='test')
        views: int = Field(ge=0, multiple_of=3)
        dt: datetime = Field(alias='_dt')
        tuple: Tuple[float, List[str]]
        indexes: List[int] = Field(max_length=3, min_length=1)
        dicts: Dict[str, List[int]]

    errors = 0
    for i in range(0, 1000):
        try:
            # schema(
            #     name="test",
            #     _dt='2022-02-02 02:02:34',
            #     views=i,
            #     tuple=[0.01, [b'1', b'2', b'ff']],
            #     indexes=[i + 0.003, decimal.Decimal('3.1')],
            #     dicts={"test1": [i], "test2": [decimal.Decimal('3.34')]},
            #     __options__=Options(no_explicit_cast=True)
            # )
            schema(
                name="test",
                _dt='2022-02-02 02:02:34',
                views=str(i),
                tuple=['3.3', [1, 2, b'ff']],
                indexes=[i + 0.003, str(i + 1).encode()],
                dicts={"test1": [i], "test2": [str(i + 1).encode()]},
                # __options__=Options(collect_errors=True)
            )
        except Exception as e:
            errors += 1
    print('errors:', errors)


# def utilmeta_19_convert():
#     import sys
#     old_syspath = sys.path
#     sys.path = [path for path in sys.path if 'Project' not in path]
#     print('PATH:', sys.path)
#     from utilmeta.utils import Schema as Schema_19
#     from utilmeta.utils import Rule
#     from typing import Tuple, List, Dict
#     from datetime import datetime
#
#     class schema(Schema_19):
#         name: str = Rule(value='test')
#         views: int = Rule(ge=0, validator=lambda v: v % 3 == 0)
#         dt: datetime = Rule(alias='_dt')
#         tuple: Tuple[float, List[str]]
#         indexes: List[int] = Rule(max_length=3, min_length=1)
#         dicts: Dict[str, List[int]]
#
#     errors = 0
#     for i in range(0, 1000):
#         try:
#             schema(
#                 name="test",
#                 _dt='2022-02-02 02:02:34',
#                 views=str(i),
#                 tuple=['3.3', [1, 2, b'ff']],
#                 indexes=[i + 0.003, str(i + 1).encode()],
#                 dicts={"test1": [i], "test2": [str(i + 1).encode()]},
#             )
#         except Exception as e:
#             errors += 1
    # print('errors:', errors)


if __name__ == "__main__":
    # print(os.path.dirname(__file__))
    # load_performance_test()
    # 5/13 4.1 ~ 4.4 s
    # run_performance_test('from utilmeta.utils import *')
    # run_performance_test('pydantic_convert()')
    # run_performance_test('utilmeta_19_convert()')
    run_performance_test('utilmeta_convert()')
    # load_config()
