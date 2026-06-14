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
from tools.git_tools import (
    get_git_status, 
    create_and_checkout_branch, 
    commit_all_changes, 
    create_merge_request
)

console = Console()

class SubTasks(BaseModel):
    tasks: List[str] = Field(description="A sequential pipeline list of 2 to 4 independent target execution actions.")


# ==================================================================
# REUSABLE GIT LIFECYCLE HELPERS
# ==================================================================

def _prepare_git_environment(prefix: str) -> str:
    """Handles Phase 1: Branch creation and initial git status context aggregation."""
    console.print("[yellow]🌲 Aligning repository state and preparing isolation branch...[/yellow]")
    # Generate a unique tracking branch name (e.g., feature/ai-1718355600)
    safe_branch_name = f"{prefix}/ai-{int(time.time())}" 
    branch_result = create_and_checkout_branch.invoke({"branch_name": safe_branch_name})
    console.print(f"🌿 [Git] {branch_result}")
    
    # Return the status context to pass directly to the LLM
    return get_git_status.invoke({})


def _ship_git_changes(goal: str, prefix: str, detailed_summary: str) -> dict:
    """Handles Phase 3: Committing local changes and opening the remote Merge Request."""
    console.print(f"\n[bold green]📦 Code updates finalized. Packaging {prefix} for review...[/bold green]")
    
    # Step A: Register the commit snapshot
    commit_msg = f"{prefix}: autonomous implementation of '{goal}'"
    commit_result = commit_all_changes.invoke({"message": commit_msg})
    console.print(f"💾 [Git] {commit_result}")
    
    # Step B: Push changes upstream and extract the clickable web hyperlink
    console.print("[yellow]🚀 Transporting modifications upstream to origin remote server...[/yellow]")
    mr_title = f"AI {prefix.capitalize()} Implementation: {goal}"
    mr_result = create_merge_request.invoke({
        "title": mr_title,
        "description": f"Automated merge request compiled by Electrify CLI.\n\n### Execution Summary:\n{detailed_summary}"
    })
    
    console.print(f"\n{mr_result}\n")
    return {"merge_request_deployment": mr_result}


# ==================================================================
# MAIN DISPATCHER CLASS
# ==================================================================

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
            
            # Phase 1: Isolated Environment Preparation
            git_context = _prepare_git_environment(prefix="patch")
            
            enriched_prompt = (
                f"Current Repository Workspace Context:\n{git_context}\n\n"
                f"Target Execution Objective: {goal}"
            )
            
            initial_state = {"messages": [HumanMessage(content=enriched_prompt)]}
            final_ai_reply = ""
            
            # Phase 2: Core Coding Execution Loop
            for event in coding_graph.stream(initial_state, stream_mode="values"):
                if "messages" in event:
                    last_msg = event["messages"][-1]
                    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                        for tool_call in last_msg.tool_calls:
                            console.print(f"[bold yellow]⚙️ Invoking Tool:[/bold yellow] [magenta]{tool_call['name']}[/magenta]")
                    elif last_msg.content and last_msg.type == "ai":
                        final_ai_reply = Dispatcher._extract_text_content(last_msg.content)
            
            if final_ai_reply.strip():
                console.print("\n[bold green]⚡ Electrify Agent Response Outline:[/bold green]")
                console.print(Markdown(final_ai_reply))
                console.print("═" * 60)
            
            # Phase 3: Deliver Git Results Upstream
            git_results = _ship_git_changes(
                goal=goal, 
                prefix="fix", 
                detailed_summary=f"Atomic changes applied directly:\n{final_ai_reply[:300]}..."
            )
            
            return {"single_code_result": final_ai_reply, **git_results}

        elif action == "parallel_coding":
            console.print(f"\n[bold magenta]🛠️ [Dispatcher] Spawning Parallel Multi-Task Pipeline Module[/bold magenta]")
            
            # Phase 1: Isolated Environment Preparation
            git_context = _prepare_git_environment(prefix="feature")
            
            # Map structural execution topology using planning models
            console.print("[yellow]🧠 Mapping dependencies and planning task topology...[/yellow]")
            llm, _ = model_selector("planning") 
            structured_planner = llm.with_structured_output(SubTasks)
            plan = structured_planner.invoke(
                f"Project Goal: {goal}\n\nCurrent Repository Workspace Context:\n{git_context}\n\n"
                f"Deconstruct this project workflow into a linear sequence of atomic code writing/modification tasks."
            )
            
            artifacts = {}
            
            # Phase 2: Sequential Coding Execution Loop
            for i, task in enumerate(plan.tasks, 1):
                console.print(f"\n[bold cyan]🚀 [Task Pipeline {i}/{len(plan.tasks)}]:[/bold cyan] {task}")
                
                initial_state = {"messages": [HumanMessage(content=task)]}
                final_ai_reply = ""
                
                for event in coding_graph.stream(initial_state, stream_mode="values"):
                    if "messages" in event:
                        last_msg = event["messages"][-1]
                        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                            for tool_call in last_msg.tool_calls:
                                console.print(f"[bold yellow]⚙️ [Task {i}] Tool Call:[/bold yellow] [cyan]{tool_call['name']}[/cyan]")
                        elif last_msg.type == "ai":
                            final_ai_reply = Dispatcher._extract_text_content(last_msg.content)
                
                artifacts[f"parallel_task_{i}"] = final_ai_reply
            
            # Phase 3: Deliver Git Results Upstream
            summary_list = "\n".join([f"- {t}" for t in plan.tasks])
            git_results = _ship_git_changes(goal=goal, prefix="feat", detailed_summary=summary_list)
            
            return {**artifacts, **git_results}

        else:
            console.print(f"[bold red]❌ Dispatcher routing sequence mismatch for operational action: {action}[/bold red]")
            return {}