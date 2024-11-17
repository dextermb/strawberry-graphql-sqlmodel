import typing as t
from datetime import date
from sqlmodel import SQLModel, Field

from app.util.decorators.resolver import InputField


class BaseModel(SQLModel):
  pass


class Person(BaseModel, table=True):
  id: t.Annotated[t.Optional[int], InputField(list=True)] = Field(default=None, primary_key=True)
  name: t.Annotated[t.Optional[str], InputField(like=True)]
  email_address: str
  age: t.Annotated[t.Optional[int], InputField()]
  created_at: t.Annotated[t.Optional[date], InputField()]
