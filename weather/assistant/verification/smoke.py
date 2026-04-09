import asyncio
import os
from dataclasses import asdict

from assistant.api.app import ahandle_query
from assistant.settings import get_settings
from assistant.tools.openai_client import OpenAIClient, OpenAIError
from assistant.tools.weather_mcp import WeatherMCPClient


async def _verify_settings() -> None:
    print("[1/4] 检查配置层与环境变量加载")
    before = bool(os.getenv("OPENAI_API_KEY"))
    settings = get_settings()
    after = bool(os.getenv("OPENAI_API_KEY"))
    masked = ""
    if settings.openai_api_key:
        masked = f"{settings.openai_api_key[:6]}...{settings.openai_api_key[-4:]}"

    print(f"  os.getenv before settings load: {before}")
    print(f"  os.getenv after settings load: {after}")
    print(f"  settings.openai_api_key loaded: {bool(settings.openai_api_key)}")
    print(f"  masked key preview: {masked or '(empty)'}")


async def _verify_llm() -> None:
    print("[2/4] 检查 LLM 接入")
    client = OpenAIClient()
    if not client.is_configured():
        print("  未配置 OPENAI_API_KEY，跳过 LLM 验证")
        return

    try:
        result = await client.generate_json(
            prompt="请只返回 JSON，给出字段 city=北京, ok=true",
            schema_hint='{"city": "字符串", "ok": true}',
        )
        print(f"  LLM response: {result}")
    except OpenAIError as exc:
        print(f"  LLM 验证失败: {exc}")


async def _verify_mcp_tools() -> None:
    print("[3/4] 检查 MCP 工具连通性")
    client = WeatherMCPClient()
    tools = await client.list_tools()
    expected = {"geocode_location", "get_forecast", "get_alerts"}
    missing = expected.difference(tools)
    if missing:
        raise RuntimeError(f"Missing MCP tools: {sorted(missing)}")
    print(f"  available tools: {tools}")


async def _verify_workflow() -> None:
    print("[4/4] 检查中国天气工作流闭环")
    forecast_state = await ahandle_query("北京明天天气怎么样")
    if not forecast_state.tool_results.forecast:
        raise RuntimeError("Forecast workflow did not produce forecast data.")
    if not forecast_state.tool_results.air_quality:
        raise RuntimeError("Forecast workflow did not produce air quality data.")
    if not forecast_state.tool_results.life_advice:
        raise RuntimeError("Forecast workflow did not produce life advice data.")
    if not forecast_state.final_answer.summary:
        raise RuntimeError("Forecast workflow did not produce a final summary.")

    activity_state = await ahandle_query("上海明天适合跑步吗")
    if not activity_state.tool_results.forecast:
        raise RuntimeError("Activity workflow did not produce forecast data.")
    if not activity_state.tool_results.air_quality:
        raise RuntimeError("Activity workflow did not produce air quality data.")
    if not activity_state.tool_results.life_advice:
        raise RuntimeError("Activity workflow did not produce life advice data.")

    print(
        f"  forecast decision: {forecast_state.final_answer.decision} | "
        f"summary: {forecast_state.final_answer.summary}"
    )
    print(
        f"  activity decision: {activity_state.final_answer.decision} | "
        f"summary: {activity_state.final_answer.summary}"
    )
    air_quality_sample = (activity_state.tool_results.air_quality or "").replace("μg/m³", "ug/m3")
    print(f"  air quality sample: {air_quality_sample}")
    print(f"  life advice sample: {activity_state.tool_results.life_advice}")
    final_answer_preview = str(asdict(activity_state.final_answer)).replace("μg/m³", "ug/m3")
    print(f"  sample final answer: {final_answer_preview}")


async def amain() -> None:
    await _verify_settings()
    await _verify_llm()
    await _verify_mcp_tools()
    await _verify_workflow()
    print("Verification passed.")


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
