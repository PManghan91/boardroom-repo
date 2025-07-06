"""Meeting management tools for LangGraph integration."""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.core.metrics import ai_tool_executions_total, ai_tool_duration_seconds
from app.core.exceptions import raise_tool_execution_error


class MeetingAgendaInput(BaseModel):
    """Input for meeting agenda creation tool."""
    topic: str = Field(description="Main topic of the meeting")
    duration_minutes: int = Field(description="Meeting duration in minutes", default=60)
    participants: List[str] = Field(description="List of participant names")
    additional_items: Optional[List[str]] = Field(description="Additional agenda items", default=None)


class DecisionSupportInput(BaseModel):
    """Input for decision support tool."""
    decision_topic: str = Field(description="The decision to be made")
    options: List[str] = Field(description="Available options for the decision")
    criteria: Optional[List[str]] = Field(description="Decision criteria", default=None)
    context: Optional[str] = Field(description="Additional context for the decision", default=None)


class MeetingMinutesInput(BaseModel):
    """Input for meeting minutes generation tool."""
    discussion_points: List[str] = Field(description="Key discussion points")
    decisions_made: List[str] = Field(description="Decisions made during the meeting")
    action_items: List[str] = Field(description="Action items assigned")
    participants: List[str] = Field(description="Meeting participants")


class CreateMeetingAgendaTool(BaseTool):
    """Tool for creating structured meeting agendas."""
    
    name: str = "create_meeting_agenda"
    description: str = "Creates a structured meeting agenda based on topic, duration, and participants"
    args_schema: type = MeetingAgendaInput

    def _run(self, **kwargs) -> str:
        """Execute the tool synchronously."""
        return self._create_agenda(**kwargs)

    async def _arun(self, **kwargs) -> str:
        """Execute the tool asynchronously."""
        return self._create_agenda(**kwargs)

    def _create_agenda(
        self, 
        topic: str, 
        duration_minutes: int, 
        participants: List[str], 
        additional_items: Optional[List[str]] = None
    ) -> str:
        """Create a meeting agenda."""
        
        with ai_tool_duration_seconds.labels(tool_name=self.name).time():
            try:
                ai_tool_executions_total.labels(tool_name=self.name, status="started").inc()
                
                # Calculate time allocations
                intro_time = min(10, duration_minutes * 0.1)
                discussion_time = duration_minutes * 0.7
                wrap_up_time = min(10, duration_minutes * 0.1)
                buffer_time = duration_minutes - intro_time - discussion_time - wrap_up_time
                
                agenda = {
                    "meeting_topic": topic,
                    "duration_minutes": duration_minutes,
                    "participants": participants,
                    "agenda_items": [
                        {
                            "item": "Welcome and Introductions",
                            "duration_minutes": intro_time,
                            "type": "opening"
                        },
                        {
                            "item": f"Discussion: {topic}",
                            "duration_minutes": discussion_time,
                            "type": "main_discussion"
                        }
                    ]
                }
                
                # Add additional items if provided
                if additional_items:
                    for item in additional_items:
                        agenda["agenda_items"].append({
                            "item": item,
                            "duration_minutes": buffer_time / len(additional_items),
                            "type": "additional"
                        })
                
                # Add wrap-up
                agenda["agenda_items"].append({
                    "item": "Action Items and Next Steps",
                    "duration_minutes": wrap_up_time,
                    "type": "closing"
                })
                
                ai_tool_executions_total.labels(tool_name=self.name, status="success").inc()
                logger.info("meeting_agenda_created", topic=topic, participants_count=len(participants))
                
                return json.dumps(agenda, indent=2)
                
            except Exception as e:
                ai_tool_executions_total.labels(tool_name=self.name, status="error").inc()
                logger.error("meeting_agenda_creation_failed", error=str(e))
                raise_tool_execution_error(f"Failed to create meeting agenda: {str(e)}", self.name)


