import strawberry
import typing as t

from .types import Person
from .resolvers import get_person, get_people


@strawberry.type
class Query:
  person: Person|None = strawberry.field(resolver=get_person)
  people: t.Sequence[Person] = strawberry.field(resolver=get_people)


schema = strawberry.Schema(query=Query)
