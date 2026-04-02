from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base


class SaasCompanyRole(Base):
    __tablename__ = "saas_company_roles"

    __table_args__ = (
        CheckConstraint("role IN ('admin','viewer','biller')", name="ck_company_role"),
        CheckConstraint("status IN ('active','inactive','removed')", name="ck_company_role_status"),
    )

    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.company_id", ondelete="RESTRICT"),
        primary_key=True, nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("saas_user_data.user_id", ondelete="RESTRICT"),
        primary_key=True, nullable=False,
    )
    role: Mapped[str] = mapped_column(Text, primary_key=True, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)

    company: Mapped["Company"] = relationship(back_populates="company_roles")
    user: Mapped["SaasUserData"] = relationship(back_populates="company_roles")
