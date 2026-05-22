"""
Configuration management for Janakpur Bolts Analytics
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    postgres_db: str = Field(default="bolts_analytics", alias="POSTGRES_DB")
    postgres_user: str = Field(default="bolts_admin", alias="POSTGRES_USER")
    postgres_password: str = Field(default="", alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    
    # Redis
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    
    # Application
    app_port: int = Field(default=8501, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    
    # Data Sources
    cricsheet_base_url: str = Field(default="https://cricsheet.org", alias="CRICSHEET_BASE_URL")
    espncricinfo_base_url: str = Field(default="https://www.espncricinfo.com", alias="ESPNCRICINFO_BASE_URL")
    
    # Scraping
    scrape_delay_min: int = Field(default=1, alias="SCRAPE_DELAY_MIN")
    scrape_delay_max: int = Field(default=3, alias="SCRAPE_DELAY_MAX")
    max_concurrent_requests: int = Field(default=2, alias="MAX_CONCURRENT_REQUESTS")
    user_agent: str = Field(default="BoltsAnalytics/1.0", alias="USER_AGENT")
    
    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def redis_url(self) -> str:
        """Construct Redis connection URL"""
        return f"redis://{self.redis_host}:{self.redis_port}/0"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields not defined in model


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
