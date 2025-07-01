"""Unit tests for meeting management tools."""

import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from app.core.langgraph.tools.meeting_management import (
    CreateMeetingAgendaTool,
    DecisionSupportTool,
    GenerateMeetingMinutesTool,
    MeetingAgendaInput,
    DecisionSupportInput,
    MeetingMinutesInput,
    create_meeting_agenda_tool,
    decision_support_tool,
    generate_meeting_minutes_tool,
)
from app.core.exceptions import ToolExecutionException


@pytest.mark.unit
class TestCreateMeetingAgendaTool:
    """Test suite for CreateMeetingAgendaTool."""

    @pytest.fixture
    def tool(self):
        """Create a CreateMeetingAgendaTool instance."""
        return CreateMeetingAgendaTool()

    @pytest.fixture
    def basic_agenda_input(self):
        """Create basic agenda input data."""
        return {
            "topic": "Project Planning Meeting",
            "duration_minutes": 60,
            "participants": ["Alice", "Bob", "Charlie"]
        }

    @pytest.fixture
    def extended_agenda_input(self):
        """Create extended agenda input with additional items."""
        return {
            "topic": "Quarterly Review",
            "duration_minutes": 90,
            "participants": ["Alice", "Bob", "Charlie", "Diana"],
            "additional_items": ["Budget Review", "Resource Allocation"]
        }

    def test_tool_metadata(self, tool):
        """Test tool metadata and schema."""
        assert tool.name == "create_meeting_agenda"
        assert "structured meeting agenda" in tool.description
        assert tool.args_schema == MeetingAgendaInput

    def test_create_basic_agenda(self, tool, basic_agenda_input):
        """Test creating a basic meeting agenda."""
        with patch('app.core.langgraph.tools.meeting_management.ai_tool_executions_total') as mock_metric:
            with patch('app.core.langgraph.tools.meeting_management.ai_tool_duration_seconds') as mock_duration:
                mock_duration.labels.return_value.time.return_value.__enter__ = Mock()
                mock_duration.labels.return_value.time.return_value.__exit__ = Mock(return_value=None)
                
                result = tool._create_agenda(**basic_agenda_input)
                
                # Parse the JSON result
                agenda = json.loads(result)
                
                assert agenda["meeting_topic"] == "Project Planning Meeting"
                assert agenda["duration_minutes"] == 60
                assert agenda["participants"] == ["Alice", "Bob", "Charlie"]
                assert len(agenda["agenda_items"]) == 3  # Welcome, Discussion, Action Items
                
                # Verify agenda items structure
                items = agenda["agenda_items"]
                assert items[0]["type"] == "opening"
                assert items[1]["type"] == "main_discussion"
                assert items[2]["type"] == "closing"
                
                # Verify metrics were called
                mock_metric.labels.assert_called()

    def test_create_agenda_with_additional_items(self, tool, extended_agenda_input):
        """Test creating agenda with additional items."""
        with patch('app.core.langgraph.tools.meeting_management.ai_tool_executions_total'):
            with patch('app.core.langgraph.tools.meeting_management.ai_tool_duration_seconds') as mock_duration:
                mock_duration.labels.return_value.time.return_value.__enter__ = Mock()
                mock_duration.labels.return_value.time.return_value.__exit__ = Mock(return_value=None)
                
                result = tool._create_agenda(**extended_agenda_input)
                
                agenda = json.loads(result)
                
                assert len(agenda["agenda_items"]) == 5  # Welcome, Discussion, 2 Additional, Action Items
                
                # Check additional items
                additional_items = [item for item in agenda["agenda_items"] if item["type"] == "additional"]
                assert len(additional_items) == 2
                assert "Budget Review" in [item["item"] for item in additional_items]
                assert "Resource Allocation" in [item["item"] for item in additional_items]

    def test_time_allocation_calculation(self, tool):
        """Test time allocation calculation for different durations."""
        input_data = {
            "topic": "Short Meeting",
            "duration_minutes": 30,
            "participants": ["Alice", "Bob"]
        }
        
        with patch('app.core.langgraph.tools.meeting_management.ai_tool_executions_total'):
            with patch('app.core.langgraph.tools.meeting_management.ai_tool_duration_seconds') as mock_duration:
                mock_duration.labels.return_value.time.return_value.__enter__ = Mock()
                mock_duration.labels.return_value.time.return_value.__exit__ = Mock(return_value=None)
                
                result = tool._create_agenda(**input_data)
                
                agenda = json.loads(result)
                
                # Verify time allocations are reasonable
                total_time = sum(item["duration_minutes"] for item in agenda["agenda_items"])
                assert total_time == 30

    @pytest.mark.asyncio
    async def test_async_execution(self, tool, basic_agenda_input):
        """Test asynchronous tool execution."""
        with patch('app.core.langgraph.tools.meeting_management.ai_tool_executions_total'):
            with patch('app.core.langgraph.tools.meeting_management.ai_tool_duration_seconds') as mock_duration:
                mock_duration.labels.return_value.time.return_value.__enter__ = Mock()
                mock_duration.labels.return_value.time.return_value.__exit__ = Mock(return_value=None)
                
                result = await tool._arun(**basic_agenda_input)
                
                agenda = json.loads(result)
                assert agenda["meeting_topic"] == "Project Planning Meeting"

    def test_tool_execution_error_handling(self, tool):
        """Test error handling in tool execution."""
        with patch('app.core.langgraph.tools.meeting_management.ai_tool_executions_total'):
            with patch('app.core.langgraph.tools.meeting_management.ai_tool_duration_seconds') as mock_duration:
                mock_duration.labels.return_value.time.return_value.__enter__ = Mock()
                mock_duration.labels.return_value.time.return_value.__exit__ = Mock(return_value=None)
                
                # Mock json.dumps to raise an error
                with patch('json.dumps', side_effect=Exception("JSON error")):
                    with pytest.raises(ToolExecutionException):
                        tool._create_agenda(
                            topic="Test",
                            duration_minutes=60,
                            participants=["Alice"]
                        )


