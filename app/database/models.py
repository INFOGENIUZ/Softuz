from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    BigInteger, Integer, String, Text, Boolean, DateTime, ForeignKey, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="user")  # 'user', 'admin', 'owner'
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    downloads_count: Mapped[int] = mapped_column(Integer, default=0)

    favorites: Mapped[List["Favorite"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    ratings: Mapped[List["Rating"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    icon: Mapped[str] = mapped_column(String(16), default="📁")
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    programs: Mapped[List["Program"]] = relationship(back_populates="category", cascade="all, delete-orphan")

class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # 'prog_1', deep-linking
    title: Mapped[str] = mapped_column(String(255), index=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"))
    os_type: Mapped[str] = mapped_column(String(32), default="windows", index=True)  # windows, android, macos, linux, other
    version: Mapped[str] = mapped_column(String(64), default="v1.0")
    description: Mapped[str] = mapped_column(Text, default="")
    archive_password: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    file_id: Mapped[str] = mapped_column(String(255))
    file_unique_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    storage_msg_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)  # bytes
    image_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    download_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    downloads_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    category: Mapped["Category"] = relationship(back_populates="programs")
    favorites: Mapped[List["Favorite"]] = relationship(back_populates="program", cascade="all, delete-orphan")
    ratings: Mapped[List["Rating"]] = relationship(back_populates="program", cascade="all, delete-orphan")

class Favorite(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    program_id: Mapped[int] = mapped_column(Integer, ForeignKey("programs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    user: Mapped["User"] = relationship(back_populates="favorites")
    program: Mapped["Program"] = relationship(back_populates="favorites")

class Rating(Base):
    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    program_id: Mapped[int] = mapped_column(Integer, ForeignKey("programs.id"))
    rating: Mapped[int] = mapped_column(Integer)  # 1 to 5
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    user: Mapped["User"] = relationship(back_populates="ratings")
    program: Mapped["Program"] = relationship(back_populates="ratings")

class AppRequest(Base):
    __tablename__ = "app_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    telegram_id: Mapped[int] = mapped_column(BigInteger)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    app_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="pending")  # 'pending', 'approved', 'rejected'
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

class MandatoryChannel(Base):
    __tablename__ = "mandatory_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    channel_title: Mapped[str] = mapped_column(String(255))
    channel_url: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
