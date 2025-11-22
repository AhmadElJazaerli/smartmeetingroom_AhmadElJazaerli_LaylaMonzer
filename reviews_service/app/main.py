from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from .database import Base, engine
from . import models
from .routers import reviews
import os

app = FastAPI(
    title="Reviews Service",
    description="Manages room reviews and ratings",
    version="1.0.0"
)

# Only create tables if not in test mode
if os.getenv("TESTING") != "1":
    Base.metadata.create_all(bind=engine)

# Add Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(app)

app.include_router(reviews.router)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "reviews"}
