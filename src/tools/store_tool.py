from langchain_core.tools import tool
import requests

from src.tools.dashboard_tool import extract_filters


BASE_DASHBOARD_API = "https://app-itdashboard-test.azurewebsites.net/api"

@tool
def store_vertex(input: str) -> str:
    """
    Use this tool to check store Vertex file processing status.
    It returns information about:
    - Date and location of the store
    - Device name and file details
    - File generated and uploaded timestamps
    - Application source
    - Exception in case of failures
    """
    filters = extract_filters(input)
    print(filters)
    storeId = filters["storeId"]
    startDate = filters["startDate"]
    endDate = filters["endDate"]
    startDateTime = filters["startDateTime"] + ' 00:00:00'
    endDateTime = filters["endDateTime"] + ' 23:59:59'
    timeRange = 4
    print(f"Extracted filters: storeId={storeId}, startDate={startDate}, endDate={endDate}, timeRange={timeRange}")

    api_url = f"{BASE_DASHBOARD_API}/ITCentralServer/storevertex"

    payload = {
        "StoreId": storeId,
        "TimeRange": timeRange,
        "StartDateKey": startDate,
        "EndDateKey": endDate,
        "StartDateTime": startDateTime,
        "EndDateTime": endDateTime
    }
    print(api_url, input, payload)
    response = requests.get(api_url, params=payload, timeout=30)

    data = response.json()

    if not data:
        return "No store Vertex records found."

    result = []

    for item in data:
        summary = f"""
        Date Key: {item['DateKey']}
        Date Time Stamp: {item['DateTimeStamp']}
        Application Source Key: {item['ApplicationSourceKey']}
        Location Key: {item['LocationKey']}
        Device Name: {item['DeviceName']}
        File Name: {item['FileName']}
        File Type: {item['FileType']}
        File Generated Timestamp: {item['FileGeneratedTimeStamp']}
        File Uploaded Timestamp: {item['FileUploadedTimeStamp']}
        Exception: {item['Exception']}
        """
        result.append(summary.strip())

    return "\n\n".join(result)


@tool
def store_exceptions(input: str) -> str:
    """
    Use this tool to check store-level exceptions/errors.
    It returns information about:
    - Store and device that raised the exception
    - Exception date and time
    - Application source of the error
    - Exception message and error code
    - Location key
    """
    filters = extract_filters(input)
    print(filters)
    storeId = filters["storeId"]
    startDate = filters["startDate"]
    endDate = filters["endDate"]
    startDateTime = filters["startDateTime"] + ' 00:00:00'
    endDateTime = filters["endDateTime"] + ' 23:59:59'
    timeRange = 4
    print(f"Extracted filters: storeId={storeId}, startDate={startDate}, endDate={endDate}, timeRange={timeRange}")

    api_url = f"{BASE_DASHBOARD_API}/ITCentralServer/storeexceptions"

    payload = {
        "StoreId": storeId,
        "TimeRange": timeRange,
        "StartDateKey": startDate,
        "EndDateKey": endDate,
        "StartDateTime": startDateTime,
        "EndDateTime": endDateTime
    }
    print(api_url, input, payload)
    response = requests.get(api_url, params=payload, timeout=30)

    data = response.json()

    if not data:
        return "No store exceptions found."

    result = []

    for item in data:
        summary = f"""
        Store ID: {item['StoreId']}
        Device ID: {item['DeviceId']}
        Exception DateTime: {item['ExceptionDateTime']}
        Application Source: {item['ApplicationSource']}
        Exception Message: {item['ExceptionMessage']}
        Error Code: {item['ErrorCode']}
        Location Key: {item['LocationKey']}
        """
        result.append(summary.strip())

    return "\n\n".join(result)


