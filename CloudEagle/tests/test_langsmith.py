from dotenv import load_dotenv
import os
from typing import Literal
from langchain.messages import HumanMessage
from langchain_openai import AzureChatOpenAI
from langchain.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, MessagesState
from langsmith import traceable

from app.config import settings
# Load environment variables from .env file
load_dotenv()

# Set the environment variables that AzureChatOpenAI expects
# AzureChatOpenAI looks for these specific environment variable names


@tool
def search(query: str):
    """Call to surf the web."""
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."

tools = [search]
tool_node = ToolNode(tools)

# Use Azure Chat OpenAI with proper configuration
# Note: api_key and azure_endpoint are read from environment variables
model = AzureChatOpenAI(
                    api_key=settings.openai_api_4_key,
                    api_version=settings.openai_api_4_version,
                    azure_endpoint=settings.openai_4_base_url,
                    azure_deployment=settings.open_api_4_engine
                ).bind_tools(tools)

def should_continue(state: MessagesState) -> Literal["tools", "__end__"]:
    messages = state['messages']
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return "__end__"

@traceable(name="call_model", run_type="chain")
def call_model(state: MessagesState):
    messages = state['messages']
    # Invoking `model` will automatically infer the correct tracing context
    response = model.invoke(messages)
    return {"messages": [response]}

workflow = StateGraph(MessagesState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_edge("__start__", "agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
)
workflow.add_edge("tools", 'agent')

app = workflow.compile()


def test_langsmith_tracing():
    """Test LangSmith tracing with Azure OpenAI agent."""
    final_state = app.invoke(
        {"messages": [HumanMessage(content="what is the weather in sf")]},
        config={"configurable": {"thread_id": 42}}
    )
    
    assert final_state is not None
    assert "messages" in final_state
    assert len(final_state["messages"]) > 0
    assert final_state["messages"][-1].content is not None