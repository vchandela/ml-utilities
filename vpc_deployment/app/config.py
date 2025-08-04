# Configuration module for loading settings from environment variables
# This file provides centralized configuration management for the FastAPI application
# Uses pydantic-settings to automatically load configuration from environment variables
# This makes our application portable and secure, as we don't hardcode sensitive information

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Loads all application settings from environment variables.
    Pydantic will automatically match environment variables to these fields.
    e.g., GCP_PROJECT_ID env var will be loaded into gcp_project_id field.
    """
    # Model configuration
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # GCP Settings
    GCP_PROJECT_ID: str
    GCP_REGION: str

    # Cloud SQL Postgres Settings
    DB_USER: str = "postgres"
    DB_PASSWORD_SECRET_NAME: str # e.g., "pavo-vpc-db-password"
    DB_HOST: str # This will be the Cloud SQL Proxy host (127.0.0.1)
    DB_PORT: int = 5432
    DB_NAME: str = "postgres" # Default DB name
    DB_INSTANCE_CONNECTION_NAME: str # e.g., project:region:instance

    # Memorystore Redis Settings
    REDIS_HOST: str
    REDIS_PORT: int = 6379

    # Pub/Sub Settings
    PUBSUB_TOPIC_NAME: str

    # GCS Settings
    GCS_BUCKET_NAME: str

    # Elasticsearch Settings
    ELASTIC_HOST: str # The full https://... endpoint
    ELASTIC_PASSWORD: str

    @property
    def DATABASE_URL(self) -> str:
        """Constructs the full database URL for SQLAlchemy."""
        # Note: The password is not included here. We will fetch it at runtime.
        # This URL is used by the application connecting to the Cloud SQL Proxy.
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # We will populate this field at runtime after fetching from Secret Manager
    DB_PASSWORD: str = ""

# Create a single, importable instance of the settings
settings = Settings() 