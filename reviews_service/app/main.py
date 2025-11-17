from fastapi import FastAPI
from .database import Base, engine
from . import models
from .routers import reviews

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Reviews Service",
    description="Manages room reviews and ratings",
    version="1.0.0"
)

app.include_router(reviews.router)
