from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from assistant.settings import get_settings

mcp = FastMCP("weather")
settings = get_settings()

WEATHER_API_BASE = settings.weather_api_base
GEOCODING_API_BASE = settings.geocoding_api_base
USER_AGENT = settings.weather_user_agent
REQUEST_TIMEOUT = settings.weather_timeout_seconds
QWEATHER_API_HOST = settings.qweather_api_host.rstrip("/")
QWEATHER_API_TOKEN = settings.qweather_api_token


async def make_request(url: str, params: dict[str, Any]) -> dict[str, Any] | None:
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


async def make_request_with_headers(
    url: str, params: dict[str, Any], headers: dict[str, str]
) -> dict[str, Any] | None:
    merged_headers = {"User-Agent": USER_AGENT, **headers}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url,
                params=params,
                headers=merged_headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


@mcp.tool()
async def geocode_location(location: str) -> str:
    """根据中国城市名称获取经纬度和省份信息。"""
    data = await make_request(
        f"{GEOCODING_API_BASE}/search",
        {
            "name": location,
            "count": 1,
            "language": "zh",
            "format": "json",
            "countryCode": "CN",
        },
    )

    results = (data or {}).get("results") or []
    if not results:
        return "未找到该中国城市的位置坐标。"

    item = results[0]
    province = item.get("admin1") or ""
    return (
        f"城市: {item.get('name', location)}\n"
        f"省份: {province}\n"
        f"纬度: {item.get('latitude')}\n"
        f"经度: {item.get('longitude')}"
    )


async def resolve_location_data(location: str) -> dict[str, Any] | None:
    data = await make_request(
        f"{GEOCODING_API_BASE}/search",
        {
            "name": location,
            "count": 1,
            "language": "zh",
            "format": "json",
            "countryCode": "CN",
        },
    )
    results = (data or {}).get("results") or []
    return results[0] if results else None


@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """获取中国城市的天气预报。"""
    data = await make_request(
        f"{WEATHER_API_BASE}/forecast",
        {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": "Asia/Shanghai",
            "forecast_days": 3,
            "current": [
                "temperature_2m",
                "apparent_temperature",
                "precipitation",
                "wind_speed_10m",
                "weather_code",
            ],
            "daily": [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
                "wind_speed_10m_max",
            ],
        },
    )
    if not data:
        return "无法获取该地点的天气预报。"

    current = data.get("current", {})
    daily = data.get("daily", {})
    days = daily.get("time", [])
    lines = [
        "当前天气:",
        f"温度: {current.get('temperature_2m', '未知')}°C",
        f"体感温度: {current.get('apparent_temperature', '未知')}°C",
        f"降水: {current.get('precipitation', '未知')} mm",
        f"风速: {current.get('wind_speed_10m', '未知')} km/h",
        f"天气代码: {current.get('weather_code', '未知')}",
        "",
        "未来三天天气:",
    ]

    for index, day in enumerate(days[:3]):
        temp_max = daily.get("temperature_2m_max", [None])[index]
        temp_min = daily.get("temperature_2m_min", [None])[index]
        precip = daily.get("precipitation_probability_max", [None])[index]
        wind = daily.get("wind_speed_10m_max", [None])[index]
        code = daily.get("weather_code", [None])[index]
        lines.extend(
            [
                f"{day}:",
                f"最高温: {temp_max}°C",
                f"最低温: {temp_min}°C",
                f"最大降水概率: {precip}%",
                f"最大风速: {wind} km/h",
                f"天气代码: {code}",
                "",
            ]
        )

    return "\n".join(lines).strip()


