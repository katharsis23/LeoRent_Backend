from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import JSON, String, Integer, Boolean, Text, Float, ForeignKey
from src.leorent_backend.database_connector import BASE
from uuid import UUID as PythonUUID, uuid4
from enum import Enum
from typing import Optional, Dict, Any, List


# Basic Constants(Enums)
class UserType(Enum):
    AGENT = "agent"
    OWNER = "owner"
    DEFAULT = "default"


class RentType(Enum):
    DEFAULT = "DEFAULT"
    DAILY = "DAILY"


class Users(BASE):
    __tablename__ = "users"

    id_: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    username: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        unique=True
    )

    password: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    email: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True)

    type_: Mapped[UserType] = mapped_column(
        ENUM(UserType), nullable=False, default=UserType.DEFAULT
    )

    phone_number: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        unique=True
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)

    firebase_uid: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        unique=True
    )

    first_name: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )

    last_name: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    # Relationships
    apartments: Mapped[List["Apartment"]] = relationship(
        "Apartment", back_populates="owner_user", cascade="all, delete-orphan"
    )

    liked_apartments: Mapped[List["Liked"]] = relationship(
        "Liked", back_populates="user", cascade="all, delete-orphan"
    )


class Apartment(BASE):
    __tablename__ = "apartment"

    id_: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    location: Mapped[str] = mapped_column(Text, nullable=False)

    district: Mapped[str] = mapped_column(String(255), nullable=False)

    cost: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    rent_type: Mapped[RentType] = mapped_column(
        ENUM(RentType), nullable=False, default=RentType.DEFAULT
    )

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    rooms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    square: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    floor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    floor_in_house: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)

    details: Mapped[Optional[Dict[str, Any]]
                    ] = mapped_column(JSON, nullable=True)

    type_: Mapped[str] = mapped_column(String(255), nullable=False)

    renovation_type: Mapped[str] = mapped_column(String(255), nullable=False)

    # Foreign key with proper constraint
    owner: Mapped[PythonUUID] = mapped_column(
        UUID(
            as_uuid=True), ForeignKey(
            "users.id_", ondelete="CASCADE"), nullable=False)

    # Relationships
    owner_user: Mapped["Users"] = relationship(
        "Users", back_populates="apartments")

    pictures: Mapped[List["Pictures"]] = relationship(
        "Pictures", back_populates="apartment", cascade="all, delete-orphan"
    )

    liked_by: Mapped[List["Liked"]] = relationship(
        "Liked", back_populates="apartment", cascade="all, delete-orphan"
    )


class Pictures(BASE):
    __tablename__ = "pictures"

    id_: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    apartment_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("apartment.id_", ondelete="CASCADE"),
        nullable=False,
    )

    # TODO: Consider adding the default value
    url: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    metadata_: Mapped[Optional[Dict[str, Any]]
                      ] = mapped_column(JSON, nullable=True)

    # Relationships
    apartment: Mapped["Apartment"] = relationship(
        "Apartment", back_populates="pictures"
    )


class Liked(BASE):
    __tablename__ = "liked"

    id_: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    user_id: Mapped[PythonUUID] = mapped_column(
        UUID(
            as_uuid=True), ForeignKey(
            "users.id_", ondelete="CASCADE"), nullable=False)

    apartment_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("apartment.id_", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    user: Mapped["Users"] = relationship(
        "Users", back_populates="liked_apartments")

    apartment: Mapped["Apartment"] = relationship(
        "Apartment", back_populates="liked_by"
    )
