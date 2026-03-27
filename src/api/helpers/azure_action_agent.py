import logging
import os
from azure.storage.blob import BlobServiceClient
from datetime import datetime
from azure.storage.fileshare import ShareClient


AZURE_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "")

def upload_action_csv_to_blob(
    csv_text: str,
    store_number: str,
):
    """
    Uploads raw CSV text directly to Azure File Share Storage.
    Checks if store_number folder exists under share 'xeniafileshare1'.
    Aborts with JSON message if folder not found.
    """
    print(csv_text)
    if not csv_text or not csv_text.strip():
        raise ValueError("CSV text is empty")

    if not store_number:
        raise ValueError("store_number is required")

    # Initialize BlobServiceClient for File Shares
    blob_service = BlobServiceClient.from_connection_string(
        AZURE_CONN_STR
    )

    # Use ShareClient directly for file share 'share1'

    share_client = ShareClient.from_connection_string(
        conn_str=AZURE_CONN_STR,
        share_name=os.getenv("AZURE_STORAGE_SHARE_NAME", "")
    )

    # Base folder path inside share
    base_folder = "FileImport"

    # List directories under 'xeniafileshare1'
    try:
        dirs = [item.name for item in share_client.list_directories_and_files(base_folder)]
        print(f"Folders in share 'xeniafileshare1': {dirs}")  # Print folder list
    except Exception as e:
        raise RuntimeError(f"Error listing directories in share: {e}")

    # Check if store_number folder exists
    if store_number not in dirs:
        # Abort with JSON message
        return {
            "status": "ABORTED",
            "message": f"Store folder '{store_number}' not found under '{base_folder}' in share 'xeniafileshare1'."
        }

    # Folder path for upload
    folder_path = f"{base_folder}/{store_number}"

    # Unique filename
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    file_name = f"action_{timestamp}.csv"

    # Get file client for upload
    file_client = share_client.get_file_client(f"{folder_path}/{file_name}")

    # Create a custom handler to capture logs
    log_capture = []

    class ListHandler(logging.Handler):
        def emit(self, record):
            log_capture.append(self.format(record))

    handler = ListHandler()
    logging.getLogger("azure.core.pipeline.policies.http_logging_policy").addHandler(handler)


    # ✅ Capture the response
    csv_bytes = csv_text.encode("utf-8")
    response = file_client.upload_file(csv_bytes,logging_enable=True)  # ← assign to variable

    # ✅ Now you can access headers
    print(f"ETag: {response['etag']}")
    print(f"Last Modified: {response['last_modified']}")
    print(f"Request ID: {response['request_id']}")
    return "<br>".join(log_capture)

    return {
        "response": "UPLOADED",
        "share": "xeniafileshare1",
        "folder_path": folder_path,
        "file_name": file_name,
        "size_bytes": len(csv_bytes),
        "uploaded_at": timestamp,
        
        # ✅ Add response headers to return
        "etag": response.get("etag"),
        "last_modified": str(response.get("last_modified")),
        "request_id": response.get("request_id"),
    }


