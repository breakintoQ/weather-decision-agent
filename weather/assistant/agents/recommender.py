import re
from dataclasses import replace

from assistant.models.state import AssistantState, FinalAnswer
from assistant.tools.openai_client import OpenAIClient, OpenAIError


def _extract_temperature_values(forecast_text: str) -> list[int]:
    return [int(match) for match in re.findall(r"温度: ?(-?\d+)", forecast_text)]


def _extract_float(label: str, text: str) -> float | None:
    match = re.search(rf"{re.escape(label)}: ?(-?\d+(?:\.\d+)?)", text)
    return float(match.group(1)) if match else None


def _infer_risk_level(state: AssistantState) -> str:
    forecast_text = (state.tool_results.forecast or "").lower()
    air_quality_text = state.tool_results.air_quality or ""
    aqi = _extract_float("欧洲空气质量指数", air_quality_text)
    uv_index = _extract_float("紫外线指数", air_quality_text)

    if any(keyword in forecast_text for keyword in ["天气代码: 95", "天气代码: 96", "天气代码: 99"]):
        return "high"
    if aqi is not None and aqi >= 80:
        return "high"
    if any(keyword in forecast_text for keyword in ["降水", "风速", "最大降水概率"]):
        return "medium"
    if aqi is not None and aqi >= 40:
        return "medium"
    if uv_index is not None and uv_index >= 6:
        return "medium"
    return "low"


def _build_rule_tips(state: AssistantState, temperatures: list[int]) -> tuple[str, list[str]]:
    activity = state.intent.activity_type
    tips: list[str] = []
    decision = "suitable"

    if temperatures:
        max_temp = max(temperatures)
        min_temp = min(temperatures)
        tips.append(f"温度范围约 {min_temp}°C - {max_temp}°C")
        if max_temp >= 35:
            decision = "caution"
            tips.append("气温较高，建议避开午后高温时段")
        if min_temp <= 5:
            decision = "caution"
            tips.append("气温较低，建议做好保暖")

    forecast_text = state.tool_results.forecast or ""
    if "最大降水概率" in forecast_text:
        tips.append("请留意降水概率变化，必要时携带雨具")
    if "风速" in forecast_text and activity in {"running", "cycling"}:
        tips.append("建议关注风速变化，适当调整路线和强度")

    air_quality_text = state.tool_results.air_quality or ""
    pm25 = _extract_float("PM2.5", air_quality_text)
    aqi = _extract_float("欧洲空气质量指数", air_quality_text)
    uv_index = _extract_float("紫外线指数", air_quality_text)

    if pm25 is not None:
        tips.append(f"PM2.5 当前约为 {pm25:.1f} μg/m³")
        if pm25 >= 75:
            decision = "caution"
            tips.append("颗粒物浓度较高，敏感人群应减少户外停留")
    if aqi is not None:
        tips.append(f"空气质量指数约为 {aqi:.0f}")
        if aqi >= 80:
            decision = "not_recommended"
            tips.append("空气质量较差，不建议进行高强度户外活动")
        elif aqi >= 40:
            decision = "caution"
            tips.append("空气质量一般，户外活动建议适度控制强度")
    if uv_index is not None and uv_index >= 6:
        tips.append(f"紫外线指数约为 {uv_index:.1f}，午间外出请做好防晒")

    life_advice_text = (state.tool_results.life_advice or "").strip()
    if life_advice_text:
        for line in life_advice_text.splitlines():
            line = line.strip()
            if line and line not in tips:
                tips.append(line)

    if activity == "running":
        tips.append("跑步建议优先选择早晨或傍晚")
    elif activity == "cycling":
        tips.append("骑行前建议确认风速和路面湿滑情况")
    elif activity == "camping":
        tips.append("露营前建议重点关注降水和夜间最低温")
    elif activity == "travel":
        tips.append("出行前建议准备轻便雨具和分层穿搭")

    return decision, tips


async def _llm_recommend(
    state: AssistantState, risk_level: str, rule_tips: list[str]
) -> dict[str, object]:
    client = OpenAIClient()
    if not client.is_configured():
        return {}

    prompt = (
        "你是一个中国天气出行助手。请基于以下信息生成中文建议。"
        f"用户问题: {state.user_query}\n"
        f"地点: {state.intent.location or state.intent.province}\n"
        f"时间: {state.intent.time_range or '未指定'}\n"
        f"活动: {state.intent.activity_type or '未指定'}\n"
        f"天气数据:\n{state.tool_results.forecast or ''}\n"
        f"空气质量数据:\n{state.tool_results.air_quality or ''}\n"
        f"生活建议工具结果:\n{state.tool_results.life_advice or ''}\n"
        f"预警数据:\n{state.tool_results.alerts or ''}\n"
        f"当前规则判断风险等级: {risk_level}\n"
        f"规则提示: {rule_tips}\n"
    )
    schema_hint = (
        '{"summary": "一句中文总结", '
        '"decision": "suitable/caution/not_recommended/clear", '
        '"tips": ["提示1", "提示2"]}'
    )
    return await client.generate_json(prompt=prompt, schema_hint=schema_hint)


async def run_recommender(state: AssistantState) -> AssistantState:
    if state.assessment.missing_fields:
        answer = FinalAnswer(
            summary="信息还不完整，暂时无法生成可靠建议。",
            decision="need_more_context",
            tips=[f"请补充: {', '.join(state.assessment.missing_fields)}"],
        )
        return replace(state, final_answer=answer)

    if state.assessment.tool_errors:
        answer = FinalAnswer(
            summary="天气工具调用失败，暂时无法完成建议生成。",
            decision="tool_error",
            tips=state.assessment.tool_errors,
        )
        return replace(state, final_answer=answer)

    location = state.intent.location or state.intent.province or "目标地区"
    temperatures = _extract_temperature_values(state.tool_results.forecast or "")
    risk_level = _infer_risk_level(state)
    decision, tips = _build_rule_tips(state, temperatures)

    if state.intent.question_type == "alert_check":
        summary = state.tool_results.alerts or f"{location} 当前暂无预警信息。"
        answer = FinalAnswer(summary=summary, decision="clear", tips=tips)
        return replace(state, final_answer=answer)

    try:
        llm_result = await _llm_recommend(state, risk_level, tips)
    except OpenAIError as exc:
        llm_result = {}
        assessment = replace(
            state.assessment,
            llm_errors=[*state.assessment.llm_errors, str(exc)],
        )
        state = replace(state, assessment=assessment)

    summary = llm_result.get("summary") if isinstance(llm_result, dict) else None
    llm_decision = llm_result.get("decision") if isinstance(llm_result, dict) else None
    llm_tips = llm_result.get("tips") if isinstance(llm_result, dict) else None

    if not summary:
        summary = f"{location} 当前可以给出第一版天气与空气质量建议，整体风险等级为 {risk_level}。"
    if not llm_decision:
        llm_decision = decision
    if not isinstance(llm_tips, list) or not llm_tips:
        llm_tips = tips

    answer = FinalAnswer(
        summary=summary,
        decision=str(llm_decision),
        tips=[str(tip) for tip in llm_tips],
    )
    return replace(state, final_answer=answer)
