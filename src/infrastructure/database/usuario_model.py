from uuid import UUID

from sqlalchemy import Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from domain.value_objects.perfil_usuario import PerfilUsuario
from infrastructure.database.base import Base


class UsuarioModel(Base):
    __tablename__ = "usuarios"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(Text)
    # O índice único garante um login por e-mail; a entidade já o guarda em minúsculas.
    email: Mapped[str] = mapped_column(String(254), unique=True)
    senha_hash: Mapped[str] = mapped_column(Text)
    # VARCHAR com CHECK em vez de tipo ENUM do PostgreSQL: incluir um perfil não exige ALTER TYPE.
    perfil: Mapped[PerfilUsuario] = mapped_column(
        Enum(
            PerfilUsuario,
            name="perfil_usuario",
            native_enum=False,
            create_constraint=True,
            length=20,
        )
    )
    ativo: Mapped[bool]
