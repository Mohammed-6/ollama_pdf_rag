# llm_client.py

import os
import ollama
from openai import AzureOpenAI, OpenAI
import openai
from ..config import settings

client = AzureOpenAI(
    api_key=os.getenv("AZURE_API_KEY"),
    azure_endpoint=os.getenv("AZURE_API_BASE"),
    api_version="2024-05-01-preview" # Use a supported API version
)

openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


def chat_completion(system_prompt: str, user_input: str) -> str:
    if settings.LLM_PROVIDER == "ollama":
        return _ollama_chat(system_prompt, user_input)

    if settings.LLM_PROVIDER == "openai":
        return _openai_chat(system_prompt, user_input)

    raise ValueError("Unsupported LLM_PROVIDER")


def _ollama_chat(system_prompt: str, user_input: str) -> str:
    response = ollama.chat(
        model=settings.OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input.strip()},
        ],
        options=settings.OLLAMA_OPTIONS,
        stream=False,
    )

    return response["message"]["content"]

def _openai_chat(system_prompt: str, user_input: str) -> str:
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,  # Azure deployment name
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input.strip()},
        ],
        temperature=0,      # REQUIRED for intent classification
        # max_tokens=20,
    )
    # print(f"OpenAI raw response: {response.choices[0].message.content}")
    return response.choices[0].message.content
