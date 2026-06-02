import sys
import os
from typing import TypedDict, Annotated
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END

# Ensure imports work when running from the CLI
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import Agent, AgentTask
from langchain_core.messages import SystemMessage, HumanMessage

class CodingState(TypedDict):
    task_name: str
    instruction: str
    code: str
    feedback: str
    satisfied: bool
    iterations: int

class TesterOutput(BaseModel):
    satisfied: bool = Field(description="True if the code completely fulfills the requirements with no issues. False otherwise.")
    feedback: str = Field(description="Constructive feedback for the coder on what to fix, or praise if satisfied.")

def generate_code(state: CodingState):
    print(f"[{state['task_name']}] Iteration {state.get('iterations', 0) + 1}: Generating code...")
    coder = Agent(name=f"Coder_{state['task_name']}", scope="coding")
    
    if state.get("feedback"):
        msg = "Refine the code based on the tester's feedback."
        ctx = {
            "original_instruction": state["instruction"],
            "previous_code": state.get("code", ""),
            "feedback": state["feedback"]
        }
    else:
        msg = state["instruction"]
        ctx = {"step": "initial_implementation"}
        
    code_result = coder.run(AgentTask(instruction=msg, context=ctx))
    
    return {
        "code": code_result,
        "iterations": state.get("iterations", 0) + 1
    }

def test_code(state: CodingState):
    print(f"[{state['task_name']}] Evaluating generated code...")
    tester = Agent(name=f"Tester_{state['task_name']}", scope="testing")
    
    # Force structured output to reliably determine routing
    structured_llm = tester.llm.with_structured_output(TesterOutput)
    
    response = structured_llm.invoke([
        SystemMessage(content=tester.prompt),
        HumanMessage(content=f"Task Instruction: {state['instruction']}\n\nCode to review:\n{state['code']}")
    ])
    
    print(f"[{state['task_name']}] Satisfied: {response.satisfied}. Feedback provided.")
    
    return {
        "feedback": response.feedback,
        "satisfied": response.satisfied
    }

def should_continue(state: CodingState):
    # End if the tester is satisfied or if we hit the maximum iteration limit (e.g., 5 prevents infinite loops)
    if state.get("satisfied", False) or state.get("iterations", 0) >= 5:
        return "end"
    return "generate_code"


# Build the LangGraph workflow
workflow = StateGraph(CodingState)

# Add nodes
workflow.add_node("generate_code", generate_code)
workflow.add_node("test_code", test_code)

# Add edges
workflow.set_entry_point("generate_code")
workflow.add_edge("generate_code", "test_code")
workflow.add_conditional_edges(
    "test_code",
    should_continue,
    {
        "generate_code": "generate_code",
        "end": END
    }
)

coding_graph = workflow.compile()

if __name__ == "__main__":
    # Example execution for a single agent workflow
    initial_state = CodingState(
        task_name="CSV_Parser",
        instruction="Write a robust Python function that parses a CSV string into a list of dictionaries. Handle empty lines and spaces.",
        code="",
        feedback="",
        satisfied=False,
        iterations=0
    )
    
    final_state = coding_graph.invoke(initial_state)
    
    print("\n" + "="*40)
    print("FINAL RESULT")
    print("="*40)
    print(f"Status: {'Success' if final_state['satisfied'] else 'Max Iterations Reached'}")
    print(f"Iterations: {final_state['iterations']}")
    print("-" * 40)
    print(final_state['code'])