@pytest.mark.unit
class TestDecisionSupportTool:
    """Test suite for DecisionSupportTool."""

    @pytest.fixture
    def tool(self):
        """Create a DecisionSupportTool instance."""
        return DecisionSupportTool()

    @pytest.fixture
    def basic_decision_input(self):
        """Create basic decision input data."""
        return {
            "decision_topic": "Choose development framework",
            "options": ["React", "Vue", "Angular"],
            "criteria": ["Learning curve", "Performance", "Community support"],
            "context": "Building a new web application for the company"
        }

    @pytest.fixture
    def minimal_decision_input(self):
        """Create minimal decision input data."""
        return {
            "decision_topic": "Choose lunch venue",
            "options": ["Restaurant A", "Restaurant B"]
        }

    def test_tool_metadata(self, tool):
        """Test tool metadata and schema."""
        assert tool.name == "decision_support_analysis"
        assert "structured analysis" in tool.description
        assert tool.args_schema == DecisionSupportInput

    def test_analyze_decision_with_criteria(self, tool, basic_decision_input):
        """Test decision analysis with provided criteria."""
        with patch('app.core.langgraph.tools.meeting_management.ai_tool_executions_total'):
            with patch('app.core.langgraph.tools.meeting_management.ai_tool_duration_seconds') as mock_duration:
                mock_duration.labels.return_value.time.return_value.__enter__ = Mock()
                mock_duration.labels.return_value.time.return_value.__exit__ = Mock(return_value=None)
                
                result = tool._analyze_decision(**basic_decision_input)
                
                analysis = json.loads(result)
                
                assert analysis["decision_topic"] == "Choose development framework"
                assert analysis["context"] == "Building a new web application for the company"
                assert len(analysis["options_analysis"]) == 3
                assert analysis["criteria"] == ["Learning curve", "Performance", "Community support"]
                
                # Verify each option has analysis
                for option_analysis in analysis["options_analysis"]:
                    assert "option" in option_analysis
                    assert "criteria_scores" in option_analysis
                    assert "overall_score" in option_analysis
                    assert option_analysis["overall_score"] > 0
                
                # Verify recommendation exists
                assert analysis["recommendation"]["preferred_option"] is not None
                assert analysis["recommendation"]["reasoning"] != ""

    def test_analyze_decision_default_criteria(self, tool, minimal_decision_input):
        """Test decision analysis with default criteria."""
        with patch('app.core.langgraph.tools.meeting_management.ai_tool_executions_total'):
            with patch('app.core.langgraph.tools.meeting_management.ai_tool_duration_seconds') as mock_duration:
                mock_duration.labels.return_value.time.return_value.__enter__ = Mock()
                mock_duration.labels.return_value.time.return_value.__exit__ = Mock(return_value=None)
                
                result = tool._analyze_decision(**minimal_decision_input)
                
                analysis = json.loads(result)
                
                # Should use default criteria
                expected_criteria = ["Feasibility", "Cost", "Risk", "Timeline", "Impact"]
                assert analysis["criteria"] == expected_criteria
                assert analysis["context"] == "No additional context provided"

    def test_scoring_consistency(self, tool):
        """Test that scoring is consistent for the same inputs."""
        input_data = {
            "decision_topic": "Test Decision",
            "options": ["Option A", "Option B"],
            "criteria": ["Criterion 1", "Criterion 2"]
        }
        
        with patch('app.core.langgraph.tools.meeting_management.ai_tool_executions_total'):
            with patch('app.core.langgraph.tools.meeting_management.ai_tool_duration_seconds') as mock_duration:
                mock_duration.labels.return_value.time.return_value.__enter__ = Mock()
                mock_duration.labels.return_value.time.return_value.__exit__ = Mock(return_value=None)
                
                result1 = tool._analyze_decision(**input_data)
                result2 = tool._analyze_decision(**input_data)
                
                analysis1 = json.loads(result1)
                analysis2 = json.loads(result2)
                
                # Scores should be consistent (using hash-based scoring)
                assert analysis1["options_analysis"][0]["overall_score"] == analysis2["options_analysis"][0]["overall_score"]

    @pytest.mark.asyncio
    async def test_async_execution(self, tool, basic_decision_input):
        """Test asynchronous tool execution."""
        with patch('app.core.langgraph.tools.meeting_management.ai_tool_executions_total'):
            with patch('app.core.langgraph.tools.meeting_management.ai_tool_duration_seconds') as mock_duration:
                mock_duration.labels.return_value.time.return_value.__enter__ = Mock()
                mock_duration.labels.return_value.time.return_value.__exit__ = Mock(return_value=None)
                
                result = await tool._arun(**basic_decision_input)
                
                analysis = json.loads(result)
                assert analysis["decision_topic"] == "Choose development framework"


