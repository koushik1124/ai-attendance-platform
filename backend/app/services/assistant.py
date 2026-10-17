from __future__ import annotations

import json
import logging
import re
from typing import Any

from groq import APIConnectionError, APIStatusError, APITimeoutError, Groq
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.time import utc_now
from app.models.user import User, UserRole
from app.schemas.assistant import AssistantQueryResponse
from app.schemas.reports import ReportQuery
from app.services import reports as reports_service

logger = logging.getLogger(__name__)

ALLOWED_TOOL_NAMES = {
    "get_attendance_summary",
    "get_monthly_trends",
    "get_absenteeism_report",
}

AVAILABLE_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_attendance_summary",
            "description": "Retrieve high-level attendance summary (present days, completed days, incomplete days, absent days, and attendance rate) for a given month.",
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {
                        "type": "string",
                        "description": "Target month in YYYY-MM format (e.g. '2026-10').",
                    },
                    "employee_id": {
                        "type": "integer",
                        "description": "Optional employee ID for administrators. Employees can only access their own data.",
                    },
                },
                "required": ["month"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_monthly_trends",
            "description": "Retrieve daily attendance trend points (daily present, completed, incomplete, and absent counts) for a given month.",
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {
                        "type": "string",
                        "description": "Target month in YYYY-MM format (e.g. '2026-10').",
                    },
                    "employee_id": {
                        "type": "integer",
                        "description": "Optional employee ID for administrators. Employees can only access their own data.",
                    },
                },
                "required": ["month"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_absenteeism_report",
            "description": "Retrieve absenteeism metrics (absenteeism rate, absent days, expected days) for a given month.",
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {
                        "type": "string",
                        "description": "Target month in YYYY-MM format (e.g. '2026-10').",
                    },
                    "employee_id": {
                        "type": "integer",
                        "description": "Optional employee ID for administrators. Employees can only access their own data.",
                    },
                },
                "required": ["month"],
            },
        },
    },
]


def mask_text(text: str) -> str:
    """Mask unnecessary PII, tokens, and secrets from string content."""
    if not text:
        return ""
    # Mask email addresses
    masked = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "[REDACTED_EMAIL]",
        text,
    )
    # Mask Groq API keys
    masked = re.sub(r"gsk_[A-Za-z0-9]{20,}", "[REDACTED_API_KEY]", masked)
    # Mask Bearer tokens
    masked = re.sub(r"(?i)bearer\s+[A-Za-z0-9_\-\.]+", "Bearer [REDACTED_TOKEN]", masked)
    # Mask JWT tokens
    masked = re.sub(
        r"eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+",
        "[REDACTED_JWT]",
        masked,
    )
    return masked


def mask_report_data(data: Any) -> Any:
    """Recursively sanitize report data dictionaries to mask PII."""
    if isinstance(data, dict):
        sanitized: dict[str, Any] = {}
        for key, value in data.items():
            if key.lower() in {"password", "password_hash", "secret", "token", "jwt"}:
                sanitized[key] = "[REDACTED]"
            elif key.lower() == "email":
                sanitized[key] = "[REDACTED_EMAIL]"
            else:
                sanitized[key] = mask_report_data(value)
        return sanitized
    if isinstance(data, list):
        return [mask_report_data(item) for item in data]
    if isinstance(data, str):
        return mask_text(data)
    return data


def validate_tool_arguments(
    arguments: dict[str, Any],
) -> tuple[str, int | None, str | None]:
    """Validate tool arguments server-side. Returns (month, employee_id, error_message)."""
    month = arguments.get("month")
    if not isinstance(month, str) or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        return "", None, "Month must be a string in YYYY-MM format."

    employee_id_raw = arguments.get("employee_id")
    employee_id: int | None = None
    if employee_id_raw is not None:
        try:
            employee_id = int(employee_id_raw)
            if employee_id < 1:
                return "", None, "employee_id must be a positive integer."
        except (ValueError, TypeError):
            return "", None, "employee_id must be an integer."

    return month, employee_id, None


