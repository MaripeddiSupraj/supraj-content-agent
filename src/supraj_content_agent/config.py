"""Application configuration loaded only from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SUPRAJ_CONTENT_",
        env_file=".env",
        extra="ignore",
    )

    website_repo: str = "MaripeddiSupraj/SuprajWebsite"
    website_default_branch: str = "main"
    website_blog_path: str = "src/content/blog"
    max_revision_attempts: int = 2
