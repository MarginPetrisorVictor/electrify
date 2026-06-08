import sys
import os

from core.orchestrator import OrchestratorDecision
from workflows.coding import coding_graph, CodingState

class Dispatcher:
    @staticmethod
    def run(decision: OrchestratorDecision) -> dict:
        """
        Executes the required workflow based on the decision action.
        Returns a dictionary representing artifacts to save.
        """
        action = decision.action
        goal = decision.parameters.get("goal", "")

        if action == "chat":
            # No workflow needed for pure chat
            return {}

        elif action == "single_coding":
            print(f"\n[Dispatcher] Spawning a single coding graph for goal: {goal}")
            initial_state = CodingState(
                task_name="SingleTask",
                instruction=goal,
                code="",
                feedback="",
                satisfied=False,
                iterations=0
            )
            final_state = coding_graph.invoke(initial_state)
            
            # Print the resulting code
            print("\n" + "="*40)
            print(f"Goal: {goal}")
            print(final_state.get('code', ''))
            print("="*40 + "\n")
            
            # Return as artifact
            return {"single_code_result": final_state.get('code')}

        elif action == "parallel_coding":
            print(f"\n[Dispatcher] Spawning parallel coding workflows for goal: {goal}")
            # Note: run_parallel_workflow returns a list of dictionaries with task keys
            results = run_parallel_workflow(goal)
            
            artifacts = {}
            for i, res in enumerate(results):
                artifacts[f"parallel_task_{i}_{res['task_name']}"] = res['final_code']
            return artifacts

        else:
            print(f"[Dispatcher] Unknown action requested: {action}")
            return {}
