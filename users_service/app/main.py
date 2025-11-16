from fastapi import FastAPI
from .database import Base, engine
from . import models
from .routers import users, auth_routes

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Users Service",
    description="Manages user accounts, roles, and authentication",
    version="1.0.0"
)

app.include_router(auth_routes.router)
app.include_router(users.router)
