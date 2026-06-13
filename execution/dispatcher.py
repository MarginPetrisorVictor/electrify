import sys
import os
import time
from rich.console import Console
from rich.markdown import Markdown
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from typing import List

from core.orchestrator import OrchestratorDecision
from workflows.coding import coding_graph
from core.llm import model_selector

console = Console()

class SubTasks(BaseModel):
    tasks: List[str] = Field(description="A sequential pipeline list of 2 to 4 independent target execution actions.")

class Dispatcher:
    @staticmethod
    def _extract_text_content(raw_content) -> str:
        if isinstance(raw_content, str):
            return raw_content
        elif isinstance(raw_content, list):
            parts = []
            for part in raw_content:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict) and "text" in part:
                    parts.append(part["text"])
            return "".join(parts)
        return ""

    @staticmethod
    def run(decision: OrchestratorDecision) -> dict:
        action = decision.action
        goal = decision.parameters.get("goal", "")

        if action == "chat":
            return {}

        elif action == "single_coding":
            console.print(f"\n[bold cyan]✨ [Dispatcher] Activating Core Agent Node Engine for Goal:[/bold cyan] {goal}\n")
            
            initial_state = {"messages": [HumanMessage(content=goal)]}
            final_ai_reply = ""
            
            # Streaming without console.status context to prevent interactive input hijacking
            for event in coding_graph.stream(initial_state, stream_mode="values"):
                if "messages" in event:
                    last_msg = event["messages"][-1]
                    
                    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                        for tool_call in last_msg.tool_calls:
                            console.print(f"[bold yellow]⚙️ Invoking Tool:[/bold yellow] [magenta]{tool_call['name']}[/magenta] with args: {tool_call['args']}")
                    
                    elif last_msg.content and last_msg.type == "ai":
                        final_ai_reply = Dispatcher._extract_text_content(last_msg.content)
            
            if final_ai_reply.strip():
                console.print("\n[bold green]⚡ Electrify Agent Response Outline:[/bold green]")
                console.print(Markdown(final_ai_reply))
                console.print("═" * 60)
            return {"single_code_result": final_ai_reply}

        elif action == "parallel_coding":
            console.print(f"\n[bold magenta]🛠️ [Dispatcher] Spawning Parallel Multi-Task Pipeline Module[/bold magenta]")
            console.print("[yellow]🧠 Mapping dependencies and planning task topology...[/yellow]")
            
            llm, _ = model_selector("planning") 
            structured_planner = llm.with_structured_output(SubTasks)
            plan = structured_planner.invoke(f"Deconstruct this project workflow into a linear sequence of atomic tasks: {goal}")
            
            artifacts = {}
            
            for i, task in enumerate(plan.tasks, 1):
                console.print(f"\n[bold cyan]🚀 [Task Pipeline {i}/{len(plan.tasks)}]:[/bold cyan] {task}")
                
                initial_state = {"messages": [HumanMessage(content=task)]}
                final_ai_reply = ""
                
                # Continuous, transparent stream logging. Safe for self-healing loops and interactive keyboard inputs.
                for event in coding_graph.stream(initial_state, stream_mode="values"):
                    if "messages" in event:
                        last_msg = event["messages"][-1]
                        
                        if hasattr(last_message:=last_msg, "tool_calls") and last_message.tool_calls:
                            for tool_call in last_message.tool_calls:
                                console.print(f"[bold yellow]⚙️ [Task {i}] Tool Call:[/bold yellow] [cyan]{tool_call['name']}[/cyan]")
                        
                        elif last_msg.content and last_msg.type == "ai":
                            final_ai_reply = Dispatcher._extract_text_content(last_msg.content)
                            if "EXIT CODE: 1" in final_ai_reply or "FAIL" in final_ai_reply.upper():
                                console.print("[bold red]❌ Failure caught in execution. Deploying self-healing patch cycles...[/bold red]")
                
                if final_ai_reply.strip():
                    console.print(f"\n[bold green]✅ Pipeline Step {i} Settled Successfully:[/bold green]")
                    console.print(Markdown(final_ai_reply))
                    console.print("═" * 60)
                
                artifacts[f"parallel_task_{i}"] = final_ai_reply
                
            return artifacts

        else:
            console.print(f"[bold red]❌ Dispatcher routing sequence mismatch for operational action: {action}[/bold red]")
            return {}