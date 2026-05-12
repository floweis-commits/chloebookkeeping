"""
Central configuration — reads from environment variables.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/chloe_bookkeeping"

    # JWT
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    refresh_token_expire_days: int = 30

    # QuickBooks
    qbo_client_id: str = ""
    qbo_client_secret: str = ""
    qbo_redirect_uri: str = "http://localhost:8000/api/connectors/quickbooks/callback"
    qbo_environment: str = "sandbox"

    # Shopify
    shopify_api_key: str = ""
    shopify_api_secret: str = ""
    shopify_store_domain: str = ""

    # Supabase (JWT verification)
    supabase_url: str = ""
    supabase_secret_key: str = ""

    # GLM (OpenAI-compatible, used for all AI agents)
    glm_api_key: str = ""
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    glm_model: str = "glm-4.5"

    # Email (Resend)
    resend_api_key: str = ""
    app_url: str = "http://localhost:3000"

    # Storage
    storage_backend: str = "local"
    storage_local_path: str = "./storage"
    max_upload_size_mb: int = 50

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
