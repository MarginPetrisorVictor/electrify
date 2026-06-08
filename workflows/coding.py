import sys
import os
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.llm import model_selector
from tools.file_tools import LOCAL_DEV_TOOLS, get_workspace_context

# 1. State aggregates messages chronologically
class CodingState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# 2. Extract configuration and bind tools
llm, system_prompt = model_selector("coding")
llm_with_tools = llm.bind_tools(LOCAL_DEV_TOOLS)

def call_agent(state: CodingState):
    # INJECTION: Grab the live workspace tree
    workspace_tree = get_workspace_context()
    
    # Dynamically build the system prompt with the live map
    dynamic_prompt = (
        f"{system_prompt}\n\n"
        f"--- CURRENT WORKSPACE STRUCTURE ---\n"
        f"You are operating in this directory tree. Use your tools to read or modify these files:\n"
        f"{workspace_tree}"
    )
    
    messages = [SystemMessage(content=dynamic_prompt)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    
    return {"messages": [response]}

def route_next(state: CodingState):
    last_message = state["messages"][-1]
    # If the model requested functional calls, keep looping
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute_tools"
    return END

# 3. Assemble the updated Graph workflow
workflow = StateGraph(CodingState)

workflow.add_node("agent", call_agent)
workflow.add_node("execute_tools", ToolNode(LOCAL_DEV_TOOLS))

workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    route_next,
    {
        "execute_tools": "execute_tools",
        END: END
    }
)
workflow.add_edge("execute_tools", "agent") 

coding_graph = workflow.compile()