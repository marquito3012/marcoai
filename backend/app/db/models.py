"""
MarcoAI – SQLAlchemy ORM Models (Phase 1 / Core)

Every future domain table MUST include a `user_id` column referencing
`users.id` to enforce row-level isolation between tenants.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Users ─────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    google_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    picture_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    # Google Calendar OAuth tokens (encrypted at rest in production)
    google_calendar_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_calendar_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    google_calendar_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships (populated as other modules are added)
    # finances: Mapped[list["Transaction"]] = relationship(back_populates="user")


# ── Chat History (lightweight, in-DB store for short-term context) ────────────
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))   # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    user: Mapped["User"] = relationship("User")


# ── Finance Transactions (Fase 7) ─────────────────────────────────────────────
class TransactionType(str):
    INCOME = "income"
    EXPENSE = "expense"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(16))  # "income" | "expense"
    amount: Mapped[float] = mapped_column()  # Always positive, type indicates direction
    category: Mapped[str] = mapped_column(String(64))  # e.g., "food", "transport", "salary"
    description: Mapped[str] = mapped_column(Text)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    is_fixed: Mapped[bool] = mapped_column(Boolean, default=False)  # Recurring transaction
    recurrence: Mapped[str | None] = mapped_column(String(32), nullable=True)  # "monthly", "weekly", etc.
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user: Mapped["User"] = relationship("User")


# ── Documents (Fase 9) ────────────────────────────────────────────────────────
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, processing, completed, error
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship("User")


# ── Habits and Todos (Fase 10) ────────────────────────────────────────────────
class Habit(Base):
    __tablename__ = "habits"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    frequency: Mapped[str] = mapped_column(String(32), default="daily") # daily, weekly
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship("User")

class HabitLog(Base):
    __tablename__ = "habit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    habit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("habits.id", ondelete="CASCADE"), index=True
    )
    completed_date: Mapped[str] = mapped_column(String(10)) # YYYY-MM-DD
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("todos.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    
    user: Mapped["User"] = relationship("User")

