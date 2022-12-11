from utype import Schema, Field
from datetime import datetime


class ArticleSchema(Schema):
    title: str
    content: str
    updated_at: datetime = Field(default_factory=datetime.now, no_input=True)


class KeyInfo(Schema):
    access_key: str = Field(no_output=True)
    last_activity: datetime = Field(default_factory=datetime.now, no_input=True)

    @property
    def key_sketch(self) -> str:
        return self.access_key[:5] + '*' * (len(self.access_key) - 5)
