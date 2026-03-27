from langchain_core.tools import tool
import json
import re

from src.api.helpers.llm_client import chat_completion
from src.api.helpers.azure_file_upload import upload_file_to_azure_storage, validate_payload

# Module-level context — set this before invoking the agent
_pending_file = None       # raw bytes
_pending_filename = None   # original filename
_pending_share_name = None # azure share name


def set_upload_context(file_bytes: bytes, filename: str, share_name: str):
    """Call this before agent.invoke() to inject the uploaded file into the tool."""
    global _pending_file, _pending_filename, _pending_share_name
    _pending_file = file_bytes
    _pending_filename = filename
    _pending_share_name = share_name


def clear_upload_context():
    global _pending_file, _pending_filename, _pending_share_name
    _pending_file = None
    _pending_filename = None
    _pending_share_name = None


EXTRACT_PROMPT = """
You are a strict information extraction agent.

Extract Azure File Storage information from the user input.

OUTPUT RULES (MANDATORY):
- Return ONLY valid JSON
- No explanations
- No markdown
- No extra text
- Do not invent values
- Use null for missing fields

JSON SCHEMA (MUST MATCH EXACTLY):
{
  "storage_name": string | null,
  "folder_name": string | null,
  "store_numbers": number[] | []
}

EXTRACTION RULES:
- storage_name: Azure File Share name mentioned after words like "to"
- folder_name: Folder name mentioned after phrases like "inside folder", "in folder"
- store_numbers: All numeric store IDs mentioned (comma or space separated)
- Store numbers must be integers
- If a value is not explicitly mentioned, return null (or [] for store_numbers)

USER INPUT:
{user_input}
"""


@tool
def upload_file(input: str) -> str:
    """
    Use this tool when the user wants to upload a file to Azure File Storage.
    It extracts the target share name, folder, and store numbers from the user query,
    then uploads the pending file to the specified Azure File Share location.
    Requires a file to have been attached to the request.
    """
    if _pending_file is None:
        return "No file was uploaded. Please attach a file to upload."

    prompt = EXTRACT_PROMPT.format(user_input=input.strip())

    try:
        content = chat_completion(
            system_prompt=prompt,
            user_input=input.strip()
        )
        print(f"Extracted upload params: {content}")
        rs = json.loads(content)
        validate_payload(rs)
    except Exception as e:
        return f"Failed to extract upload parameters: {e}"

    # Build a minimal file-like object compatible with upload_file_to_azure_storage
    class _FileWrapper:
        def __init__(self, content: bytes, name: str):
            import io
            self.filename = name
            self.file = io.BytesIO(content)

    share_name = _pending_share_name or ""
    if not share_name:
        return "Could not determine the Azure File Share name. Please specify it in your request."

    folder_names = [rs["folder_name"]] if rs.get("folder_name") else []
    store_numbers = rs.get("store_numbers") or []

    result = upload_file_to_azure_storage(
        share_name=share_name,
        folder_names=folder_names,
        file=_FileWrapper(_pending_file, _pending_filename),
        store_numbers=store_numbers
    )

    clear_upload_context()

    return result
