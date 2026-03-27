# tools/file_transfer_tool.py
import logging

from langchain_core.tools import tool
import shutil
import os
from dotenv import load_dotenv
from azure.storage.fileshare import ShareFileClient

load_dotenv()

@tool
def transfer_file(query_input: str) -> str:
    """
    Handles natural language commands to move or copy files.
    Parses layman English input to extract source path, destination, and optional file name.
    """
    try:
        import json
        import re

        if not query_input or not query_input.strip():
            return "Error: Empty input received. Please provide a valid command."

        # Normalize input to lowercase for parsing
        input_lower = query_input.lower()

        # Attempt to extract source path using regex for windows paths or unix paths
        source_match = re.search(r'(?:from|source|file|location)\s*[:=]?\s*["\']?([a-zA-Z]:[\\/][^ "\']+|\/[^ "\']+)["\']?', input_lower)
        if not source_match:
            # Try to find any path pattern in input as fallback
            source_match = re.search(r'([a-zA-Z]:[\\/][^ "\']+|\/[^ "\']+)', input_lower)
        if not source_match:
            return "Error: Could not find source file path in the input."

        source_path = source_match.group(1)

        # Attempt to extract destination
        # Look for keywords like 'to azure', 'to <folder>'
        dest_match = re.search(r'to\s+([a-zA-Z0-9_\\/:.-]+)', input_lower)
        if not dest_match:
            return "Error: Could not find destination in the input."

        destination_raw = dest_match.group(1)

        # Determine if destination is azure or local folder
        if 'azure' in destination_raw:
            destination = 'azure'
            # Optionally extract folder name after azure
            folder_match = re.search(r'azure\s+([a-zA-Z0-9_\\/:.-]+)', input_lower)
            folder_name = folder_match.group(1) if folder_match else None
        else:
            destination = destination_raw
            folder_name = None

        # Attempt to extract file name if specified
        file_name_match = re.search(r'(?:as|named|called|rename to)\s+([a-zA-Z0-9_.-]+)', input_lower)
        if file_name_match:
            file_name = file_name_match.group(1)
        else:
            file_name = os.path.basename(source_path)

        # Validate source path exists
        if not os.path.exists(source_path):
            return f"File not found: {source_path}"

        # Upload to Azure File Share
        
        status_lines = []  # Collect status lines for feedback

        class ListHandler(logging.Handler):
            def emit(self, record):
                status_lines.append(self.format(record))

        if destination == "azure":
            conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            share_name = os.getenv("AZURE_STORAGE_SHARE_NAME")
            file_path_prefix = os.getenv("AZURE_STORAGE_FILE_PATH_PREFIX", "RehanTest")
            with open(source_path, "rb") as f:
                file_path = f"{file_path_prefix}/{file_name}"
                if folder_name:
                    file_path = f"{file_path_prefix}/{folder_name}/{file_name}"
                file_client = ShareFileClient.from_connection_string(
                    conn_str=conn_str,
                    share_name=share_name,
                    file_path=file_path
                )
                file_client.upload_file(f)
                handler = ListHandler()
                logging.getLogger("azure.core.pipeline.policies.http_logging_policy").addHandler(handler)
                print(status_lines)

            return "\n".join(status_lines) if status_lines else f"✅ File '{file_name}' successfully moved to Azure File Share."

        # Move to local folder
        else:
            shutil.move(source_path, os.path.join(destination, file_name))
            return f"✅ File '{file_name}' moved to {destination}"

    except json.JSONDecodeError:
        return "Error: Invalid JSON input. Please provide a valid JSON string."
    except Exception as e:
        return f"File transfer failed: {str(e)}"

@tool
def transfer_file1(query: str) -> str:
    """Transfer a file to Azure storage."""
    return "File transferred successfully"

@tool
def search_logs(query: str) -> str:
    """Search logs for errors."""
    return "Not Found log results"

@tool
def get_store_backup(store_id: str) -> str:
    """Get backup of store database."""
    return f"Backup retrieved for store {store_id}"