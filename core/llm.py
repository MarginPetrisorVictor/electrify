import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

def get_base_llm(temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError("GOOGLE_API_KEY is missing from environment variables.")
        
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",  
        temperature=temperature,
        max_retries=3,             
    )
