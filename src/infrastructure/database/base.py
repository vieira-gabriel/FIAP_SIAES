from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base dos modelos do ORM; seu `metadata` alimenta o autogenerate do Alembic."""
