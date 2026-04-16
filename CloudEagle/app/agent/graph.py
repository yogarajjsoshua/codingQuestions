import structlog
from langgraph.graph import StateGraph, END
from app.models.graph_state import CountryInfoState
from app.agent.nodes.intent_identifier import intent_identifier_node
from app.agent.nodes.tool_invocation import tool_invocation_node
from app.agent.nodes.answer_synthesis import answer_synthesis_node
from app.agent.nodes.response_judge import response_judge_node

logger = structlog.get_logger()


def create_country_info_graph():
    """
    Create and compile the LangGraph workflow for country information queries.
    
    The workflow consists of four nodes:
    1. Intent Identifier: Extracts country name and requested fields
    2. Tool Invocation: Calls REST Countries API and extracts data (skipped for out-of-scope)
    3. Answer Synthesis: Formats the data into a natural language answer (for in-scope)
    4. Response Judge: Evaluates and improves out-of-scope responses
    
    Flow for out-of-scope queries:
    intent_identifier → response_judge → END
    
    Flow for in-scope queries:
    intent_identifier → tool_invocation → answer_synthesis → END
    """
    workflow = StateGraph(CountryInfoState)
    
    workflow.add_node("intent_identifier", intent_identifier_node)
    workflow.add_node("tool_invocation", tool_invocation_node)
    workflow.add_node("answer_synthesis", answer_synthesis_node)
    workflow.add_node("response_judge", response_judge_node)
    
    workflow.set_entry_point("intent_identifier")
    
    # Conditional routing based on out_of_scope flag
    def should_continue(state: CountryInfoState) -> str:
        """Route to response_judge if out of scope, to tool invocation if in scope, or END if error."""
        if state.get("error"):
            return END
        if state.get("out_of_scope", False):
            return "response_judge"
        return "tool_invocation"
    
    workflow.add_conditional_edges(
        "intent_identifier",
        should_continue,
        {
            END: END,
            "response_judge": "response_judge",
            "tool_invocation": "tool_invocation"
        }
    )
    
    # After judge, go to END
    workflow.add_edge("response_judge", END)
    
    # Normal flow for in-scope queries
    workflow.add_edge("tool_invocation", "answer_synthesis")
    workflow.add_edge("answer_synthesis", END)
    
    app = workflow.compile()
    
    logger.info("langgraph_workflow_created", nodes=["intent_identifier", "tool_invocation", "answer_synthesis", "response_judge"])
    return app


country_info_graph = create_country_info_graph()
