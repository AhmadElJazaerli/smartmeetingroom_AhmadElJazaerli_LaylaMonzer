from pydantic import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Analytics Service"
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/smartmeeting"
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_ENV"
    JWT_ALGORITHM: str = "HS256"
    
    # Service URLs for inter-service communication
    USERS_SERVICE_URL: str = "http://users_service:8000"
    ROOMS_SERVICE_URL: str = "http://rooms_service:8000"
    BOOKINGS_SERVICE_URL: str = "http://bookings_service:8000"
    REVIEWS_SERVICE_URL: str = "http://reviews_service:8000"

    class Config:
        env_file = ".env"


settings = Settings()
