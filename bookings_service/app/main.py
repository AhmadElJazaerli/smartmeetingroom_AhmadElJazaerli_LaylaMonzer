from fastapi import FastAPI
from .database import Base, engine
from . import models
from .routers import bookings

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Bookings Service",
    description="Manages meeting room bookings",
    version="1.0.0"
)

app.include_router(bookings.router)
