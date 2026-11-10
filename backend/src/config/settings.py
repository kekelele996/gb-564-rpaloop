from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "rpaloop"
    APP_ENV: str = "demo"
    API_PREFIX: str = "/api"
    DB_HOST: str = "db"
    DB_PORT: int = 3306
    DB_NAME: str = "rpaloop"
    DB_USER: str = "rpaloop"
    DB_PASSWORD: str = "rpaloop"
    JWT_SECRET: str = "rpaloop-dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 720
    REDIS_URL: str = "redis://redis:6379/0"
    SEED_DEMO: bool = True
    RATE_LIMIT_PER_MINUTE: int = 240
    RUN_QUOTA_PER_HOUR: int = 60
    ROBOT_NAME: str = "SU-BOT-01"
    SIMULATED_STEP_MAX_MS: int = 40

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
