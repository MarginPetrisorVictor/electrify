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

# Force a clean layout without unnecessary padding, default highlighting, or loud box borders
console = Console(highlight=False)

class SubTasks(BaseModel):
    tasks: List[str] = Field(description="A sequential pipeline list of 2 to 4 independent target execution actions.")


# ==================================================================
# REUSABLE GIT LIFECYCLE & UI HELPERS
# ==================================================================

def _prepare_git_environment(prefix: str) -> str:
    """Handles Phase 1: Minimalist branch creation and context building."""
    console.print(f"[dim]── git › preparing isolated environment[/dim]")
    
    safe_branch_name = f"{prefix}/ai-{int(time.time())}" 
    branch_result = create_and_checkout_branch.invoke({"branch_name": safe_branch_name})
    
    console.print(f"[green]✔[/green] branch active [bold white]{safe_branch_name}[/bold white]")
    return get_git_status.invoke({})


def _display_workspace_diff():
    """Dynamically generates a Git diff for all files modified by the agent."""
    try:
        repo = get_repo()
        
        # Stage files natively so Git recognizes untracked/newly created files in the diff.
        # Using "." strictly respects .gitignore (e.g., skips .egg-info automatically).
        repo.git.add(".")
        
        # Compare staged changes against the baseline HEAD commit
        diff_text = repo.git.diff("--cached")
        
        if not diff_text.strip():
            return
            
        console.print("\n[bold white]› Workspace Modifications:[/bold white]")
        
        # Stream the Git diff through our Claude-style colorizer
        for line in diff_text.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                console.print(f"[green]{line}[/green]")
            elif line.startswith("-") and not line.startswith("---"):
                console.print(f"[red]{line}[/red]")
            elif line.startswith("@@"):
                console.print(f"[cyan]{line}[/cyan]")
            elif line.startswith("---") or line.startswith("+++"):
                console.print(f"[bold white]{line}[/bold white]")
            else:
                console.print(f"[dim]{line}[/dim]")
        console.print()
        
    except Exception as e:
        console.print(f"[dim]› diff generation skipped: {str(e)}[/dim]")


def _ship_git_changes(goal: str, prefix: str, detailed_summary: str) -> dict:
    """Handles Phase 3: Committing and outputting a clean MR section."""
    console.print(f"\n[dim]── git › packaging changes[/dim]")
    
    commit_msg = f"{prefix}: autonomous implementation of '{goal}'"
    commit_result = commit_all_changes.invoke({"message": commit_msg})
    
    console.print(f"[green]✔[/green] changes committed to tracking branch")
    console.print(f"[dim]📈 pushing upstream to remote origin...[/dim]")
    
    mr_title = f"AI {prefix.capitalize()} Implementation: {goal}"
    mr_result = create_merge_request.invoke({
        "title": mr_title,
        "description": f"Automated merge request compiled by Electrify CLI.\n\n### Execution Summary:\n{detailed_summary}"
    })
    
    # Format the MR result cleanly without loud boxes
    console.print("\n[bold white]🚀 Merge Request Created Successfully[/bold white]")
    if "http" in mr_result:
        # Extract link cleanly if present, otherwise print the full tool result
        link = mr_result.split("here: ")[-1] if "here: " in mr_result else mr_result
        console.print(f"  [dim]Review URL:[/dim] [cyan underline]{link.strip()}[/cyan underline]\n")
    else:
        console.print(f"  {mr_result}\n")
        
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
            console.print(f"\n[bold white]› Electrify Node Engine[/bold white] [dim]• patch track[/dim]")
            console.print(f"[dim]Goal:[/dim] {goal}\n")
            
            # Phase 1: Isolated Git Setup
            git_context = _prepare_git_environment(prefix="patch")
            
            enriched_prompt = (
                f"Current Repository Workspace Context:\n{git_context}\n\n"
                f"Target Execution Objective: {goal}"
            )
            
            initial_state = {"messages": [HumanMessage(content=enriched_prompt)]}
            final_ai_reply = ""
            
            # Phase 2: Execution Loop
            for event in coding_graph.stream(initial_state, stream_mode="values"):
                if "messages" in event:
                    last_msg = event["messages"][-1]
                    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                        for tool_call in last_msg.tool_calls:
                            console.print(f"  [dim]⚡ tool ›[/dim] [white]{tool_call['name']}[/white]")
                    elif last_msg.content and last_msg.type == "ai":
                        final_ai_reply = Dispatcher._extract_text_content(last_msg.content)
            
            # Phase 3: Display Summary & Diffs
            if final_ai_reply.strip():
                console.print(f"\n[bold white]› Summary Response[/bold white]")
                console.print(Markdown(final_ai_reply))
            
            _display_workspace_diff()
            
            # Phase 4: Stage, Commit, and MR
            git_results = _ship_git_changes(
                goal=goal, 
                prefix="fix", 
                detailed_summary=f"Atomic changes applied directly:\n{final_ai_reply[:300]}..."
            )
            
            return {"single_code_result": final_ai_reply, **git_results}

        elif action == "parallel_coding":
            console.print(f"\n[bold white]› Electrify Pipeline Module[/bold white] [dim]• feature track[/dim]")
            console.print(f"[dim]Goal:[/dim] {goal}\n")
            
            # Phase 1: Isolated Git Setup
            git_context = _prepare_git_environment(prefix="feature")
            
            console.print("[dim]🧠 computing task topology graph...[/dim]")
            llm, _ = model_selector("planning") 
            structured_planner = llm.with_structured_output(SubTasks)
            plan = structured_planner.invoke(
                f"Project Goal: {goal}\n\nCurrent Repository Workspace Context:\n{git_context}\n\n"
                f"Deconstruct this project workflow into a linear sequence of atomic code writing/modification tasks."
            )
            
            artifacts = {}
            
            # Phase 2: Sequential Workflow Loop
            for i, task in enumerate(plan.tasks, 1):
                console.print(f"\n[bold white]› Task {i}/{len(plan.tasks)}[/bold white] [dim]{task}[/dim]")
                
                initial_state = {"messages": [HumanMessage(content=task)]}
                final_ai_reply = ""
                
                for event in coding_graph.stream(initial_state, stream_mode="values"):
                    if "messages" in event:
                        last_msg = event["messages"][-1]
                        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                            for tool_call in last_msg.tool_calls:
                                console.print(f"  [dim]⚡ tool ›[/dim] [white]{tool_call['name']}[/white]")
                        elif last_msg.type == "ai":
                            final_ai_reply = Dispatcher._extract_text_content(last_msg.content)
                
                artifacts[f"parallel_task_{i}"] = final_ai_reply
            
            # Phase 3: Display Cumulative Diffs
            _display_workspace_diff()
            
            # Phase 4: Stage, Commit, and MR
            summary_list = "\n".join([f"- {t}" for t in plan.tasks])
            git_results = _ship_git_changes(goal=goal, prefix="feat", detailed_summary=summary_list)
            
            return {**artifacts, **git_results}

        else:
            console.print(f"[bold red]✖ routing sequence mismatch: {action}[/bold red]")
            return {}