class DecisionSupportTool(BaseTool):
    """Tool for providing decision support analysis."""
    
    name: str = "decision_support_analysis"
    description: str = "Provides structured analysis to support decision making"
    args_schema: type = DecisionSupportInput

    def _run(self, **kwargs) -> str:
        """Execute the tool synchronously."""
        return self._analyze_decision(**kwargs)

    async def _arun(self, **kwargs) -> str:
        """Execute the tool asynchronously."""
        return self._analyze_decision(**kwargs)

    def _analyze_decision(
        self, 
        decision_topic: str, 
        options: List[str], 
        criteria: Optional[List[str]] = None,
        context: Optional[str] = None
    ) -> str:
        """Analyze a decision and provide structured support."""
        
        with ai_tool_duration_seconds.labels(tool_name=self.name).time():
            try:
                ai_tool_executions_total.labels(tool_name=self.name, status="started").inc()
                
                # Default criteria if none provided
                if not criteria:
                    criteria = ["Feasibility", "Cost", "Risk", "Timeline", "Impact"]
                
                analysis = {
                    "decision_topic": decision_topic,
                    "context": context or "No additional context provided",
                    "options_analysis": [],
                    "criteria": criteria,
                    "recommendation": {
                        "preferred_option": None,
                        "reasoning": "",
                        "considerations": []
                    }
                }
                
                # Analyze each option against criteria
                for option in options:
                    option_analysis = {
                        "option": option,
                        "criteria_scores": {},
                        "pros": [],
                        "cons": [],
                        "overall_score": 0
                    }
                    
                    # Simple scoring logic (in real implementation, this could be more sophisticated)
                    total_score = 0
                    for criterion in criteria:
                        # Placeholder scoring - would be enhanced with real analysis
                        score = hash(f"{option}{criterion}") % 5 + 1  # Score 1-5
                        option_analysis["criteria_scores"][criterion] = score
                        total_score += score
                    
                    option_analysis["overall_score"] = total_score / len(criteria)
                    analysis["options_analysis"].append(option_analysis)
                
                # Determine recommendation
                best_option = max(analysis["options_analysis"], key=lambda x: x["overall_score"])
                analysis["recommendation"]["preferred_option"] = best_option["option"]
                analysis["recommendation"]["reasoning"] = f"Highest overall score ({best_option['overall_score']:.1f}) based on evaluation criteria"
                analysis["recommendation"]["considerations"] = [
                    "Review the criteria scores for each option",
                    "Consider any qualitative factors not captured in the analysis",
                    "Validate assumptions with stakeholders"
                ]
                
                ai_tool_executions_total.labels(tool_name=self.name, status="success").inc()
                logger.info("decision_analysis_completed", topic=decision_topic, options_count=len(options))
                
                return json.dumps(analysis, indent=2)
                
            except Exception as e:
                ai_tool_executions_total.labels(tool_name=self.name, status="error").inc()
                logger.error("decision_analysis_failed", error=str(e))
                raise_tool_execution_error(f"Failed to analyze decision: {str(e)}", self.name)


class GenerateMeetingMinutesTool(BaseTool):
    """Tool for generating structured meeting minutes."""
    
    name: str = "generate_meeting_minutes"
    description: str = "Generates structured meeting minutes from discussion points and decisions"
    args_schema: type = MeetingMinutesInput

    def _run(self, **kwargs) -> str:
        """Execute the tool synchronously."""
        return self._generate_minutes(**kwargs)

    async def _arun(self, **kwargs) -> str:
        """Execute the tool asynchronously."""
        return self._generate_minutes(**kwargs)

    def _generate_minutes(
        self, 
        discussion_points: List[str], 
        decisions_made: List[str], 
        action_items: List[str], 
        participants: List[str]
    ) -> str:
        """Generate meeting minutes."""
        
        with ai_tool_duration_seconds.labels(tool_name=self.name).time():
            try:
                ai_tool_executions_total.labels(tool_name=self.name, status="started").inc()
                
                minutes = {
                    "meeting_date": datetime.now().strftime("%Y-%m-%d"),
                    "meeting_time": datetime.now().strftime("%H:%M"),
                    "participants": participants,
                    "discussion_summary": {
                        "key_points": discussion_points,
                        "total_discussion_items": len(discussion_points)
                    },
                    "decisions": {
                        "decisions_made": decisions_made,
                        "total_decisions": len(decisions_made)
                    },
                    "action_items": {
                        "items": [
                            {
                                "item": action,
                                "assigned_date": datetime.now().strftime("%Y-%m-%d"),
                                "due_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
                                "status": "assigned"
                            }
                            for action in action_items
                        ],
                        "total_actions": len(action_items)
                    },
                    "next_steps": [
                        "Follow up on action items within one week",
                        "Schedule follow-up meeting if needed",
                        "Share meeting minutes with all participants"
                    ]
                }
                
                ai_tool_executions_total.labels(tool_name=self.name, status="success").inc()
                logger.info("meeting_minutes_generated", 
                           participants_count=len(participants),
                           decisions_count=len(decisions_made),
                           action_items_count=len(action_items))
                
                return json.dumps(minutes, indent=2)
                
            except Exception as e:
                ai_tool_executions_total.labels(tool_name=self.name, status="error").inc()
                logger.error("meeting_minutes_generation_failed", error=str(e))
                raise_tool_execution_error(f"Failed to generate meeting minutes: {str(e)}", self.name)


# Export tools
create_meeting_agenda_tool = CreateMeetingAgendaTool()
decision_support_tool = DecisionSupportTool()
generate_meeting_minutes_tool = GenerateMeetingMinutesTool()