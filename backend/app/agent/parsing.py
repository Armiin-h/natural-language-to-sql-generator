"""Parse LangGraph agent message traces into SQL + step summaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentStep:
    kind: str
    name: str | None = None
    content: str = ""
    tool_input: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedAgentResult:
    answer: str
    sql_queries: list[str] = field(default_factory=list)
    steps: list[AgentStep] = field(default_factory=list)
    raw_messages: list[Any] = field(default_factory=list)


def _content_to_str(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]))
            else:
                parts.append(str(block))
        return "\n".join(parts).strip()
    return str(content).strip()


def _tool_call_name(call: Any) -> str:
    if isinstance(call, dict):
        return str(call.get("name") or call.get("tool") or "")
    return str(getattr(call, "name", "") or "")


def _tool_call_args(call: Any) -> dict[str, Any]:
    if isinstance(call, dict):
        args = call.get("args") or call.get("arguments") or {}
        return dict(args) if isinstance(args, dict) else {"input": args}
    args = getattr(call, "args", None) or getattr(call, "arguments", None) or {}
    return dict(args) if isinstance(args, dict) else {"input": args}


def extract_sql_from_tool_input(args: dict[str, Any]) -> str | None:
    """Pull a SQL string from toolkit tool arguments."""
    for key in ("query", "sql", "input"):
        value = args.get(key)
        if isinstance(value, str) and value.strip():
            stripped = value.strip()
            # Toolkit list/schema tools sometimes pass empty or table lists
            if key == "input" and not _looks_like_sql(stripped):
                continue
            if _looks_like_sql(stripped) or key in {"query", "sql"}:
                return stripped
    return None


def _looks_like_sql(text: str) -> bool:
    head = text.lstrip().lower()
    return head.startswith(("select", "with", "pragma", "explain"))


def _extract_sql_from_text(text: str) -> list[str]:
    """Pull SQL from fenced code blocks or bare SELECT statements in model text."""
    import re

    found: list[str] = []
    for match in re.finditer(r"```(?:sql)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL):
        candidate = match.group(1).strip()
        if _looks_like_sql(candidate):
            found.append(candidate)
    if not found:
        for match in re.finditer(
            r"(?is)\b(select\b.+?)(?:;|$)",
            text,
        ):
            candidate = match.group(1).strip().rstrip(";")
            if _looks_like_sql(candidate):
                found.append(candidate + ";")
                break
    return found


def parse_agent_messages(messages: list[Any]) -> ParsedAgentResult:
    """Extract final answer, executed SQL, and a readable step trace."""
    steps: list[AgentStep] = []
    sql_queries: list[str] = []
    answer = ""

    for message in messages:
        msg_type = getattr(message, "type", None) or message.__class__.__name__
        content = _content_to_str(getattr(message, "content", ""))

        if msg_type in {"human", "HumanMessage"}:
            steps.append(AgentStep(kind="human", content=content))
            continue

        tool_calls = getattr(message, "tool_calls", None) or []
        if tool_calls:
            for call in tool_calls:
                name = _tool_call_name(call)
                args = _tool_call_args(call)
                sql = extract_sql_from_tool_input(args)
                if sql and name in {"sql_db_query", "sql_db_query_checker"}:
                    if sql not in sql_queries:
                        sql_queries.append(sql)
                steps.append(
                    AgentStep(
                        kind="tool_call",
                        name=name,
                        content=content,
                        tool_input=args,
                    )
                )
            continue

        if msg_type in {"tool", "ToolMessage"}:
            name = getattr(message, "name", None)
            steps.append(AgentStep(kind="tool_result", name=name, content=content))
            continue

        if msg_type in {"ai", "AIMessage", "AIMessageChunk"}:
            if content:
                answer = content
                steps.append(AgentStep(kind="ai", content=content))
                for sql in _extract_sql_from_text(content):
                    if sql not in sql_queries:
                        sql_queries.append(sql)

    return ParsedAgentResult(
        answer=answer,
        sql_queries=sql_queries,
        steps=steps,
        raw_messages=list(messages),
    )