@pytest.mark.unit
class TestGenerateMeetingMinutesTool:
    """Test suite for GenerateMeetingMinutesTool."""

    @pytest.fixture
    def tool(self):
        """Create a GenerateMeetingMinutesTool instance."""
        return GenerateMeetingMinutesTool()

    @pytest.fixture
    def meeting_minutes_input(self):
        """Create meeting minutes input data."""
        return {
            "discussion_points": [
                "Reviewed project timeline",
                "Discussed budget constraints",
                "Evaluated team capacity"
            ],
            "decisions_made": [
                "Approved extended timeline",
                "Allocated additional budget"
            ],
            "action_items": [
                "Update project plan",
                "Communicate changes to stakeholders",
                "Schedule follow-up meeting"
            ],
            "participants": ["Alice", "Bob", "Charlie", "Diana"]
        }

    def test_tool_metadata(self, tool):
        """Test tool metadata and schema."""
        assert tool.name == "generate_meeting_minutes"
        assert "structured meeting minutes" in tool.description
        assert tool.args_schema == MeetingMinutesInput

    def test_generate_minutes_basic(self, tool, meeting_minutes_input):
        """Test basic meeting minutes generation."""
        with patch('app.core.langgraph.tools.meeting_management.ai_tool_executions_total'):
            with patch('app.core.langgraph.tools.meeting_management.ai_tool_duration_seconds') as mock_duration:
                mock_duration.labels.return_value.time.return_value.__enter__ = Mock()
                mock_duration.labels.return_value.time.return_value.__exit__ = Mock(return_value=None)
                
                result = tool._generate_minutes(**meeting_minutes_input)
                
                minutes = json.loads(result)
                
                # Verify structure
                assert "meeting_date" in minutes
                assert "meeting_time" in minutes
                assert "participants" in minutes
                assert "discussion_summary" in minutes
                assert "decisions" in minutes
                assert "action_items" in minutes
                assert "next_steps" in minutes
                
                # Verify content
                assert minutes["participants"] == ["Alice", "Bob", "Charlie", "Diana"]
                assert len(minutes["discussion_summary"]["key_points"]) == 3
                assert len(minutes["decisions"]["decisions_made"]) == 2
                assert len(minutes["action_items"]["items"]) == 3
                
                # Verify counts
                assert minutes["discussion_summary"]["total_discussion_items"] == 3
                assert minutes["decisions"]["total_decisions"] == 2
                assert minutes["action_items"]["total_actions"] == 3

    def test_action_items_structure(self, tool, meeting_minutes_input):
        """Test action items structure with dates."""
        with patch('app.core.langgraph.tools.meeting_management.ai_tool_executions_total'):
            with patch('app.core.langgraph.tools.meeting_management.ai_tool_duration_seconds') as mock_duration:
                mock_duration.labels.return_value.time.return_value.__enter__ = Mock()
                mock_duration.labels.return_value.time.return_value.__exit__ = Mock(return_value=None)
                
                result = tool._generate_minutes(**meeting_minutes_input)
                
                minutes = json.loads(result)
                action_items = minutes["action_items"]["items"]
                
                for item in action_items:
                    assert "item" in item
                    assert "assigned_date" in item
                    assert "due_date" in item
                    assert "status" in item
                    assert item["status"] == "assigned"
                    
                    # Verify date format (basic check)
                    assert len(item["assigned_date"]) == 10  # YYYY-MM-DD format
                    assert len(item["due_date"]) == 10

    def test_empty_lists_handling(self, tool):
        """Test handling of empty discussion points, decisions, and actions."""
        input_data = {
            "discussion_points": [],
            "decisions_made": [],
            "action_items": [],
            "participants": ["Alice"]
        }
        
        with patch('app.core.langgraph.tools.meeting_management.ai_tool_executions_total'):
            with patch('app.core.langgraph.tools.meeting_management.ai_tool_duration_seconds') as mock_duration:
                mock_duration.labels.return_value.time.return_value.__enter__ = Mock()
                mock_duration.labels.return_value.time.return_value.__exit__ = Mock(return_value=None)
                
                result = tool._generate_minutes(**input_data)
                
                minutes = json.loads(result)
                
                assert minutes["discussion_summary"]["total_discussion_items"] == 0
                assert minutes["decisions"]["total_decisions"] == 0
                assert minutes["action_items"]["total_actions"] == 0
                assert len(minutes["action_items"]["items"]) == 0

    @pytest.mark.asyncio
    async def test_async_execution(self, tool, meeting_minutes_input):
        """Test asynchronous tool execution."""
        with patch('app.core.langgraph.tools.meeting_management.ai_tool_executions_total'):
            with patch('app.core.langgraph.tools.meeting_management.ai_tool_duration_seconds') as mock_duration:
                mock_duration.labels.return_value.time.return_value.__enter__ = Mock()
                mock_duration.labels.return_value.time.return_value.__exit__ = Mock(return_value=None)
                
                result = await tool._arun(**meeting_minutes_input)
                
                minutes = json.loads(result)
                assert len(minutes["participants"]) == 4

    def test_date_formatting(self, tool, meeting_minutes_input):
        """Test date formatting in minutes."""
        with patch('app.core.langgraph.tools.meeting_management.ai_tool_executions_total'):
            with patch('app.core.langgraph.tools.meeting_management.ai_tool_duration_seconds') as mock_duration:
                mock_duration.labels.return_value.time.return_value.__enter__ = Mock()
                mock_duration.labels.return_value.time.return_value.__exit__ = Mock(return_value=None)
                
                # Mock datetime to control output
                mock_date = datetime(2023, 12, 15, 14, 30, 0)
                with patch('app.core.langgraph.tools.meeting_management.datetime') as mock_datetime:
                    mock_datetime.now.return_value = mock_date
                    mock_datetime.strftime = mock_date.strftime
                    
                    result = tool._generate_minutes(**meeting_minutes_input)
                    
                    minutes = json.loads(result)
                    
                    assert minutes["meeting_date"] == "2023-12-15"
                    assert minutes["meeting_time"] == "14:30"


