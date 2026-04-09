from dataclasses import replace

from assistant.models.state import AssistantState


def run_verifier(state: AssistantState) -> AssistantState:
    confidence = "high"
    if state.assessment.missing_fields or state.assessment.tool_errors:
        confidence = "low"
    elif state.assessment.llm_errors:
        confidence = "medium"
    elif state.execution_plan.need_forecast and state.tool_results.forecast is None:
        confidence = "medium"

    risk = state.assessment.weather_risk
    forecast_text = (state.tool_results.forecast or "")
    air_quality_text = (state.tool_results.air_quality or "")
    if any(keyword in forecast_text for keyword in ["最大降水概率", "风速"]):
        risk = "medium"
    if any(keyword in forecast_text for keyword in ["天气代码: 95", "天气代码: 96", "天气代码: 99"]):
        risk = "high"
    if any(keyword in air_quality_text for keyword in ["欧洲空气质量指数: 60", "欧洲空气质量指数: 7", "欧洲空气质量指数: 8", "欧洲空气质量指数: 9"]):
        risk = "high"
    elif "欧洲空气质量指数" in air_quality_text and risk != "high":
        risk = "medium"

    assessment = replace(
        state.assessment,
        data_confidence=confidence,
        weather_risk=risk,
    )
    return replace(state, assessment=assessment)
