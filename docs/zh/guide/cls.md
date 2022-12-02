# 解析数据类
```python
from utype import Schema, Rule, Field
from datetime import datetime

class Slug(str, Rule):  
    regex = r"[a-z0-9]+(?:-[a-z0-9]+)*"
    
class ArticleSchema(Schema):
	slug: Slug = Field(max_length=30)
	content: str = Field(alias_from=['body', 'text'])
	views: int = Field(ge=0, default=0)
	created_at: datetime = Field(required=False)

print(ArticleSchema(slug='my-article', text=b'my article body'))
#>
```

