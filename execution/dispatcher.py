import sys
import os
from rich.console import Console
from rich.markdown import Markdown
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from typing import List

from core.orchestrator import OrchestratorDecision
from workflows.coding import coding_graph
from core.llm import model_selector

console = Console()

# Schema for breaking down large goals into smaller chunks
class SubTasks(BaseModel):
    tasks: List[str] = Field(description="A list of 2 to 4 independent, highly specific coding sub-tasks required to achieve the main goal.")

class Dispatcher:
    @staticmethod
    def _extract_text_content(raw_content) -> str:
        """Safely parses content whether it arrives as a string or a multimodal list of parts."""
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
            console.print(f"\n[bold cyan][Dispatcher] Spawning agent for goal:[/bold cyan] {goal}\n")
            
            initial_state = {"messages": [HumanMessage(content=goal)]}
            final_ai_reply = ""
            
            # Stream the graph live!
            for event in coding_graph.stream(initial_state, stream_mode="values"):
                if "messages" in event:
                    last_msg = event["messages"][-1]
                    
                    # Print tool executions
                    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                        for tool_call in last_msg.tool_calls:
                            console.print(f"[bold yellow]⚙️ Executing Tool:[/bold yellow] {tool_call['name']}")
                            console.print(f"   Args: {tool_call['args']}")
                    
                    # Print the agent's text responses safely
                    elif last_msg.content and last_msg.type == "ai":
                        text_content = Dispatcher._extract_text_content(last_msg.content)
                        if text_content.strip():
                            console.print("\n[bold green]⚡ Electrify Agent:[/bold green]")
                            console.print(Markdown(text_content))
                            console.print("-" * 40)
                            final_ai_reply = text_content
            
            return {"single_code_result": final_ai_reply}

        elif action == "parallel_coding":
            console.print(f"\n[bold magenta][Dispatcher] Initiating Parallel Workflow for goal:[/bold magenta] {goal}\n")
            
            # 1. Break down the overarching goal using your planning model setup
            console.print("[yellow]🧠 Breaking down goal into sequential sub-tasks...[/yellow]")
            llm, _ = model_selector("planning") 
            structured_planner = llm.with_structured_output(SubTasks)
            plan = structured_planner.invoke(f"Break this coding goal down into independent tasks: {goal}")
            
            artifacts = {}
            
            # 2. Loop through and execute each isolated task sequentially
            for i, task in enumerate(plan.tasks, 1):
                console.print(f"\n[bold cyan]🚀 Starting Task {i}/{len(plan.tasks)}:[/bold cyan] {task}")
                
                initial_state = {"messages": [HumanMessage(content=task)]}
                final_ai_reply = ""
                
                for event in coding_graph.stream(initial_state, stream_mode="values"):
                    if "messages" in event:
                        last_msg = event["messages"][-1]
                        
                        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                            for tool_call in last_msg.tool_calls:
                                console.print(f"[bold yellow]⚙️ [Task {i}] Tool:[/bold yellow] {tool_call['name']}")
                        
                        elif last_msg.content and last_msg.type == "ai":
                            final_ai_reply = Dispatcher._extract_text_content(last_msg.content)
                
                # Output final markdown report for each finished subtask block
                if final_ai_reply.strip():
                    console.print(f"\n[bold green]✅ Task {i} Complete:[/bold green]")
                    console.print(Markdown(final_ai_reply))
                    console.print("-" * 40)
                
                artifacts[f"parallel_task_{i}"] = final_ai_reply
                
            return artifacts

        else:
            console.print(f"[red][Dispatcher] Unknown action requested: {action}[/red]")
            return {}