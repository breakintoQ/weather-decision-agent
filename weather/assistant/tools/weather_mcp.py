import json
import os
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from assistant.settings import get_settings


class WeatherMCPError(RuntimeError):
    """Raised when MCP weather tool execution fails."""


def _default_server_script() -> Path:
    return Path(get_settings().mcp_server_script)


@dataclass(frozen=True)
class WeatherMCPConfig:
    transport: str = field(default_factory=lambda: get_settings().mcp_transport)
    command: str = field(
        default_factory=lambda: get_settings().mcp_server_command or sys.executable
    )
    args: tuple[str, ...] = field(default_factory=lambda: (str(_default_server_script()),))
    cwd: str = field(default_factory=lambda: str(_default_server_script().parent))
    env: dict[str, str] = field(
        default_factory=lambda: {
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "WEATHER_API_BASE": get_settings().weather_api_base,
            "GEOCODING_API_BASE": get_settings().geocoding_api_base,
            "WEATHER_USER_AGENT": get_settings().weather_user_agent,
            "WEATHER_TIMEOUT_SECONDS": str(get_settings().weather_timeout_seconds),
            "QWEATHER_API_HOST": get_settings().qweather_api_host,
            "QWEATHER_API_TOKEN": get_settings().qweather_api_token,
        }
    )


class WeatherMCPClient:
    def __init__(self, config: WeatherMCPConfig | None = None) -> None:
        self.config = config or WeatherMCPConfig()

    @asynccontextmanager
    async def _session(self):
        if self.config.transport != "stdio":
            raise WeatherMCPError(f"Unsupported MCP transport: {self.config.transport}")

        server = StdioServerParameters(
            command=self.config.command,
            args=list(self.config.args),
            cwd=self.config.cwd,
            env={**os.environ, **self.config.env},
        )
        async with stdio_client(server) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield session

    async def list_tools(self) -> list[str]:
        async with self._session() as session:
            result = await session.list_tools()
            return [tool.name for tool in result.tools]

    async def geocode_location(self, location: str) -> str:
        return await self._call_tool(
            name="geocode_location",
            arguments={"location": location},
        )

    async def get_forecast(self, latitude: float, longitude: float) -> str:
        return await self._call_tool(
            name="get_forecast",
            arguments={"latitude": latitude, "longitude": longitude},
        )

    async def get_alerts(self, location: str) -> str:
        return await self._call_tool(
            name="get_alerts",
            arguments={"location": location},
        )

    async def get_air_quality(self, latitude: float, longitude: float) -> str:
        return await self._call_tool(
            name="get_air_quality",
            arguments={"latitude": latitude, "longitude": longitude},
        )

    async def get_life_advice(self, latitude: float, longitude: float) -> str:
        return await self._call_tool(
            name="get_life_advice",
            arguments={"latitude": latitude, "longitude": longitude},
        )

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        async with self._session() as session:
            available_tools = await session.list_tools()
            tool_names = {tool.name for tool in available_tools.tools}
            if name not in tool_names:
                raise WeatherMCPError(f"MCP tool not found: {name}")

            result = await session.call_tool(name=name, arguments=arguments)
            if result.isError:
                raise WeatherMCPError(self._result_to_text(result))
            return self._result_to_text(result)

    def _result_to_text(self, result: Any) -> str:
        parts: list[str] = []
        for block in result.content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                parts.append(block.text)
                continue
            if block_type == "resource":
                resource = getattr(block, "resource", None)
                resource_text = getattr(resource, "text", None)
                if resource_text:
                    parts.append(resource_text)

        text = "\n".join(part.strip() for part in parts if part.strip()).strip()
        if text:
            return text

        structured = getattr(result, "structuredContent", None)
        if structured is not None:
            return json.dumps(structured, ensure_ascii=False, indent=2)

        raise WeatherMCPError("MCP tool returned an empty result.")
