from dataclasses import dataclass, field


@dataclass(frozen=True)
class MemoryTurn:
    user_query: str = ""
    assistant_summary: str = ""
    decision: str = ""
    location: str = ""
    province: str = ""
    time_range: str = ""
    activity_type: str = ""
    question_type: str = ""


@dataclass(frozen=True)
class Intent:
    location: str = ""
    latitude: float | None = None
    longitude: float | None = None
    province: str = ""
    time_range: str = ""
    activity_type: str = ""
    question_type: str = ""


@dataclass(frozen=True)
class ExecutionPlan:
    need_geocode: bool = False
    need_forecast: bool = False
    need_air_quality: bool = False
    need_life_advice: bool = False
    need_alerts: bool = False


@dataclass(frozen=True)
class ToolResults:
    geocode: str | None = None
    forecast: str | None = None
    air_quality: str | None = None
    life_advice: str | None = None
    alerts: str | None = None


@dataclass(frozen=True)
class Assessment:
    weather_risk: str = ""
    data_confidence: str = "unknown"
    missing_fields: list[str] = field(default_factory=list)
    tool_errors: list[str] = field(default_factory=list)
    llm_errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FinalAnswer:
    summary: str = ""
    decision: str = ""
    tips: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AssistantState:
    user_query: str
    session_id: str = "default"
    memory_window: list[MemoryTurn] = field(default_factory=list)
    intent: Intent = field(default_factory=Intent)
    execution_plan: ExecutionPlan = field(default_factory=ExecutionPlan)
    tool_results: ToolResults = field(default_factory=ToolResults)
    assessment: Assessment = field(default_factory=Assessment)
    final_answer: FinalAnswer = field(default_factory=FinalAnswer)

    @classmethod
    def create(
        cls,
        user_query: str,
        session_id: str = "default",
        memory_window: list[MemoryTurn] | None = None,
    ) -> "AssistantState":
        return cls(
            user_query=user_query,
            session_id=session_id,
            memory_window=memory_window or [],
        )
