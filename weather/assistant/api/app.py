import asyncio

from assistant.graph.workflow import run_workflow
from assistant.memory import WindowMemoryStore
from assistant.models.state import AssistantState

MEMORY_STORE = WindowMemoryStore(window_size=4)


async def ahandle_query(user_query: str, session_id: str = "default") -> AssistantState:
    """Async entrypoint for API and UI integrations."""
    initial_state = AssistantState.create(
        user_query=user_query,
        session_id=session_id,
        memory_window=MEMORY_STORE.get_window(session_id),
    )
    final_state = await run_workflow(initial_state)
    MEMORY_STORE.append(final_state)
    return final_state


def handle_query(user_query: str, session_id: str = "default") -> AssistantState:
    """Sync wrapper for scripts or local demos."""
    return asyncio.run(ahandle_query(user_query, session_id=session_id))


def get_session_memory(session_id: str = "default") -> list[dict]:
    return MEMORY_STORE.export(session_id)


def clear_session_memory(session_id: str = "default") -> None:
    MEMORY_STORE.clear(session_id)