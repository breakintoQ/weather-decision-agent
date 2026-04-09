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
TIME_KEYWORDS = (
    "今天",
    "明天",
    "后天",
    "今晚",
    "明早",
    "明晚",
    "周末",
    "这周末",
    "下周",
    "下午",
    "上午",
    "晚上",
    "早上",
)
LOCATION_FOLLOW_UP_PATTERNS = ("那上海", "那北京", "那广州", "那深圳", "那杭州", "那南京")
TIME_FOLLOW_UP_PATTERNS = ("那今天", "那明天", "那后天", "那周末", "那下午", "那晚上")
ACTIVITY_FOLLOW_UP_PATTERNS = (
    "那适合跑步吗",
    "那适合骑行吗",
    "那适合露营吗",
    "那适合出行吗",
    "那跑步呢",
    "那骑行呢",
    "那露营呢",
)
INDOOR_FOLLOW_UP_PATTERNS = ("那室内呢", "那在室内呢", "那改成室内呢")
RAIN_GEAR_FOLLOW_UP_PATTERNS = ("那要带伞吗", "那需要带伞吗", "那要不要带伞")


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


def _extract_time_range(query: str) -> str:
    matches = [keyword for keyword in TIME_KEYWORDS if keyword in query]
    return " ".join(matches)


def _latest_memory_value(state: AssistantState, field_name: str) -> str:
    for turn in reversed(state.memory_window):
        value = getattr(turn, field_name, "")
        if value:
            return value
    return ""


def _is_follow_up_query(query: str) -> bool:
    follow_up_markers = (
        "那",
        "那么",
        "然后",
        "还有",
        "适合吗",
        "可以吗",
        "怎么样",
        "呢",
    )
    return any(marker in query for marker in follow_up_markers)


def _apply_follow_up_templates(
    state: AssistantState,
    query: str,
    location_name: str,
    province: str,
    activity_type: str,
    time_range: str,
    question_type: str,
) -> tuple[str, str, str, str, str]:
    if any(pattern in query for pattern in LOCATION_FOLLOW_UP_PATTERNS):
        resolved = resolve_location(query)
        if resolved:
            location_name = resolved.canonical_name
            province = resolved.province

    if any(pattern in query for pattern in TIME_FOLLOW_UP_PATTERNS):
        extracted_time = _extract_time_range(query)
        if extracted_time:
            time_range = extracted_time

    if any(pattern in query for pattern in ACTIVITY_FOLLOW_UP_PATTERNS):
        extracted_activity = _extract_activity(query)
        if extracted_activity:
            activity_type = extracted_activity
        question_type = "activity_decision"

    if any(pattern in query for pattern in INDOOR_FOLLOW_UP_PATTERNS):
        activity_type = "indoor"
        question_type = "activity_decision"

    if any(pattern in query for pattern in RAIN_GEAR_FOLLOW_UP_PATTERNS):
        question_type = "weather_overview"

    if _is_follow_up_query(query):
        if not location_name:
            location_name = _latest_memory_value(state, "location")
        if not province:
            province = _latest_memory_value(state, "province")
        if not activity_type:
            activity_type = _latest_memory_value(state, "activity_type")
        if not time_range:
            time_range = _latest_memory_value(state, "time_range")
        if question_type == "weather_overview":
            previous_question_type = _latest_memory_value(state, "question_type")
            if previous_question_type in {
                "weather_overview",
                "activity_decision",
                "alert_check",
            }:
                question_type = previous_question_type

    return location_name, province, activity_type, time_range, question_type


def _memory_context(state: AssistantState) -> str:
    if not state.memory_window:
        return "无历史上下文。"

    lines = []
    for index, turn in enumerate(state.memory_window, start=1):
        lines.append(
            f"{index}. 用户: {turn.user_query} | 助手总结: {turn.assistant_summary} | 决策: {turn.decision}"
        )
    return "\n".join(lines)


async def _llm_parse_query(state: AssistantState, query: str) -> dict[str, str]:
    client = OpenAIClient()
    if not client.is_configured():
        return {}

    schema_hint = (
        '{"location": "城市名或空字符串", '
        '"time_range": "时间描述或空字符串", '
        '"activity_type": "running/cycling/camping/travel/empty", '
        '"question_type": "weather_overview/activity_decision/alert_check"}'
    )
    prompt = (
        "请解析这句中文天气需求，并提取城市、时间、活动和问题类型。\n"
        f"最近对话窗口:\n{_memory_context(state)}\n"
        f"当前用户输入: {query}"
    )
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
    time_range = state.intent.time_range or _extract_time_range(query)
    llm_errors = list(state.assessment.llm_errors)

    try:
        llm_result = await _llm_parse_query(state, query)
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

    (
        location_name,
        province,
        activity_type,
        time_range,
        question_type,
    ) = _apply_follow_up_templates(
        state,
        query,
        location_name,
        province,
        activity_type,
        time_range,
        question_type,
    )

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
