import logging
import os
from azure.storage.fileshare import ShareFileClient
from fastapi import UploadFile
from typing import List
import json
import ollama
import re

from src.api.helpers.llm_client import chat_completion

# Azure file storage accounts — credentials loaded from environment
AZURE_FILE_STORAGES = {
    "storage1": {
        "connection_string": os.getenv("AZURE_STORAGE_CONNECTION_STRING", ""),
        "share_name": os.getenv("AZURE_STORAGE_SHARE_NAME", "")
    },
    "storage2": {
        "connection_string": os.getenv("AZURE_STORAGE2_CONNECTION_STRING", ""),
        "share_name": os.getenv("AZURE_STORAGE2_SHARE_NAME", "")
    },
    # Add more storages as needed
}

def extract_upload_parameters(user_input: str, file:bytes, share_name:str) -> dict:
    """
    Uses the Ollama phi3 model to extract storage_name, folder_names, and store_numbers from user input.

    Args:
        user_input (str): The raw user input string.

    Returns:
        dict: {
            "storage_name": str,
            "folder_names": List[str],
            "store_numbers": List[str]
        }
    """
    prompt = """
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

    # print(user_input)
    # print(prompt)
    # response = ollama.chat(
    #     model="codellama",
    #     messages=[
    #         # {"role": "system", "content": SYSTEM_PROMPT},
    #         {"role": "system", "content": prompt},
    #         {
    #             "role": "user",
    #             "content": user_input.strip()
    #         }
    #     ],
    #     options={
    #         "temperature": 0,
    #         "top_p": 1,
    #         "num_predict": 128,
    #         "repeat_penalty": 1.1
    #     },
    #     stream=False,
    # )

    try:
        content = chat_completion(
                system_prompt=prompt,
                user_input=user_input.strip(),
            )
        # content = response["message"]["content"]
        print(f"Ollama response content: {content}")
        rs = json.loads(content)
        if validate_payload(rs):
            result = upload_file_to_azure_storage(
                share_name=share_name,
                folder_names=[rs["folder_name"]] if rs["folder_name"] else [],
                file=file,
                store_numbers=rs["store_numbers"])
        else:
            result = {
                "storage_name": "",
                "folder_names": [],
                "store_numbers": []
            }
    except Exception as e:
        print(f"Error parsing Ollama response: {e}")
        # fallback empty result on parse error
        result = {
            "storage_name": "",
            "folder_names": [],
            "store_numbers": []
        }

    return result

def validate_payload(data: dict):
    # ---- storage_name ----
    storage_name = data.get("storage_name")
    if not isinstance(storage_name, str) or not storage_name.strip():
        raise ValueError("storage_name must be a non-empty string")

    if not re.fullmatch(r"[a-z0-9]{3,63}", storage_name):
        raise ValueError("storage_name must be lowercase alphanumeric (3–63 chars)")

    # ---- store_numbers ----
    store_numbers = data.get("store_numbers")
    if not isinstance(store_numbers, list) or not store_numbers:
        raise ValueError("store_numbers must be a non-empty list")

    if not all(isinstance(n, int) and n > 0 for n in store_numbers):
        raise ValueError("store_numbers must contain positive integers only")

    return True

def upload_file_to_azure_storage(share_name: str, folder_names: list[str], file: UploadFile, store_numbers: List[str]) -> List[str]:
    """
    Uploads the given file to the specified Azure file share and multiple folders.
    The file is saved with names based on store_numbers list.

    Args:
        share_name (str): The Azure file share name.
        folder_names (list[str]): List of folder paths inside the share to upload to.
        file (UploadFile): The file object to upload.
        store_numbers (List[str]): List of store numbers to use in file naming.

    Returns:
        List[str]: List of uploaded file paths in Azure storage.
    """
    # Find storage config by share_name
    storage_config = None
    for config in AZURE_FILE_STORAGES.values():
        if config["share_name"] == share_name:
            storage_config = config
            break

    if not storage_config:
        raise ValueError(f"Share name '{share_name}' not found in configuration.")

    connection_string = storage_config["connection_string"]

    uploaded_paths = []
    status_lines = []  # Collect status lines for feedback

    class ListHandler(logging.Handler):
        def emit(self, record):
            status_lines.append(self.format(record))

    # Read file content once
    file_content = file.file.read()

    for folder_name in folder_names:
        for store_number in store_numbers:
            try:
                # Construct file path inside share including store_number as folder
                file_name = os.path.basename(file.filename)
                file_path = os.path.join(folder_name, str(store_number), file_name).replace("\\", "/")  # Azure uses forward slashes

                # Create ShareFileClient
                file_client = ShareFileClient.from_connection_string(
                    conn_str=connection_string,
                    share_name=share_name,
                    file_path=file_path
                )

                # Upload file content
                file_client.upload_file(file_content)
                handler = ListHandler()
                logging.getLogger("azure.core.pipeline.policies.http_logging_policy").addHandler(handler)
                uploaded_paths.append(file_path)
                # Include full file_client object representation for detailed output
                status_lines.append(f"Success: Uploaded to {file_path}\nFull client info: {repr(file_client)}")
            except Exception as e:
                print(f"Error uploading to {file_path}: {e}")
                status_lines.append(f"Error uploading to {file_path}: {e}")

    # Return both uploaded paths and status lines for detailed feedback
    return "\n".join(status_lines)
