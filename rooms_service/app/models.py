from sqlalchemy import Column, Integer, String, Boolean, Text
from .database import Base


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    capacity = Column(Integer, nullable=False)
    equipment = Column(Text, nullable=True)  # Can store comma-separated list or JSON
    location = Column(String, nullable=False)
    is_available = Column(Boolean, default=True)
    is_out_of_service = Column(Boolean, default=False)
