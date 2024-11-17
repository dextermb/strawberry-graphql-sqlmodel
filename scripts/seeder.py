from datetime import datetime
from sqlmodel import SQLModel, Session, create_engine

from app.db.models import Person

engine = create_engine("sqlite:///database.db")

SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    session.add(Person(name="Person 1", email_address="person-1@example.com", age=10, created_at=datetime.now()))
    session.add(Person(name="Person 2", email_address="person-2@example.com", age=20, created_at=datetime.now()))
    session.add(Person(name="Person 3", email_address="person-3@example.com", age=30, created_at=datetime.now()))
    session.commit()
