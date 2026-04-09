import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_dotenv(dotenv_path: Path | None = None) -> None:
    path = dotenv_path or (_project_root() / ".env")
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    app_env: str
    weather_api_base: str
    geocoding_api_base: str
    weather_user_agent: str
    weather_timeout_seconds: float
    qweather_api_host: str
    qweather_api_token: str
    mcp_transport: str
    mcp_server_command: str
    mcp_server_script: str
    openai_api_key: str
    openai_model: str
    openai_base_url: str
    openai_timeout_seconds: float


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_dotenv()
    project_root = _project_root()

    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        weather_api_base=os.getenv("WEATHER_API_BASE", "https://api.open-meteo.com/v1"),
        geocoding_api_base=os.getenv(
            "GEOCODING_API_BASE", "https://geocoding-api.open-meteo.com/v1"
        ),
        weather_user_agent=os.getenv("WEATHER_USER_AGENT", "weather-agent/1.0"),
        weather_timeout_seconds=float(os.getenv("WEATHER_TIMEOUT_SECONDS", "30")),
        qweather_api_host=os.getenv("QWEATHER_API_HOST", ""),
        qweather_api_token=os.getenv("QWEATHER_API_TOKEN", ""),
        mcp_transport=os.getenv("WEATHER_MCP_TRANSPORT", "stdio"),
        mcp_server_command=os.getenv(
            "WEATHER_MCP_SERVER_COMMAND",
            os.getenv("PYTHON", os.getenv("PYTHON_EXECUTABLE", sys.executable)),
        ),
        mcp_server_script=os.getenv(
            "WEATHER_MCP_SERVER_SCRIPT",
            str(project_root / "weather.py"),
        ),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.1"),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://yunwu.ai/v1"),
        openai_timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60")),
    )
