from datetime import datetime
import strawberry
import typing as t

from sqlmodel import SQLModel
from app.db import models as m


def list_to_map(list: t.List[t.Any]) -> t.Mapping[int, t.Any]:
  return {k: v for k, v in enumerate(list)}


class MetaKeywordArguments(type):
  def __new__(cls, name, bases, class_dict, **kwargs):
    if 'model' in kwargs:
      model: SQLModel = kwargs['model']
      class_dict['__annotations__'] = {}

      for field, type in model.model_fields.items():
        graphql_type = type.annotation
        metadata = list_to_map(type.metadata)

        if hasattr(type, 'primary_key') and type.primary_key:
          graphql_type = strawberry.ID

        class_dict['__annotations__'][field] = graphql_type
        class_dict[field] = strawberry.field(
          graphql_type=graphql_type,
          metadata=metadata
        )

    return super().__new__(cls, name, bases, class_dict)

  def __init__(cls, name, bases, class_dict, **kwargs):
    return super().__init__(name, bases, class_dict)


class BaseType(metaclass=MetaKeywordArguments):
  @classmethod
  def from_model(cls, model: SQLModel):
    return cls(**{k: getattr(model, k) for k in model.model_fields})


@strawberry.type
class Person(BaseType, model=m.Person):
  pass