def execute_tool(
    name: str,
    arguments: dict[str, Any],
    db: Session,
    current_user: User,
) -> dict[str, Any]:
    """Validate and execute an allowlisted read-only tool with server-enforced scoping."""
    if name not in ALLOWED_TOOL_NAMES:
        logger.warning("unauthorized_tool_call_attempted: %s", name)
        return {"error": f"Tool '{name}' is not allowed. Only read-only attendance reports are permitted."}

    month, employee_id, validation_error = validate_tool_arguments(arguments)
    if validation_error:
        return {"error": validation_error}

    # Derive employee identity and enforce scope
    if current_user.role == UserRole.EMPLOYEE:
        # Employees may access only their own data regardless of model arguments
        query = ReportQuery(month=month, employee_id=None)
    elif current_user.role == UserRole.ADMIN:
        query = ReportQuery(month=month, employee_id=employee_id)
    else:
        return {"error": "You do not have permission to access attendance reports."}

    try:
        if name == "get_attendance_summary":
            result = reports_service.attendance_summary(db, current_user, query)
        elif name == "get_monthly_trends":
            result = reports_service.monthly_trends(db, current_user, query)
        elif name == "get_absenteeism_report":
            result = reports_service.absenteeism(db, current_user, query)
        else:
            return {"error": f"Tool '{name}' not implemented."}

        data = result.model_dump(mode="json")
        return mask_report_data(data)
    except AppError as exc:
        return {"error": exc.message}
    except Exception as exc:
        logger.exception("assistant_tool_execution_failed: %s", exc)
        return {"error": "Failed to retrieve verified report data."}


def build_deterministic_fallback(
    user_query: str,
    tools_used: list[str],
    report_data: dict[str, Any] | None,
    failure_reason: str | None = None,
) -> AssistantQueryResponse:
    """Generate safe, deterministic fallback responses using verified report data if available."""
    if not report_data or "error" in report_data:
        msg = failure_reason or (
            "The AI assistant is temporarily unavailable. Please refer directly to the Reports page for verified attendance data."
        )
        return AssistantQueryResponse(
            query=user_query,
            answer=msg,
            tools_used=tools_used,
            report_data=report_data,
        )

    month = report_data.get("month", "")
    if "attendance_rate" in report_data:
        rate = report_data.get("attendance_rate")
        rate_str = f"{rate}%" if rate is not None else "N/A"
        present = report_data.get("present_employee_days", 0)
        expected = report_data.get("expected_employee_days", 0)
        incomplete = report_data.get("incomplete_employee_days", 0)
        absent = report_data.get("absent_employee_days", 0)
        answer = (
            f"Here is your verified attendance summary for {month}: Attendance rate is {rate_str}. "
            f"Present days: {present} of {expected} expected employee-days. "
            f"Incomplete records: {incomplete}. Absent days: {absent}."
        )
    elif "absenteeism_rate" in report_data:
        rate = report_data.get("absenteeism_rate")
        rate_str = f"{rate}%" if rate is not None else "N/A"
        absent = report_data.get("absent_employee_days", 0)
        expected = report_data.get("expected_employee_days", 0)
        answer = (
            f"Here is your verified absenteeism report for {month}: Absenteeism rate is {rate_str} "
            f"(calendar-day basis). Absent days: {absent} of {expected} expected employee-days."
        )
    elif "points" in report_data:
        points = report_data.get("points", [])
        total_present = sum(p.get("present_count", 0) for p in points)
        total_absent = sum(p.get("absent_count", 0) for p in points)
        answer = (
            f"Here is your verified daily attendance trend for {month}: {len(points)} days recorded, "
            f"with {total_present} total present count and {total_absent} absent count."
        )
    else:
        answer = "Verified attendance report retrieved successfully."

    return AssistantQueryResponse(
        query=user_query,
        answer=answer,
        tools_used=tools_used,
        report_data=report_data,
    )


