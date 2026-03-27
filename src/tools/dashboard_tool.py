from langchain_core.tools import tool
import requests
import json
import os

import re
from datetime import datetime, timedelta
from langchain_core.tools import tool
import requests

from src.api.helpers.llm_client import chat_completion
from datetime import datetime

BASE_DASHBOARD_API = os.getenv("BASE_DASHBOARD_API", "")

EXTRACT_PROMPT = """
Extract parameters from the user query.

Return ONLY valid JSON.
Do not include markdown or explanations.

Current year: {current_year}

Fields:
storeId: store number mentioned in the query
startDate: date in YYYYMMDD
endDate: date in YYYYMMDD
startDateTime: date in YYYY-MM-DD
endDateTime: date in YYYY-MM-DD

Rules:
- If no storeId is mentioned return 0
- If a date is provided without a year, assume the year is {current_year}
- If no dates mentioned return today date as startDate and endDate

User query:
{query}
"""


def extract_filters(query):
    current_year= datetime.now().year
    prompt = EXTRACT_PROMPT.format(query=query, current_year=current_year)
    response = chat_completion(
                system_prompt=prompt,
                user_input=query
            )

    # content = response.content.strip()

    data = json.loads(response)

    # print(response)

    return data

@tool
def vertex_cs_status(input:str) -> str:
    """
    Use this tool to check Central Server Vertex RTE processing status (do not run when the word "store" is included in the input).

    It returns a summarized report containing:

    **Processing Summary:**
    - Total Success Count
    - Total Failure Count
    - Any exceptions or error details in case of failures

    **Vertex RTE Status (at the end of the summary):**
    - Vertex Download: True (downloaded) / False (not downloaded)
    - Vertex Import: True (imported) / False (not imported)
    *(Based on raw values: 1 = True, 0 = False)*

    At the last summary line, include the Vertex RTE status in the format:
"Vertex Download: True/False, Vertex Import: True/False"
    """

    filters = extract_filters(input)
    # print(filters, input)
    # return str(filters)
    storeId = filters["storeId"]
    startDate = filters["startDate"]
    endDate = filters["endDate"]
    timeRange = 4
    print(f"Extracted filters: storeId={storeId}, startDate={startDate}, endDate={endDate}, timeRange={timeRange}")
    api_url = f"{BASE_DASHBOARD_API}/ITCentralServer/vertex"
    print(api_url, input)

    payload = {
        "TimeRange": timeRange,
        "StartDateKey": startDate,
        "EndDateKey": endDate
    }
    response = requests.get(api_url, json=payload, timeout=30)

    data = response.json()

    if not data:
        return "No Vertex data found."

    result = []

    for item in data:
        summary = f"""
        Date: {item['Date']}
        Overall Status: {item['OverallStatus']}
        RTE File Download: {item['RTEFileDownloadStatus']}
        Mapper Extract: {item['MapperExtract']}
        Vertex Success Stores: {item['VertexRTESuccessStores']}
        Vertex Failure Stores: {item['VertexRTEFailureStores']}
        Exceptions: {item['ExceptionsInCaseOfFailures']}
        """
        result.append(summary.strip())

    return "\n\n".join(result)

