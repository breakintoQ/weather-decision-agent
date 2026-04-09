import re
from dataclasses import replace

from assistant.models.state import AssistantState, ExecutionPlan
from assistant.tools.location_resolver import resolve_location, resolve_province
from assistant.tools.openai_client import OpenAIClient, OpenAIError

DECISION_KEYWORDS = ("适合", "能不能", "要不要", "合适吗")
ALERT_KEYWORDS = ("预警", "告警", "警报")
ACTIVITY_KEYWORDS = {
    "running": ("跑步", "慢跑"),
    "cycling": ("骑行", "骑车"),
    "camping": ("露营",),
    "travel": ("出行", "出差", "旅游"),
}


def _extract_coordinates(query: str) -> tuple[float | None, float | None]:
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*[,，]\s*(-?\d+(?:\.\d+)?)", query)
    if not match:
        return None, None
    return float(match.group(1)), float(match.group(2))


def _extract_activity(query: str) -> str:
    for activity, keywords in ACTIVITY_KEYWORDS.items():
        if any(keyword in query for keyword in keywords):
            return activity
    return ""


async def _llm_parse_query(query: str) -> dict[str, str]:
    client = OpenAIClient()
    if not client.is_configured():
        return {}

    schema_hint = (
        '{"location": "城市名或空字符串", '
        '"time_range": "时间描述或空字符串", '
        '"activity_type": "running/cycling/camping/travel/empty", '
        '"question_type": "weather_overview/activity_decision/alert_check"}'
    )
    prompt = f"请解析这句中文天气需求，并提取城市、时间、活动和问题类型：{query}"
    return await client.generate_json(prompt=prompt, schema_hint=schema_hint)


async def run_planner(state: AssistantState) -> AssistantState:
    query = state.user_query.strip()
    question_type = "weather_overview"
    if any(keyword in query for keyword in DECISION_KEYWORDS):
        question_type = "activity_decision"
    elif any(keyword in query for keyword in ALERT_KEYWORDS):
        question_type = "alert_check"

    latitude, longitude = state.intent.latitude, state.intent.longitude
    if latitude is None or longitude is None:
        latitude, longitude = _extract_coordinates(query)

    resolved_location = resolve_location(query)
    location_name = state.intent.location or (resolved_location.canonical_name if resolved_location else "")
    province = state.intent.province or (resolved_location.province if resolved_location else resolve_province(query))
    if resolved_location and (latitude is None or longitude is None):
        latitude = resolved_location.latitude
        longitude = resolved_location.longitude
    activity_type = state.intent.activity_type or _extract_activity(query)
    time_range = state.intent.time_range
    llm_errors = list(state.assessment.llm_errors)

    try:
        llm_result = await _llm_parse_query(query)
    except OpenAIError as exc:
        llm_result = {}
        llm_errors.append(str(exc))

    if llm_result.get("question_type") in {"weather_overview", "activity_decision", "alert_check"}:
        question_type = llm_result["question_type"]
    if llm_result.get("location") and not location_name:
        location_name = llm_result["location"].strip()
    if llm_result.get("activity_type") and not activity_type:
        activity_type = llm_result["activity_type"].strip()
    if llm_result.get("time_range"):
        time_range = llm_result["time_range"].strip()

    plan = ExecutionPlan(
        need_geocode=bool(location_name) and (latitude is None or longitude is None),
        need_forecast=question_type in {"weather_overview", "activity_decision"},
        need_air_quality=question_type in {"weather_overview", "activity_decision"},
        need_life_advice=question_type in {"weather_overview", "activity_decision"},
        need_alerts=question_type == "alert_check",
    )
    intent = replace(
        state.intent,
        location=location_name,
        latitude=latitude,
        longitude=longitude,
        province=province,
        time_range=time_range,
        activity_type=activity_type,
        question_type=question_type,
    )
    assessment = replace(state.assessment, llm_errors=llm_errors)
    return replace(state, intent=intent, execution_plan=plan, assessment=assessment)
