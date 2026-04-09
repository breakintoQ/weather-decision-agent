import asyncio

from assistant.graph.workflow import run_workflow
from assistant.models.state import AssistantState


async def ahandle_query(user_query: str) -> AssistantState:
    """Async entrypoint for API and UI integrations."""
    initial_state = AssistantState.create(user_query=user_query)
    return await run_workflow(initial_state)


def handle_query(user_query: str) -> AssistantState:
    """Sync wrapper for scripts or local demos."""
    return asyncio.run(ahandle_query(user_query))
