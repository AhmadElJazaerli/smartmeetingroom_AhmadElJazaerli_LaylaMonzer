from pydantic import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Bookings Service"
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/smartmeeting"
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_ENV"
    JWT_ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"


settings = Settings()
