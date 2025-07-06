"""LangGraph tools for enhanced language model capabilities.

This package contains custom tools that can be used with LangGraph to extend
the capabilities of language models. Includes tools for web search, meeting
management, and advanced AI/ML operations.
"""

from langchain_core.tools.base import BaseTool

from .duckduckgo_search import duckduckgo_search_tool
from .meeting_management import (
    create_meeting_agenda_tool,
    decision_support_tool,
    generate_meeting_minutes_tool,
)
from .ai_ml_tools import (
    meeting_intelligence_tool,
    decision_support_tool as ai_decision_support_tool,
    predictive_analytics_tool,
    sentiment_analysis_tool,
    topic_extraction_tool,
    semantic_search_tool,
    engagement_analysis_tool,
    schedule_optimization_tool,
)

tools: list[BaseTool] = [
    # Web search tools
    duckduckgo_search_tool,
    
    # Meeting management tools
    create_meeting_agenda_tool,
    decision_support_tool,
    generate_meeting_minutes_tool,
    
    # Advanced AI/ML tools
    meeting_intelligence_tool,
    ai_decision_support_tool,
    predictive_analytics_tool,
    sentiment_analysis_tool,
    topic_extraction_tool,
    semantic_search_tool,
    engagement_analysis_tool,
    schedule_optimization_tool,
]
