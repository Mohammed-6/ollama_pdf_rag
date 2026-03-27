import json
import os
from langchain_openai import AzureChatOpenAI
import ollama
from typing import Dict, Any

from src.api.helpers.azure_action_agent import upload_action_csv_to_blob
from src.api.helpers.llm_client import chat_completion
from src.tools.file_transfer_tool import get_store_backup, search_logs, transfer_file, transfer_file1
from src.tools.dashboard_tool import get_dashboard_overview, vertex_cs_status, cs_exceptions, cs_dailysync, cs_fileprocessing
from src.tools.ms_calender_tool import get_calendar_meetings
from src.tools.store_tool import store_vertex, store_exceptions, store_fileprocessing, store_salesdata_file, store_fileupload
from src.tools.upload_tool import upload_file
from langchain_classic import hub
from langchain_classic.agents import AgentExecutor, create_react_agent
from openai import AzureOpenAI

tools = [
    transfer_file, transfer_file1, search_logs, get_store_backup, get_calendar_meetings, get_dashboard_overview, vertex_cs_status, cs_exceptions, cs_dailysync, cs_fileprocessing, store_vertex, store_exceptions, store_fileprocessing, store_salesdata_file, store_fileupload, upload_file
]

prompt = hub.pull("hwchase17/react")
# prompt = hub.pull("hwchase17/openai-tools-agent")
tool_llm = AzureChatOpenAI(deployment_name="gpt-4.1-mini",
                           api_key=os.getenv("AZURE_API_KEY"),
                            azure_endpoint=os.getenv("AZURE_API_BASE"),
                            api_version="2024-05-01-preview")
agent = create_react_agent(llm=tool_llm, tools=tools, prompt=prompt)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=5,
    handle_parsing_errors=True
)



ACTION_PLANNER_PROMPT = """
SYSTEM: Generate EXACTLY 2 lines CSV. Line 1=header, Line 2=data.

LINE 1 (COPY EXACTLY):
intent,action_type,target,store_number,source_path,destination_path,azure_container,azure_folder,requires_confirmation,question

LINE 2 (FILL FOR THIS INPUT):
{user_input}

RULES:
ACTION=operation requested, ASK_CLARIFICATION=missing info
action_type: UPLOAD|DOWNLOAD|BACKUP|FETCH_LOGS|""
target: database|logs|files|""
store_number: number OR ""
requires_confirmation: true|false
question: ONLY for ASK_CLARIFICATION

OUTPUT 2 LINES NOW:

"""


def plan_action(user_input: str) -> Dict[str, Any]:
    """
    Converts user intent into a structured action plan.
    Returns JSON dict only.
    """
    if not user_input or not user_input.strip():
        return {
            "intent": "ASK_CLARIFICATION",
            "missing_information": ["user_request"],
            "question": "Please describe what action you want to perform."
        }

    prompt = ACTION_PLANNER_PROMPT.format(
        user_input=user_input.strip()
    )

    
    agent_response = agent_executor.invoke({"input": user_input})

    print(f"Agent output: {agent_response}")

    final_answer = agent_response.get("output", "")

    return final_answer  # Run the agent with the user question
    

    try:
        output = chat_completion(
                system_prompt=prompt,
                user_input=user_input.strip(),
            )

        # Basic validation: must contain header + one row
        lines = output.splitlines()
        print(f"📊 Model output lines: {lines}")
        if len(lines) < 2 or not lines[0].startswith("intent,"):
            print("❌ Invalid CSV from model")
            return "RETRY_MODEL_FAILED"
        store_number = "1001"  # default for now
        headers = [h.strip() for h in lines[0].split(",")]
        values = [v.strip() for v in lines[1].split(",")]

        if "store_number" in headers:
            idx = headers.index("store_number")
            print(idx, values[idx])
            if idx < len(values):
                store_number = values[idx]
        print(store_number)
        # return store_number
        result = handle_action_with_confirmation(
            csv_text=output,
            user_confirmation="No",  # or None / "NO"
            upload_func=upload_action_csv_to_blob,
            store_number=store_number,
            message=user_input.strip()
        )

        # print(result)



        return str(result)


    except Exception as e:
        print(f"❌ Action planner error: {e}")

        return {
            "intent": "ASK_CLARIFICATION",
            "missing_information": ["action_details"],
            "question": "I couldn't determine the exact action. Can you clarify?"
        }


def requires_confirmation(csv_text: str, user_input: str | None = None) -> bool:
    """
    Returns True if confirmation is still required.
    Returns False if safe to proceed.
    """

    # ---------- Step 1: CSV-based decision ----------
    csv_requires_confirmation = True  # default safe

    if csv_text:
        lines = csv_text.strip().splitlines()
        if len(lines) >= 2:
            headers = [h.strip() for h in lines[0].split(",")]
            values = [v.strip() for v in lines[1].split(",")]

            if "requires_confirmation" in headers:
                idx = headers.index("requires_confirmation")
                if idx < len(values):
                    csv_requires_confirmation = (
                        values[idx].lower() == "true"
                    )

    # ---------- Step 2: User confirmation override ----------
    if user_input:
        confirmation_keywords = {
            "yes",
            "y",
            "confirm",
            "confirmed",
            "proceed",
            "go ahead",
            "do it",
            "ok",
            "okay",
            "sure",
            "approved",
        }

        text = user_input.strip().lower()
        if any(k in text for k in confirmation_keywords):
            return False  # 🔑 override CSV

    # ---------- Step 3: Final decision ----------
    return csv_requires_confirmation


def normalize_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return False


def handle_action_with_confirmation(
    csv_text: str,
    user_confirmation: str | None,
    upload_func,
    message:str,
    store_number:str,
):
    """
    Controls whether an action is uploaded to Azure based on confirmation.
    """

    needs_confirmation = requires_confirmation(csv_text, message)
    print(needs_confirmation,user_confirmation)
    needs_confirmation = normalize_bool(needs_confirmation)

    # Step 1: Ask confirmation if required
    if needs_confirmation and user_confirmation.upper() == "YES":
        return {
            "status": "CONFIRMATION_REQUIRED",
            "message": "User confirmation needed before proceeding",
            "csv_payload": csv_text,
            "message": message + ", Please confirm"  # This can be used by frontend to prompt user
        }

    # Step 2: User said NO → abort
    if not needs_confirmation or user_confirmation.upper() == "NO":
        return upload_func(csv_text=csv_text, store_number=store_number)
    
    return {
            "status": "NO_CONFIRMATION_NEEDED_OR_CONFIRMED",
            "csv_payload": csv_text
        }
    # Step 3: User said YES → upload
    if not needs_confirmation or user_confirmation.upper() == "YES":
        return upload_func(csv_text=csv_text, **upload_kwargs)
