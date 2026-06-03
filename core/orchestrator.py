from typing import Literal, Dict, Any, List
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from core.llm import model_selector

class OrchestratorDecision(BaseModel):
    action: Literal["chat", "single_coding", "parallel_coding"] = Field(
        description="The workflow action to execute based on user request."
    )
    message: str = Field(
        description="Your conversational response to the user. For workflows, this is a brief confirmation."
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted arguments required for the workflow. For coding workflows, please include a 'goal' key."
    )

class OrchestratorAgent:
    def __init__(self):
        llm, prompt = model_selector("orchestrator")
        self.prompt = prompt
        # Force structured output returning OrchestratorDecision
        self.structured_llm = llm.with_structured_output(OrchestratorDecision)

    def decide(self, user_input: str, history: List[Dict[str, Any]] = None) -> OrchestratorDecision:
        messages = [SystemMessage(content=self.prompt)]
        
        # Inject recent history if available
        if history:
            for turn in history:
                if turn.get("role") == "user":
                    messages.append(HumanMessage(content=turn.get("content", "")))
                else:
                    messages.append(AIMessage(content=turn.get("content", "")))
        
        # Finally, append the latest user input
        messages.append(HumanMessage(content=user_input))
        
        # Invoke the structured LLM
        return self.structured_llm.invoke(messages)