@tool
def cs_exceptions(input: str) -> str:
    """
    Use this tool to check Central Server exceptions/errors.
    It returns information about:
    - Store and device that raised the exception
    - Exception date and time
    - Application source of the error
    - Exception message and error code
    - Location key
    """
    filters = extract_filters(input)
    storeId = filters["storeId"]
    startDate = filters["startDate"]
    endDate = filters["endDate"]
    startDateTime = filters["startDateTime"] + ' 00:00:00'
    endDateTime = filters["endDateTime"] + ' 23:59:59'
    timeRange = 4
    print(f"Extracted filters: storeId={storeId}, startDate={startDate}, endDate={endDate}, timeRange={timeRange}")

    api_url = f"{BASE_DASHBOARD_API}/ITCentralServer/exceptions"

    payload = {
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
        return "No CS exceptions found."

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
def cs_dailysync(input: str) -> str:
    """
    Use this tool to check Central Server daily sync status.
    It returns information about:
    - Date and location of the sync
    - Device name and file name
    - Sync start and end date/time
    - Sync status
    - Exception and additional information in case of failures
    """
    filters = extract_filters(input)
    storeId = filters["storeId"]
    startDate = filters["startDate"]
    endDate = filters["endDate"]
    startDateTime = filters["startDateTime"] + ' 00:00:00'
    endDateTime = filters["endDateTime"] + ' 23:59:59'
    timeRange = 4
    print(f"Extracted filters: storeId={storeId}, startDate={startDate}, endDate={endDate}, timeRange={timeRange}")

    api_url = f"{BASE_DASHBOARD_API}/ITCentralServer/dailysync"

    payload = {
        "StoreId": 0,
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
        return "No CS daily sync records found."

    result = []

    for item in data:
        summary = f"""
        Date Key: {item['DateKey']}
        Location Key: {item['LocationKey']}
        Device Name: {item['DeviceName']}
        File Name: {item['FileName']}
        Start DateTime: {item['StartDateTime']}
        End DateTime: {item['EndDateTime']}
        Status: {item['Status']}
        Exception: {item['Exception']}
        Additional Information: {item['AdditionalInformation']}
        """
        result.append(summary.strip())

    return "\n\n".join(result)


@tool
def cs_fileprocessing(input: str) -> str:
    """
    Use this tool to check Central Server file processing status.
    It returns information about:
    - File type being processed
    - Total files and success count
    - Last processed date/time
    """
    filters = extract_filters(input)
    storeId = filters["storeId"]
    startDate = filters["startDate"]
    endDate = filters["endDate"]
    startDateTime = filters["startDateTime"] + ' 00:00:00'
    endDateTime = filters["endDateTime"] + ' 23:59:59'
    timeRange = 4
    print(f"Extracted filters: storeId={storeId}, startDate={startDate}, endDate={endDate}, timeRange={timeRange}")

    api_url = f"{BASE_DASHBOARD_API}/ITCentralServer/fileprocessing"

    payload = {
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
        return "No CS file processing records found."

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
def get_dashboard_overview(input: str) -> str:
    """
    Use this tool when the user asks about dashboard statistics,
    system overview, metrics, or summary numbers.
    """
    try:
        filters = extract_filters(input)
        # print(filters, input)
        # return str(filters)
        storeId = filters["storeId"]
        startDate = filters["startDate"]
        endDate = filters["endDate"]
        timeRange = 4
        print(f"Extracted filters: storeId={storeId}, startDate={startDate}, endDate={endDate}, timeRange={timeRange}")
        api_url = f"{BASE_DASHBOARD_API}/ITCentralServer/dashboard-summary/{int(startDate)}"
        print(api_url, input)

        response = requests.get(api_url, timeout=10)
        data = response.json()

        export = data["StoreExportSummary"]
        import_summary = data["StoreImportSummary"]
        cs_export = data["CsExportSummary"]
        cs_import = data["CsImportSummary"]
        CsUpDownload = data["CsUpDownload"]

        summary = f"""
Dashboard Overview for {startDate} to {endDate}

Store Export
------------
Stores: {export['StoreCount']}
Registers: {export['RegisterCount']}
EJ Success: {export['EJSuccess']}
EJ Failure: {export['EJFailure']}
Sales Export Success: {export['SalesDataExportSuccess']}
Sales Export Failure: {export['SalesDataExportFailure']}
Transaction BLOB Upload Success: {export['TransactionBLOBUploadSuccess']}
Transaction BLOB Upload Failure: {export['TransactionBLOBUploadFailure']}

Store Import
------------
MD Item Success: {import_summary['MD_Item_Success']}
MD Item Failure: {import_summary['MD_Item_Failure']}
MD Dept Success: {import_summary['md_dept_Success']}
MD Dept Failure: {import_summary['md_dept_Failure']}
Promo Success: {import_summary['Promo_Success']}
Promo Failure: {import_summary['Promo_Failure']}
PriceChange Success: {import_summary['PriceChange_Success']}
PriceChange Failure: {import_summary['PriceChange_Failure']}
XENIADOIT Success: {import_summary['XENIADOIT_Success']}
XENIADOIT Failure: {import_summary['XENIADOIT_Failure']}
VertexRTE Success: {import_summary['VertexRTE_Success']}
VertexRTE Failure: {import_summary['VertexRTE_Failure']}
XeniaStoreConfig Success: {import_summary['XeniaStoreConfig_Success']}
XeniaStoreConfig Failure: {import_summary['XeniaStoreConfig_Failure']}


CS Export
---------
Vertex Success: {cs_export['CSVertexSuccess']}
Vertex Failure: {cs_export['CSVertexFailure']}

CS Import
---------
MD Item Success: {cs_import['CS_MD_Item_Success']}
MD Item Failure: {cs_import['CS_MD_Item_Failure']}
md dept Success: {cs_import['CS_md_dept_Success']}
md dept Failure: {cs_import['CS_md_dept_Failure']}
Promo Success: {cs_import['CS_Promo_Success']}
Promo Failure: {cs_import['CS_Promo_Failure']}
PriceChange uccess: {cs_import['CS_PriceChange_Success']}
PriceChange Failure: {cs_import['CS_PriceChange_Failure']}
Transaction BLOB Downlaod: {cs_import['CS_Transaction_BLOB_Downlaod']}
Transaction BLOB Failure: {cs_import['CS_Transaction_BLOB_Failure']}


CS Vertex Up/Download
---------
Vertex Download: {CsUpDownload['VertexNightDownload']}
Vertex Import: {CsUpDownload['VertexImport']}
"""

        return summary.strip()

    except Exception as e:
        return f"Failed to fetch dashboard data: {str(e)}"