from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    avatar_color = Column(String(7), default="#4CAF50")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    duplicates = relationship("DuplicateSticker", back_populates="owner", cascade="all, delete-orphan")
    wanted = relationship("WantedSticker", back_populates="owner", cascade="all, delete-orphan")


class DuplicateSticker(Base):
    __tablename__ = "duplicate_stickers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sticker_number = Column(Integer, nullable=False)
    quantity = Column(Integer, default=1)

    __table_args__ = (UniqueConstraint("user_id", "sticker_number", name="uq_user_duplicate"),)

    owner = relationship("User", back_populates="duplicates")


class WantedSticker(Base):
    __tablename__ = "wanted_stickers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sticker_number = Column(Integer, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "sticker_number", name="uq_user_wanted"),)

    owner = relationship("User", back_populates="wanted")


class TradeSuggestion(Base):
    __tablename__ = "trade_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    payload = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
