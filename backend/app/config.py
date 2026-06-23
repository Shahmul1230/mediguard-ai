from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "MediGuard AI"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    DOCTOR_SECRET_KEY: str = "123456"
    DATABASE_URL: str = "sqlite:///./mediguard.db"

    EMAIL_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = "riyaaan97@gmail.com"
    SMTP_PASSWORD: str = "wejl ljby ahww ivjq"
    SMTP_FROM_EMAIL: str = "riyaaan97@gmail.com"
    SMTP_FROM_NAME: str = "MediGuard AI"

    class Config:
        env_file = ".env"


settings = Settings()