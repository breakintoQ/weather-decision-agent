import re
from dataclasses import replace

from assistant.models.state import AssistantState, ToolResults
from assistant.tools.weather_mcp import WeatherMCPClient, WeatherMCPError


GEOCODE_LAT_PATTERN = re.compile(r"纬度: ?(-?\d+(?:\.\d+)?)")
GEOCODE_LON_PATTERN = re.compile(r"经度: ?(-?\d+(?:\.\d+)?)")
GEOCODE_PROVINCE_PATTERN = re.compile(r"省份: ?(.+)")
GEOCODE_CITY_PATTERN = re.compile(r"城市: ?(.+)")


async def run_weather_data_agent(state: AssistantState) -> AssistantState:
    assessment = state.assessment
    tool_results = state.tool_results
    intent = state.intent
    client = WeatherMCPClient()

    if state.execution_plan.need_geocode:
        if not intent.location:
            assessment = replace(
                assessment,
                missing_fields=sorted(set([*assessment.missing_fields, "location"])),
            )
        else:
            try:
                geocode = await client.geocode_location(location=intent.location)
                tool_results = replace(tool_results, geocode=geocode)
                lat_match = GEOCODE_LAT_PATTERN.search(geocode)
                lon_match = GEOCODE_LON_PATTERN.search(geocode)
                province_match = GEOCODE_PROVINCE_PATTERN.search(geocode)
                city_match = GEOCODE_CITY_PATTERN.search(geocode)
                intent = replace(
                    intent,
                    latitude=float(lat_match.group(1)) if lat_match else intent.latitude,
                    longitude=float(lon_match.group(1)) if lon_match else intent.longitude,
                    province=province_match.group(1).strip() if province_match else intent.province,
                    location=city_match.group(1).strip() if city_match else intent.location,
                )
            except WeatherMCPError as exc:
                assessment = replace(
                    assessment,
                    tool_errors=[*assessment.tool_errors, str(exc)],
                )

    if state.execution_plan.need_forecast:
        if intent.latitude is None or intent.longitude is None:
            assessment = replace(
                assessment,
                missing_fields=sorted(set([*assessment.missing_fields, "latitude", "longitude"])),
            )
        else:
            try:
                forecast = await client.get_forecast(
                    latitude=intent.latitude,
                    longitude=intent.longitude,
                )
                tool_results = replace(tool_results, forecast=forecast)
            except WeatherMCPError as exc:
                assessment = replace(
                    assessment,
                    tool_errors=[*assessment.tool_errors, str(exc)],
                )

    if state.execution_plan.need_air_quality:
        if intent.latitude is None or intent.longitude is None:
            assessment = replace(
                assessment,
                missing_fields=sorted(set([*assessment.missing_fields, "latitude", "longitude"])),
            )
        else:
            try:
                air_quality = await client.get_air_quality(
                    latitude=intent.latitude,
                    longitude=intent.longitude,
                )
                tool_results = replace(tool_results, air_quality=air_quality)
            except WeatherMCPError as exc:
                assessment = replace(
                    assessment,
                    tool_errors=[*assessment.tool_errors, str(exc)],
                )

    if state.execution_plan.need_life_advice:
        if intent.latitude is None or intent.longitude is None:
            assessment = replace(
                assessment,
                missing_fields=sorted(set([*assessment.missing_fields, "latitude", "longitude"])),
            )
        else:
            try:
                life_advice = await client.get_life_advice(
                    latitude=intent.latitude,
                    longitude=intent.longitude,
                )
                tool_results = replace(tool_results, life_advice=life_advice)
            except WeatherMCPError as exc:
                assessment = replace(
                    assessment,
                    tool_errors=[*assessment.tool_errors, str(exc)],
                )

    if state.execution_plan.need_alerts:
        target_location = intent.location or intent.province
        if not target_location:
            assessment = replace(
                assessment,
                missing_fields=sorted(set([*assessment.missing_fields, "location"])),
            )
        else:
            try:
                alerts = await client.get_alerts(location=target_location)
                tool_results = replace(tool_results, alerts=alerts)
            except WeatherMCPError as exc:
                assessment = replace(
                    assessment,
                    tool_errors=[*assessment.tool_errors, str(exc)],
                )

    return replace(state, intent=intent, assessment=assessment, tool_results=tool_results)