@tool
def store_fileprocessing(input: str) -> str:
    """
    Use this tool to check store-level file processing status.
    It returns information about:
    - File type being processed
    - Total files and success count
    - Last processed date/time
    """
    filters = extract_filters(input)
    print(filters)
    storeId = filters["storeId"]
    startDate = filters["startDate"]
    endDate = filters["endDate"]
    startDateTime = filters["startDateTime"] + ' 00:00:00'
    endDateTime = filters["endDateTime"] + ' 23:59:59'
    timeRange = 4
    print(f"Extracted filters: storeId={storeId}, startDate={startDate}, endDate={endDate}, timeRange={timeRange}")

    api_url = f"{BASE_DASHBOARD_API}/ITCentralServer/storefileprocessing"

    payload = {
        "StoreId": storeId,
        "TimeRange": timeRange,
        "StartDateKey": startDate,
        "EndDateKey": endDate,
        "StartDateTime": startDateTime,
        "EndDateTime": endDateTime
    }
    print(api_url, input, payload)
    response = requests.get(api_url, params=payload, timeout=30)

    data = response.json()

    if not data:
        return "No store file processing records found."

    result = []

    for item in data:
        summary = f"""
        File Type: {item['FileType']}
        Total Files: {item['TotalFiles']}
        Success Count: {item['SuccessCount']}
        Last Processed On: {item['LastProcessedOn']}
        """
        result.append(summary.strip())

    return "\n\n".join(result)


@tool
def store_salesdata_file(input: str) -> str:
    """
    Use this tool to check store sales data file status.
    It returns information about:
    - Date and location of the store
    - Device name and file details
    - File generated and uploaded timestamps
    - Application source
    - Exception in case of failures
    """
    filters = extract_filters(input)
    print(filters)
    storeId = filters["storeId"]
    startDate = filters["startDate"]
    endDate = filters["endDate"]
    startDateTime = filters["startDateTime"] + ' 00:00:00'
    endDateTime = filters["endDateTime"] + ' 23:59:59'
    timeRange = 4
    print(f"Extracted filters: storeId={storeId}, startDate={startDate}, endDate={endDate}, timeRange={timeRange}")

    api_url = f"{BASE_DASHBOARD_API}/ITCentralServer/storesalesdata"

    payload = {
        "StoreId": storeId,
        "TimeRange": timeRange,
        "StartDateKey": startDate,
        "EndDateKey": endDate,
        "StartDateTime": startDateTime,
        "EndDateTime": endDateTime,
        "FileType": 'SalesDataExport',
    }
    print(api_url, input, payload)
    response = requests.get(api_url, params=payload, timeout=30)

    data = response.json()

    if not data:
        return "No store sales data records found."

    result = []

    for item in data:
        summary = f"""
        Date Key: {item['DateKey']}
        Date Time Stamp: {item['DateTimeStamp']}
        Application Source Key: {item['ApplicationSourceKey']}
        Location Key: {item['LocationKey']}
        Device Name: {item['DeviceName']}
        File Name: {item['FileName']}
        File Type: {item['FileType']}
        File Generated Timestamp: {item['FileGeneratedTimeStamp']}
        File Uploaded Timestamp: {item['FileUploadedTimeStamp']}
        Exception: {item['Exception']}
        """
        result.append(summary.strip())

    return "\n\n".join(result)


@tool
def store_fileupload(input: str) -> str:
    """
    Use this tool to check store file upload status.
    It returns information about:
    - Date and location of the store
    - Device name and file details
    - File generated and uploaded timestamps
    - Application source
    - Exception in case of failures
    """
    filters = extract_filters(input)
    print(filters)
    storeId = filters["storeId"]
    startDate = filters["startDate"]
    endDate = filters["endDate"]
    startDateTime = filters["startDateTime"] + ' 00:00:00'
    endDateTime = filters["endDateTime"] + ' 23:59:59'
    timeRange = 4
    print(f"Extracted filters: storeId={storeId}, startDate={startDate}, endDate={endDate}, timeRange={timeRange}")

    api_url = f"{BASE_DASHBOARD_API}/ITCentralServer/fileupload"

    payload = {
        "StoreId": storeId,
        "TimeRange": timeRange,
        "StartDateKey": startDate,
        "EndDateKey": endDate,
        "StartDateTime": startDateTime,
        "EndDateTime": endDateTime
    }
    print(api_url, input, payload)
    response = requests.get(api_url, params=payload, timeout=30)

    data = response.json()

    if not data:
        return "No store file upload records found."

    result = []

    for item in data:
        summary = f"""
        Date Key: {item['DateKey']}
        Date Time Stamp: {item['DateTimeStamp']}
        Application Source Key: {item['ApplicationSourceKey']}
        Location Key: {item['LocationKey']}
        Device Name: {item['DeviceName']}
        File Name: {item['FileName']}
        File Type: {item['FileType']}
        File Generated Timestamp: {item['FileGeneratedTimeStamp']}
        File Uploaded Timestamp: {item['FileUploadedTimeStamp']}
        Exception: {item['Exception']}
        """
        result.append(summary.strip())

    return "\n\n".join(result)
