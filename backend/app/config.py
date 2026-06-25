from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    DOCTOR_SECRET_KEY: str = "123456"
    APP_NAME: str = "MediGuard AI"
    DATABASE_URL: str = "sqlite:///./mediguard.db"

    EMAIL_ENABLED: bool = False
    EMAIL_PROVIDER: str = "smtp"

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "MediGuard AI"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()