@mcp.tool()
async def get_alerts(location: str) -> str:
    """获取中国城市的天气预警信息。"""
    if not QWEATHER_API_HOST or not QWEATHER_API_TOKEN:
        return (
            f"{location} 暂未配置中国天气预警源。"
            "请在环境变量中设置 QWEATHER_API_HOST 和 QWEATHER_API_TOKEN。"
        )

    resolved = await resolve_location_data(location)
    if not resolved:
        return f"未找到 {location} 的坐标信息，无法查询天气预警。"

    latitude = resolved.get("latitude")
    longitude = resolved.get("longitude")
    if latitude is None or longitude is None:
        return f"{location} 的坐标信息不完整，无法查询天气预警。"

    data = await make_request_with_headers(
        f"{QWEATHER_API_HOST}/v7/warning/now",
        {
            "location": f"{longitude},{latitude}",
            "lang": "zh",
        },
        {
            "Authorization": f"Bearer {QWEATHER_API_TOKEN}",
        },
    )
    if not data:
        return f"无法获取 {location} 的天气预警信息。"

    warnings = data.get("warning") or []
    if not warnings:
        return f"{location} 当前没有生效中的天气预警。"

    lines = [f"{location} 当前天气预警:"]
    for item in warnings:
        lines.extend(
            [
                f"标题: {item.get('title', '未知')}",
                f"级别: {item.get('severity', '未知')}",
                f"类型: {item.get('typeName', '未知')}",
                f"发布时间: {item.get('pubTime', '未知')}",
                f"发布单位: {item.get('sender', '未知')}",
                f"状态: {item.get('status', '未知')}",
                f"内容: {item.get('text', '无详细内容')}",
                "---",
            ]
        )
    return "\n".join(lines[:-1])


@mcp.tool()
async def get_air_quality(latitude: float, longitude: float) -> str:
    """获取空气质量和紫外线信息。"""
    data = await make_request(
        "https://air-quality-api.open-meteo.com/v1/air-quality",
        {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": "Asia/Shanghai",
            "current": [
                "pm2_5",
                "pm10",
                "european_aqi",
                "uv_index",
            ],
        },
    )
    if not data:
        return "无法获取空气质量数据。"

    current = data.get("current", {})
    return (
        "当前空气质量:\n"
        f"PM2.5: {current.get('pm2_5', '未知')} μg/m³\n"
        f"PM10: {current.get('pm10', '未知')} μg/m³\n"
        f"欧洲空气质量指数: {current.get('european_aqi', '未知')}\n"
        f"紫外线指数: {current.get('uv_index', '未知')}"
    )


@mcp.tool()
async def get_life_advice(latitude: float, longitude: float) -> str:
    """根据天气给出简要生活建议。"""
    data = await make_request(
        f"{WEATHER_API_BASE}/forecast",
        {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": "Asia/Shanghai",
            "current": [
                "temperature_2m",
                "precipitation",
                "wind_speed_10m",
            ],
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
            ],
            "forecast_days": 1,
        },
    )
    if not data:
        return "无法生成生活建议。"

    current = data.get("current", {})
    daily = data.get("daily", {})
    temp = current.get("temperature_2m")
    wind = current.get("wind_speed_10m")
    precip = (daily.get("precipitation_probability_max") or [None])[0]
    tips: list[str] = []

    if temp is not None:
        if temp >= 30:
            tips.append("天气偏热，建议穿轻薄透气衣物并注意补水。")
        elif temp <= 10:
            tips.append("天气偏凉，建议增加外套并注意保暖。")
        else:
            tips.append("体感较舒适，适合日常出行。")

    if precip is not None:
        if precip >= 60:
            tips.append("降水概率较高，建议随身携带雨具。")
        elif precip <= 20:
            tips.append("降水概率较低，户外活动压力不大。")

    if wind is not None and wind >= 20:
        tips.append("风速偏大，骑行和长时间户外活动需谨慎。")

    return "\n".join(tips) if tips else "当前暂无明确生活建议。"


def main() -> None:
    print("中国天气服务 MCP 服务器启动成功")
    print("可用功能: geocode_location, get_forecast, get_alerts, get_air_quality, get_life_advice")
    print("服务已就绪，等待连接...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