@pytest.mark.unit
class TestToolInstances:
    """Test the exported tool instances."""

    def test_tool_instances_exist(self):
        """Test that tool instances are properly exported."""
        assert create_meeting_agenda_tool is not None
        assert decision_support_tool is not None
        assert generate_meeting_minutes_tool is not None
        
        assert isinstance(create_meeting_agenda_tool, CreateMeetingAgendaTool)
        assert isinstance(decision_support_tool, DecisionSupportTool)
        assert isinstance(generate_meeting_minutes_tool, GenerateMeetingMinutesTool)

    def test_tool_names_unique(self):
        """Test that tool names are unique."""
        tools = [create_meeting_agenda_tool, decision_support_tool, generate_meeting_minutes_tool]
        names = [tool.name for tool in tools]
        
        assert len(names) == len(set(names))  # All names should be unique


@pytest.mark.unit
class TestInputSchemas:
    """Test input schema validation."""

    def test_meeting_agenda_input_validation(self):
        """Test MeetingAgendaInput validation."""
        # Valid input
        valid_input = MeetingAgendaInput(
            topic="Test Meeting",
            duration_minutes=60,
            participants=["Alice", "Bob"]
        )
        assert valid_input.topic == "Test Meeting"
        assert valid_input.duration_minutes == 60
        assert valid_input.participants == ["Alice", "Bob"]
        assert valid_input.additional_items is None

        # With additional items
        with_additional = MeetingAgendaInput(
            topic="Test Meeting",
            duration_minutes=60,
            participants=["Alice"],
            additional_items=["Extra topic"]
        )
        assert with_additional.additional_items == ["Extra topic"]

    def test_decision_support_input_validation(self):
        """Test DecisionSupportInput validation."""
        # Minimal valid input
        minimal_input = DecisionSupportInput(
            decision_topic="Choose option",
            options=["A", "B"]
        )
        assert minimal_input.decision_topic == "Choose option"
        assert minimal_input.options == ["A", "B"]
        assert minimal_input.criteria is None
        assert minimal_input.context is None

        # Full input
        full_input = DecisionSupportInput(
            decision_topic="Choose framework",
            options=["React", "Vue"],
            criteria=["Performance", "Learning curve"],
            context="Web development project"
        )
        assert full_input.criteria == ["Performance", "Learning curve"]
        assert full_input.context == "Web development project"

    def test_meeting_minutes_input_validation(self):
        """Test MeetingMinutesInput validation."""
        valid_input = MeetingMinutesInput(
            discussion_points=["Point 1", "Point 2"],
            decisions_made=["Decision 1"],
            action_items=["Action 1", "Action 2"],
            participants=["Alice", "Bob", "Charlie"]
        )
        
        assert len(valid_input.discussion_points) == 2
        assert len(valid_input.decisions_made) == 1
        assert len(valid_input.action_items) == 2
        assert len(valid_input.participants) == 3