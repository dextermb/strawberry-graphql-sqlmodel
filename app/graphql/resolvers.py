import typing as t
from sqlmodel.sql.expression import SelectOfScalar
from sqlmodel import Session, create_engine, select

from app.db import models as db
from app.graphql import types as gql
from app.util.decorators.resolver import resolver


engine = create_engine("sqlite:///database.db")


def get_person(self, id: int):
  with Session(engine) as session:
    stmt = select(db.Person).where(db.Person.id == id).limit(1)

    person = session.exec(stmt).first()

    if person is not None:
      return gql.Person.from_model(person)

    return None


@resolver(db.Person, t.Sequence[gql.Person])
def get_people(
    self,
    stmt: SelectOfScalar[db.Person],
    **kwargs
  ) -> t.Sequence[gql.Person]:
  with Session(engine) as session:
    people = session.exec(stmt).all()

    return [gql.Person.from_model(m) for m in people]
