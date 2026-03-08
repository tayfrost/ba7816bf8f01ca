from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base


class SaasUserData(Base):
    __tablename__ = "saas_user_data"

    __table_args__ = (
        CheckConstraint("char_length(trim(name)) > 1", name="ck_saas_name_len"),
        CheckConstraint("char_length(trim(surname)) > 1", name="ck_saas_surname_len"),
        CheckConstraint(
            "char_length(trim(email)) > 3 AND position('@' in trim(email)) > 1 "
            "AND position('@' in trim(email)) < char_length(trim(email))",
            name="ck_saas_email",
        ),
    )

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    surname: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)

    company_roles: Mapped[list["SaasCompanyRole"]] = relationship(back_populates="user")
