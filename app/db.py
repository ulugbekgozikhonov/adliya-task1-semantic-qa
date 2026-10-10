from sqlalchemy import ForeignKey, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings

engine = create_engine(settings.database_url)


class Base(DeclarativeBase):
    pass


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int]
    topic_id: Mapped[int]
    answer: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    answer_id: Mapped[int] = mapped_column(
        ForeignKey("answers.id", ondelete="CASCADE"), index=True
    )
    question: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)
