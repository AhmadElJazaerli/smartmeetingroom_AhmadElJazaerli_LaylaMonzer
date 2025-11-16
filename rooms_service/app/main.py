from fastapi import FastAPI
from .database import Base, engine
from . import models
from .routers import rooms

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Rooms Service",
    description="Manages meeting room details and availability",
    version="1.0.0"
)

app.include_router(rooms.router)
