from datetime import datetime
from sqlalchemy import String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Redirect(Base):
    __tablename__ = "redirect"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(50))
    host: Mapped[str] = mapped_column(String(50))
    user_agent: Mapped[str] = mapped_column(String(500))
    destination: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"Redirect(id={self.id!r}, platform={self.platform!r}, host={self.host!r}, user_agent={self.user_agent!r}, destination={self.destination!r}, created_at={self.created_at!r})"
