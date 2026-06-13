import sys
import os
import time
import typer
from rich.console import Console
from langchain_core.messages import ToolMessage
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from google.api_core.exceptions import ResourceExhausted

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.llm import model_selector
from tools import LOCAL_DEV_TOOLS, get_workspace_context

console = Console()

class CodingState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

llm, system_prompt = model_selector("coding")
llm_with_tools = llm.bind_tools(LOCAL_DEV_TOOLS)

llm_with_retry = llm_with_tools.with_retry(
    retry_if_exception_type=(ResourceExhausted,),
    wait_exponential_jitter=True,
    stop_after_attempt=3
)

def call_agent(state: CodingState):
    workspace_tree = get_workspace_context()
    dynamic_prompt = (
        f"{system_prompt}\n\n"
        f"--- AST-PRUNED WORKSPACE STRUCTURE ---\n"
        f"Use tools to modify files. If a command or test suite fails, look at the EXIT CODE, correct your error, and rewrite it!\n"
        f"{workspace_tree}"
    )
    
    messages = [SystemMessage(content=dynamic_prompt)] + state["messages"]
    
    try:
        response = llm_with_tools.invoke(messages)
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            typer.secho("\n⚠️ [Quota Alert] Token windows maxed out. Sleeping 30 seconds...", fg=typer.colors.YELLOW)
            time.sleep(30)
            response = llm_with_tools.invoke(messages)
        else:
            raise e
            
    return {"messages": [response]}

# Node representing Human Verification (HITL Intervention

def human_approval_node(state: CodingState):
    last_msg = state["messages"][-1]
    tool_outputs = []
    
    for tool_call in last_msg.tool_calls:
        t_name = tool_call["name"]
        t_args = tool_call["args"]
        
        if t_name == "execute_command":
            # Clear a clean line and print directly to the standard output stream
            console.print("\n\n[bold red]🛑 [Guardrail Alert] Agent wants to execute local shell script:[/bold red]")
            console.print(f"   [cyan]Command:[/cyan] {t_args.get('command')}")
            
            # Drop an interactive prompt into the terminal
            choice = typer.prompt("Allow execution? (y/n)", default="n")
            console.print() # Just adds a neat spacing line
            
            if choice.lower() != 'y':
                console.print("⛔ [bold red]Command execution rejected by operator.[/bold red]")
                tool_outputs.append(ToolMessage(
                    content="ERROR: Execution aborted by user operator command. Find another way or ask permission again.",
                    tool_call_id=tool_call["id"],
                    name=t_name
                ))
                continue
                
        # If safe or approved, process the tool call
        for tool in LOCAL_DEV_TOOLS:
            if tool.name == t_name:
                res = tool.invoke(t_args)
                tool_outputs.append(ToolMessage(content=str(res), tool_call_id=tool_call["id"], name=t_name))
                
    return {"messages": tool_outputs}

def route_next(state: CodingState):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "human_approval"
    return END

# Reconstruct workflow using the intervention engine
workflow = StateGraph(CodingState)
workflow.add_node("agent", call_agent)
workflow.add_node("human_approval", human_approval_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", route_next, {"human_approval": "human_approval", END: END})
workflow.add_edge("human_approval", "agent")

coding_graph = workflow.compile()