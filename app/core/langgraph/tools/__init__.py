"""LangGraph tools for enhanced language model capabilities.

This package contains custom tools that can be used with LangGraph to extend
the capabilities of language models. Currently includes tools for web search
and other external integrations.
"""

from langchain_core.tools.base import BaseTool

from .duckduckgo_search import duckduckgo_search_tool
from .meeting_management import (
    create_meeting_agenda_tool,
    decision_support_tool,
    generate_meeting_minutes_tool,
)

tools: list[BaseTool] = [
    duckduckgo_search_tool,
    create_meeting_agenda_tool,
    decision_support_tool,
    generate_meeting_minutes_tool,
]
