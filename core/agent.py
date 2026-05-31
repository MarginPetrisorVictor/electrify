from llm import model_selector
from langchain_google_genai import ChatGoogleGenerativeAI

class Agent:
    def __init__(self, name: str, scope: str, llm: ChatGoogleGenerativeAI):
        self.name = name
        self.scope = scope
        self.llm = model_selector(scope)