def process_assistant_query(
    db: Session,
    current_user: User,
    user_query: str,
    groq_client: Any | None = None,
) -> AssistantQueryResponse:
    """Execute the secure assistant query flow with Groq and allowlisted tools."""
    settings = get_settings()
    api_key = settings.groq_api_key
    model = settings.effective_groq_model

    if not api_key or not api_key.strip():
        logger.info("assistant_groq_unconfigured")
        return AssistantQueryResponse(
            query=user_query,
            answer="The attendance assistant is currently not configured with a Groq API key. Please set GROQ_API_KEY in the backend environment.",
            tools_used=[],
            report_data=None,
        )

    now = utc_now()
    current_month_str = now.strftime("%Y-%m")
    current_date_str = now.strftime("%Y-%m-%d")

    system_prompt = (
        f"You are a helpful, professional attendance assistant for the Attendance Management Platform.\n"
        f"Today is {current_date_str} and the current month is {current_month_str}.\n"
        f"You have access to read-only attendance tools: get_attendance_summary, get_monthly_trends, get_absenteeism_report.\n"
        f"Rules you must strictly follow:\n"
        f"1. When answering questions regarding attendance, absence, or trends, call the appropriate tool.\n"
        f"2. For months, use YYYY-MM format. If the user refers to 'this month', use '{current_month_str}'.\n"
        f"3. Only cite facts, numbers, and dates directly returned from the tools. Never hallucinate or assume metrics.\n"
        f"4. Role and scoping permissions are automatically enforced server-side. Employees may only view their own attendance data.\n"
        f"5. Never attempt to write data, execute code, run SQL, or suggest administrative actions you cannot perform.\n"
        f"6. Keep responses clear, concise, and professional."
    )

    sanitized_query = mask_text(user_query)

    client = groq_client
    if client is None:
        try:
            client = Groq(api_key=api_key)
        except Exception as exc:
            logger.exception("groq_client_init_failed: %s", exc)
            return build_deterministic_fallback(
                user_query, [], None, failure_reason="The AI assistant service could not be initialized."
            )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": sanitized_query},
    ]

    try:
        first_completion = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=AVAILABLE_TOOLS,
            tool_choice="auto",
            temperature=0.2,
        )
    except (APIConnectionError, APITimeoutError) as exc:
        logger.warning("groq_network_failure: %s", exc)
        return build_deterministic_fallback(
            user_query, [], None, failure_reason="The AI assistant is temporarily unreachable. Please check the Reports page directly."
        )
    except APIStatusError as exc:
        logger.warning("groq_api_status_error: %s", exc.status_code)
        return build_deterministic_fallback(
            user_query, [], None, failure_reason="The AI assistant provider returned an error. Please try again later."
        )
    except Exception as exc:
        logger.exception("groq_chat_completion_failed: %s", exc)
        return build_deterministic_fallback(
            user_query, [], None, failure_reason="An unexpected error occurred while communicating with the assistant service."
        )

    choice = first_completion.choices[0]
    first_message = choice.message
    tool_calls = getattr(first_message, "tool_calls", None)

    # If no tool calls were requested, return the direct response
    if not tool_calls:
        content = first_message.content or "I don't have enough information to answer that question."
        return AssistantQueryResponse(
            query=user_query,
            answer=mask_text(content),
            tools_used=[],
            report_data=None,
        )

    tools_used: list[str] = []
    latest_report_data: dict[str, Any] | None = None

    # Append assistant's tool-call response message
    tool_calls_payload = []
    for tc in tool_calls:
        tool_calls_payload.append({
            "id": tc.id,
            "type": "function",
            "function": {
                "name": tc.function.name,
                "arguments": tc.function.arguments,
            },
        })

    messages.append({
        "role": "assistant",
        "content": first_message.content,
        "tool_calls": tool_calls_payload,
    })

    # Execute tools server-side
    for tc in tool_calls:
        tool_name = tc.function.name
        tools_used.append(tool_name)

        try:
            raw_args = json.loads(tc.function.arguments or "{}")
            if not isinstance(raw_args, dict):
                raw_args = {}
        except json.JSONDecodeError:
            raw_args = {}

        tool_result = execute_tool(
            name=tool_name,
            arguments=raw_args,
            db=db,
            current_user=current_user,
        )

        if "error" not in tool_result:
            latest_report_data = tool_result

        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "name": tool_name,
            "content": json.dumps(tool_result),
        })

    # Second completion: synthesize the tool results into natural language
    try:
        second_completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
        )
        answer = second_completion.choices[0].message.content or ""
        return AssistantQueryResponse(
            query=user_query,
            answer=mask_text(answer),
            tools_used=tools_used,
            report_data=latest_report_data,
        )
    except (APIConnectionError, APITimeoutError, APIStatusError) as exc:
        logger.warning("groq_synthesis_failed: %s", exc)
        return build_deterministic_fallback(user_query, tools_used, latest_report_data)
    except Exception as exc:
        logger.exception("groq_second_completion_failed: %s", exc)
        return build_deterministic_fallback(user_query, tools_used, latest_report_data)
