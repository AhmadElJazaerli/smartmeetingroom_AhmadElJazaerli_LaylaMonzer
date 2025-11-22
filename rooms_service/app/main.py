from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from .database import Base, engine
from . import models
from .routers import rooms
import os

app = FastAPI(
    title="Rooms Service",
    description="Manages meeting room details and availability",
    version="1.0.0"
)

# Only create tables if not in test mode
if os.getenv("TESTING") != "1":
    Base.metadata.create_all(bind=engine)

# Add Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(app)

app.include_router(rooms.router)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "rooms"}
