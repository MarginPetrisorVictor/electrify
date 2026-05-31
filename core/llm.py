import os
import json
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI


load_dotenv() # This must be moved

_ROLES_PATH = Path(__file__).with_name("roles.json")


@lru_cache(maxsize=1)
def _load_roles() -> dict:
    with _ROLES_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)

def _get_base_llm(model_name: str) -> ChatGoogleGenerativeAI:
    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError("GOOGLE_API_KEY is missing from environment variables.")

    return ChatGoogleGenerativeAI(
        model=model_name,
        max_retries=3,
    )


def model_selector(scope: str) -> ChatGoogleGenerativeAI:
    roles = _load_roles()
    model_name = roles.get("scopes", {}).get(scope, {}).get("model")

    if not model_name:
        raise KeyError(f"Unknown scope: {scope}")

    return _get_base_llm(model_name)