from collections import defaultdict, deque
from dataclasses import asdict

from assistant.models.state import AssistantState, MemoryTurn


class WindowMemoryStore:
    def __init__(self, window_size: int = 4) -> None:
        self.window_size = window_size
        self._sessions: dict[str, deque[MemoryTurn]] = defaultdict(
            lambda: deque(maxlen=self.window_size)
        )

    def get_window(self, session_id: str) -> list[MemoryTurn]:
        return list(self._sessions[session_id])

    def append(self, state: AssistantState) -> None:
        self._sessions[state.session_id].append(
            MemoryTurn(
                user_query=state.user_query,
                assistant_summary=state.final_answer.summary,
                decision=state.final_answer.decision,
                location=state.intent.location,
                province=state.intent.province,
                time_range=state.intent.time_range,
                activity_type=state.intent.activity_type,
                question_type=state.intent.question_type,
            )
        )

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def export(self, session_id: str) -> list[dict]:
        return [asdict(turn) for turn in self.get_window(session_id)]
