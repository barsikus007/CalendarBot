from pydantic import PostgresDsn, BaseSettings


class Settings(BaseSettings):
    DEBUG: bool = False
    ADMIN_ID: int
    ADMIN_USERNAME: str
    TELEGRAM_TOKEN: str

    POSTGRES_PASSWORD: str = 'TODO_CHANGE'
    POSTGRES_USER: str = 'postgres'
    POSTGRES_HOST: str = 'postgres'
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = POSTGRES_USER
    DATABASE_URL: PostgresDsn = f'postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@' \
                                f'{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'

    AUTH_URL: str
    WEBAPP_URL: str
    GET_CALENDAR_URL: str
    ELECTIVES_CALENDAR_ID: str
    GIF_IOS12: str
    GIF_IOS14: str
    GIF_GOOGLE: str
    GIF_GUIDE: str
    GIF_GUIDE_ID: str
    GIF_GUIDE_AUTH: str

    class Config:
        case_sensitive = True
        env_file = '.env'


settings = Settings()
