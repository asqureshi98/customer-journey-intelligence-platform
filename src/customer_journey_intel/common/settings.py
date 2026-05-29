from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Local runtime settings loaded from environment variables."""

    kafka_bootstrap_servers: str = Field(default="localhost:19092")
    kafka_topic: str = Field(default="customer-events")
    clickhouse_host: str = Field(default="localhost")
    clickhouse_port: int = Field(default=8123)
    clickhouse_database: str = Field(default="customer_journey")
    clickhouse_user: str = Field(default="cji")
    clickhouse_password: str = Field(default="cji_local_password")
    log_level: str = Field(default="INFO")

    model_config = SettingsConfigDict(
        env_prefix="CUSTOMER_JOURNEY_",
        env_file=".env",
        extra="ignore",
    )
