from typing import TypedDict

from assistant.agents.planner import run_planner
from assistant.agents.recommender import run_recommender
from assistant.agents.verifier import run_verifier
from assistant.agents.weather_data import run_weather_data_agent
from assistant.models.state import AssistantState

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:  # pragma: no cover - fallback until langgraph is installed
    END = START = StateGraph = None


class WorkflowState(TypedDict):
    state: AssistantState


async def _planner_node(workflow_state: WorkflowState) -> WorkflowState:
    return {"state": await run_planner(workflow_state["state"])}


async def _weather_data_node(workflow_state: WorkflowState) -> WorkflowState:
    return {"state": await run_weather_data_agent(workflow_state["state"])}


def _verifier_node(workflow_state: WorkflowState) -> WorkflowState:
    return {"state": run_verifier(workflow_state["state"])}


async def _recommender_node(workflow_state: WorkflowState) -> WorkflowState:
    return {"state": await run_recommender(workflow_state["state"])}


def _build_workflow():
    if StateGraph is None:
        return None

    graph = StateGraph(WorkflowState)
    graph.add_node("planner", _planner_node)
    graph.add_node("weather_data", _weather_data_node)
    graph.add_node("verifier", _verifier_node)
    graph.add_node("recommender", _recommender_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "weather_data")
    graph.add_edge("weather_data", "verifier")
    graph.add_edge("verifier", "recommender")
    graph.add_edge("recommender", END)
    return graph.compile()


WORKFLOW_APP = _build_workflow()


async def run_workflow(state: AssistantState) -> AssistantState:
    if WORKFLOW_APP is None:
        state = await run_planner(state)
        state = await run_weather_data_agent(state)
        state = run_verifier(state)
        state = await run_recommender(state)
        return state

    result = await WORKFLOW_APP.ainvoke({"state": state})
    return result["state"]