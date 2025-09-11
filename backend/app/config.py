from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "companies"

    redis_host: str = "redis"
    redis_port: int = 6379

    opensearch_host: str = "opensearch"
    opensearch_port: int = 9200
    opensearch_user: str = "admin"
    opensearch_password: str = "admin"
    opensearch_use_ssl: bool = False

    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key: str = "minio"
    s3_secret_key: str = "minio123"
    s3_bucket: str = "companies"

    # Origins allowed for CORS
    allowed_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"


def get_settings() -> Settings:
    return Settings()
