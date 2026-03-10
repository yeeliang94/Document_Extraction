"""Minimal settings for enterprise test app."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Suppress LiteLLM SSL warnings
try:
    import litellm
    litellm.suppress_debug_info = True
except ImportError:
    pass


class Settings(BaseSettings):
    # --- Proxy ---
    llm_proxy_url: str = "https://genai-sharedservice-emea.pwc.com"
    google_api_key: str = ""
    test_model: str = "vertex_ai.gemini-3-flash-preview"

    # --- Paths ---
    upload_dir: Path = Path("data/uploads")
    images_dir: Path = Path("data/images")
    db_path: Path = Path("data/app.db")

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8002

    # --- Pipeline ---
    page_image_dpi: int = 200
    max_output_tokens: int = 4096
    temperature: float = 1.0  # Required for Gemini 3

    # --- Agent ---
    review_agent_enabled: bool = True
    review_agent_max_turns: int = 20

    @property
    def adk_model_name(self) -> str:
        return f"openai/{self.test_model}"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
