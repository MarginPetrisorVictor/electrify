import json
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

_CORE_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _CORE_DIR.parent
_ROLES_PATH = _CORE_DIR / "roles.json"
_PROMPTS_DIR = _ROOT_DIR / "prompts"

def _load_roles() -> dict:
    with _ROLES_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)

def _load_prompt(prompt_file: str) -> str:
    prompt_path = _PROMPTS_DIR / prompt_file

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with prompt_path.open("r", encoding="utf-8") as file:
        return file.read()

def _get_base_llm(model_name: str) -> ChatGoogleGenerativeAI:
    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError("GOOGLE_API_KEY is missing from environment variables.")

    return ChatGoogleGenerativeAI(model=model_name, max_retries=3)


def model_selector(scope: str) -> tuple[ChatGoogleGenerativeAI, str]:
    roles = _load_roles()
    scope_config = roles.get("scopes").get(scope)

    if not scope_config:
        raise KeyError(f"Unknown scope: {scope}")

    model = scope_config.get("model")
    prompt_file = scope_config.get("prompt_file")

    if not model:
        raise KeyError(f"Scope '{scope}' is missing a model")

    if not prompt_file:
        raise KeyError(f"Scope '{scope}' is missing a prompt_file")

    llm = _get_base_llm(model)
    prompt = _load_prompt(prompt_file)

    return llm, prompt