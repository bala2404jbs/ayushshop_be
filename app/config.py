from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/dbname"
    SECRET_KEY: str = "secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Email
    MAIL_USERNAME: str = "balasubramanian@starkintelligencelab.com"
    MAIL_PASSWORD: str = "omhdrebvgtomztls"
    MAIL_FROM: str = "balasubramanian@starkintelligencelab.com"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
