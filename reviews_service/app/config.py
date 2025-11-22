from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    
    APP_NAME: str = "Reviews Service"
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/smartmeeting"
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_ENV"
    JWT_ALGORITHM: str = "HS256"


settings = Settings()
