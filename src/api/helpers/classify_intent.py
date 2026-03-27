import ollama
from enum import Enum

import re

from src.api.helpers.llm_client import chat_completion


class Intent(str, Enum):
    DOCUMENT_QA = "DOCUMENT_QA"
    ACTION = "ACTION"
    GENERAL_QA = "GENERAL_QA"


# Prompt template for intent classification
INTENT_CLASSIFICATION_PROMPT = """
You are a strict intent classifier. Classify the user input into EXACTLY ONE category: GENERAL_QA, or ACTION.

Return ONLY the category name in uppercase. No explanations, no extra words, no punctuation, no emojis.

DEFINITIONS
ACTION: User requests an operation or command, OR is asking for data/status from any of the available agent tools listed below.

GENERAL_QA: General information, explanation, or definition questions not tied to a specific document or command (e.g., "What is a store log?").

AVAILABLE AGENT TOOLS (any query related to these = ACTION)
- Dashboard overview / summary statistics
- Vertex CS status: Central Server Vertex RTE processing status
- CS exceptions: Central Server exception/error logs
- CS daily sync: Central Server daily sync status
- CS file processing: Central Server file processing status
- Store Vertex: Store-level Vertex file processing
- Store exceptions: Store-level exception/error logs
- Store file processing: Store-level file processing status
- Store sales data file: Store sales data file status
- Store file upload: Store file upload status
- File transfer / copy between stores or servers
- Store backup retrieval
- Calendar meetings lookup

DISAMBIGUATION RULES (MANDATORY)
- Any query asking for status, data, counts, errors, exceptions, logs, sync, uploads, or processing results = ACTION.
- Any command verb (fetch, get, show, check, retrieve, download, upload, backup, run, generate, create, delete, copy) = ACTION.
- Confirmation phrases (yes, y, confirm, ok, sure, proceed, go ahead, do it, approved) = ACTION.
- Vague questions like "tell me" or "show me" without a specific tool or operation = GENERAL_QA.
- Hypotheticals or examples (e.g., "What if I ran...?") = GENERAL_QA unless containing a direct command.

USER INPUT:
"{user_input}"

"""


ACTION_HINTS = [
    "get", "copy", "download", "upload", "backup",
    "export", "fetch", "retrieve", "move"
]

QUESTION_HINTS = [
    "what", "where", "how", "why", "when", "who",
    "which", "explain", "describe"
]


def rule_based_intent(user_input: str):
    text = user_input.lower()

    for k in ACTION_HINTS:
        if re.search(rf"\b{k}\b", text):
            return Intent.ACTION

    for k in QUESTION_HINTS:
        if re.search(rf"\b{k}\b", text):
            return Intent.DOCUMENT_QA

    return Intent.GENERAL_QA


def classify_intent(user_input: str) -> Intent:
    if not user_input or not user_input.strip():
        return Intent.GENERAL_QA

    user_input = user_input.strip()

    # 1️⃣ FAST deterministic path
    # rule_intent = rule_based_intent(user_input)
    # if rule_intent != Intent.GENERAL_QA:
    #     return rule_intent

    # 2️⃣ LLM fallback
    try:
        raw = chat_completion(
                system_prompt=INTENT_CLASSIFICATION_PROMPT,
                user_input=user_input.strip(),
            )
        raw = re.sub(r"[^A-Z_]", "", raw)
        print(raw)
        if raw in Intent.__members__:
            return Intent[raw]

    except Exception as e:
        print(f"[IntentClassifier] Error: {e}")
