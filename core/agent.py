from typing import Any, Union
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from llm import model_selector

class AgentTask(BaseModel):
    """Structured communication payload between agents."""
    instruction: str
    context: dict[str, Any] = {}

class Agent:
    def __init__(self, name: str, scope: str, llm: ChatGoogleGenerativeAI | None = None):
        self.name = name
        self.scope = scope
       
        selected_llm, prompt = model_selector(scope)
       
        self.llm = llm or selected_llm
        self.prompt = prompt

    def run(self, input_data: Union[str, AgentTask]) -> str:
        # If the input is a task from another agent, format it.
        if isinstance(input_data, AgentTask):
            content = f"Task: {input_data.instruction}\n\nContext:\n{input_data.context}"
        else:
            # Direct human input
            content = input_data

        response = self.llm.invoke([
            SystemMessage(content=self.prompt),
            HumanMessage(content=content),
        ])

        return response.content

class PlannerAgent(Agent):
    """Example of an orchestrator that triggers sub-agents using Tasks."""
    def __init__(self, name: str = "Planner", llm: ChatGoogleGenerativeAI | None = None):
        super().__init__(name, "planning", llm)
        self.sub_agents: dict[str, Agent] = {}

    def get_or_create_subagent(self, name: str, scope:str) -> Agent:
        if scope not in self.sub_agents:
            self.sub_agents[scope] = Agent(name=name, scope=scope)
        return self.sub_agents[scope]

    def delegate(self, scope: str, instruction: str, context: dict = None) -> str:
        """Sends a typed AgentTask to a sub-agent."""
        agent = self.get_or_create_subagent(scope)
        task = AgentTask(instruction=instruction, context=context or {})
        return agent.run(task)

