from utype import Schema, Field
from typing import List


class Member(Schema):
    name: str
    level: int = 0


class Group(Schema):
    name: str
    creator: Member
    members: List[Member] = Field(default_factory=list)


Group(
    name='group 1',
    creator=b'{"name": "Alice", "level": 3}',
    members=[{'name': 'bob'}, {'name': 'tom', 'level': '2'}]
)
