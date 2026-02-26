from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = "PipeCanary"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql+asyncpg://pipecanary:pipecanary@localhost:5432/pipecanary"
    database_url_sync: str = "postgresql://pipecanary:pipecanary@localhost:5432/pipecanary"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    auth_secret_key: str = "change-me-in-production"
    auth_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_minutes: int = 10080  # 7 days

    # Slack
    slack_webhook_url: str = ""

    # Snowflake defaults
    snowflake_account: str = ""
    snowflake_warehouse: str = ""

    model_config = {"env_prefix": "PIPECANARY_", "env_file": ".env"}


settings = Settings()
