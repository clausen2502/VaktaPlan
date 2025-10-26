from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String
from core.database import Base

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)

    # relationships
    users = relationship("User", back_populates="org", cascade="all, delete") 
    employees = relationship("Employee", back_populates="org", cascade="all, delete-orphan")
    locations = relationship("Location", back_populates="org", cascade="all, delete-orphan")
    jobroles = relationship("JobRole", back_populates="org", cascade="all, delete-orphan")
