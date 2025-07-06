"""Automation Service for intelligent workflows and notifications."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.logging import logger
from app.core.metrics import ai_operations_total
from app.services.ml_service import ml_service

class TriggerType(Enum):
    """Types of automation triggers."""
    SCHEDULED = "scheduled"
    EVENT_BASED = "event_based"
    CONDITION_BASED = "condition_based"
    USER_ACTION = "user_action"
    ML_PREDICTION = "ml_prediction"

class ActionType(Enum):
    """Types of automation actions."""
    NOTIFICATION = "notification"
    EMAIL = "email"
    MEETING_CREATION = "meeting_creation"
    REPORT_GENERATION = "report_generation"
    DATA_PROCESSING = "data_processing"
    WEBHOOK = "webhook"
    ML_INFERENCE = "ml_inference"

class AutomationStatus(Enum):
    """Status of automation rules."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    ERROR = "error"

@dataclass
class AutomationRule:
    """Automation rule definition."""
    rule_id: str
    name: str
    description: str
    trigger_type: TriggerType
    trigger_config: Dict[str, Any]
    action_type: ActionType
    action_config: Dict[str, Any]
    conditions: Optional[List[Dict]] = None
    priority: int = 1
    status: AutomationStatus = AutomationStatus.ACTIVE
    created_at: datetime = datetime.now()
    last_executed: Optional[datetime] = None
    execution_count: int = 0
    error_count: int = 0

@dataclass
class NotificationTemplate:
    """Notification template for intelligent notifications."""
    template_id: str
    name: str
    subject_template: str
    body_template: str
    channel: str  # email, slack, teams, etc.
    personalization_fields: List[str]
    optimal_timing_enabled: bool = True
    sentiment_awareness: bool = True

@dataclass
class ExecutionContext:
    """Context for automation execution."""
    rule_id: str
    trigger_data: Dict[str, Any]
    user_data: Optional[Dict] = None
    meeting_data: Optional[Dict] = None
    timestamp: datetime = datetime.now()

class AutomationService:
    """Service for managing intelligent automation workflows."""
    
    def __init__(self):
        """Initialize automation service."""
        self.scheduler = AsyncIOScheduler()
        self.rules: Dict[str, AutomationRule] = {}
        self.notification_templates: Dict[str, NotificationTemplate] = {}
        self.execution_history: List[Dict] = []
        self._initialize_default_templates()
        
    async def start(self):
        """Start the automation service."""
        try:
            self.scheduler.start()
            logger.info("automation_service_started")
        except Exception as e:
            logger.error("automation_service_start_failed", error=str(e))
            raise
    
    async def stop(self):
        """Stop the automation service."""
        try:
            self.scheduler.shutdown()
            logger.info("automation_service_stopped")
        except Exception as e:
            logger.error("automation_service_stop_failed", error=str(e))
            raise
    
    def _initialize_default_templates(self):
        """Initialize default notification templates."""
        # Meeting reminder template
        meeting_reminder = NotificationTemplate(
            template_id="meeting_reminder",
            name="Intelligent Meeting Reminder",
            subject_template="Meeting Reminder: {meeting_title}",
            body_template="""
            Hi {user_name},
            
            This is a reminder for your upcoming meeting:
            
            Title: {meeting_title}
            Date: {meeting_date}
            Time: {meeting_time}
            Duration: {meeting_duration}
            
            {ai_insights}
            
            {agenda_preview}
            
            Best regards,
            Boardroom AI
            """,
            channel="email",
            personalization_fields=["user_name", "meeting_title", "meeting_date", "meeting_time", "meeting_duration", "ai_insights", "agenda_preview"]
        )
        
        # Action item follow-up template
        action_followup = NotificationTemplate(
            template_id="action_followup",
            name="Action Item Follow-up",
            subject_template="Follow-up: {action_item}",
            body_template="""
            Hi {assignee_name},
            
            This is a follow-up on your action item from {meeting_title}:
            
            Action Item: {action_item}
            Due Date: {due_date}
            Priority: {priority}
            
            {progress_insights}
            
            {recommendations}
            
            Best regards,
            Boardroom AI
            """,
            channel="email",
            personalization_fields=["assignee_name", "action_item", "meeting_title", "due_date", "priority", "progress_insights", "recommendations"]
        )
        
        # Engagement notification template
        engagement_notification = NotificationTemplate(
            template_id="engagement_alert",
            name="Engagement Alert",
            subject_template="Engagement Insight: {insight_type}",
            body_template="""
            Hi {manager_name},
            
            Our AI has detected an engagement pattern that may require attention:
            
            User: {user_name}
            Insight: {insight_description}
            Recommendation: {recommendation}
            
            {detailed_analysis}
            
            Best regards,
            Boardroom AI
            """,
            channel="email",
            personalization_fields=["manager_name", "user_name", "insight_type", "insight_description", "recommendation", "detailed_analysis"]
        )
        
        self.notification_templates.update({
            "meeting_reminder": meeting_reminder,
            "action_followup": action_followup,
            "engagement_alert": engagement_notification
        })
    
    async def create_automation_rule(self, rule_data: Dict[str, Any]) -> str:
        """Create a new automation rule."""
        try:
            ai_operations_total.labels(operation="automation_rule_creation", model="automation", status="started").inc()
            
            rule_id = str(uuid.uuid4())
            
            rule = AutomationRule(
                rule_id=rule_id,
                name=rule_data["name"],
                description=rule_data.get("description", ""),
                trigger_type=TriggerType(rule_data["trigger_type"]),
                trigger_config=rule_data["trigger_config"],
                action_type=ActionType(rule_data["action_type"]),
                action_config=rule_data["action_config"],
                conditions=rule_data.get("conditions"),
                priority=rule_data.get("priority", 1)
            )
            
            self.rules[rule_id] = rule
            
            # Schedule the rule if it's a scheduled trigger
            if rule.trigger_type == TriggerType.SCHEDULED:
                await self._schedule_rule(rule)
            
            ai_operations_total.labels(operation="automation_rule_creation", model="automation", status="success").inc()
            logger.info("automation_rule_created", rule_id=rule_id, name=rule.name)
            
            return rule_id
            
        except Exception as e:
            ai_operations_total.labels(operation="automation_rule_creation", model="automation", status="error").inc()
            logger.error("automation_rule_creation_failed", error=str(e))
            raise
    
    async def _schedule_rule(self, rule: AutomationRule):
        """Schedule a rule for execution."""
        try:
            trigger_config = rule.trigger_config
            
            if trigger_config.get("type") == "cron":
                trigger = CronTrigger(**trigger_config.get("cron_params", {}))
            elif trigger_config.get("type") == "interval":
                trigger = IntervalTrigger(**trigger_config.get("interval_params", {}))
            elif trigger_config.get("type") == "date":
                trigger = DateTrigger(**trigger_config.get("date_params", {}))
            else:
                raise ValueError(f"Unsupported trigger type: {trigger_config.get('type')}")
            
            self.scheduler.add_job(
                self._execute_rule,
                trigger=trigger,
                args=[rule.rule_id],
                id=rule.rule_id,
                name=rule.name,
                max_instances=1
            )
            
            logger.info("automation_rule_scheduled", rule_id=rule.rule_id)
            
        except Exception as e:
            logger.error("automation_rule_scheduling_failed", rule_id=rule.rule_id, error=str(e))
            raise
    
    async def trigger_rule(self, rule_id: str, trigger_data: Dict[str, Any]) -> bool:
        """Manually trigger an automation rule."""
        try:
            if rule_id not in self.rules:
                raise ValueError(f"Rule not found: {rule_id}")
            
            rule = self.rules[rule_id]
            
            if rule.status != AutomationStatus.ACTIVE:
                logger.warning("automation_rule_not_active", rule_id=rule_id, status=rule.status)
                return False
            
            # Check conditions
            if rule.conditions and not await self._evaluate_conditions(rule.conditions, trigger_data):
                logger.info("automation_rule_conditions_not_met", rule_id=rule_id)
                return False
            
            # Execute the rule
            context = ExecutionContext(
                rule_id=rule_id,
                trigger_data=trigger_data
            )
            
            success = await self._execute_rule_action(rule, context)
            
            # Update execution statistics
            rule.last_executed = datetime.now()
            rule.execution_count += 1
            if not success:
                rule.error_count += 1
            
            # Record execution history
            self.execution_history.append({
                "rule_id": rule_id,
                "timestamp": datetime.now().isoformat(),
                "success": success,
                "trigger_data": trigger_data
            })
            
            logger.info("automation_rule_executed", rule_id=rule_id, success=success)
            return success
            
        except Exception as e:
            logger.error("automation_rule_execution_failed", rule_id=rule_id, error=str(e))
            return False
    
    async def _execute_rule(self, rule_id: str):
        """Execute a scheduled automation rule."""
        await self.trigger_rule(rule_id, {"scheduled": True})
    
    async def _evaluate_conditions(self, conditions: List[Dict], trigger_data: Dict[str, Any]) -> bool:
        """Evaluate rule conditions."""
        try:
            for condition in conditions:
                condition_type = condition.get("type")
                
                if condition_type == "time_based":
                    if not self._evaluate_time_condition(condition, trigger_data):
                        return False
                elif condition_type == "data_based":
                    if not self._evaluate_data_condition(condition, trigger_data):
                        return False
                elif condition_type == "ml_based":
                    if not await self._evaluate_ml_condition(condition, trigger_data):
                        return False
            
            return True
            
        except Exception as e:
            logger.error("condition_evaluation_failed", error=str(e))
            return False
    
    def _evaluate_time_condition(self, condition: Dict, trigger_data: Dict) -> bool:
        """Evaluate time-based condition."""
        now = datetime.now()
        
        if "day_of_week" in condition:
            if now.weekday() not in condition["day_of_week"]:
                return False
        
        if "time_range" in condition:
            time_range = condition["time_range"]
            current_time = now.time()
            start_time = datetime.strptime(time_range["start"], "%H:%M").time()
            end_time = datetime.strptime(time_range["end"], "%H:%M").time()
            
            if not (start_time <= current_time <= end_time):
                return False
        
        return True
    
    def _evaluate_data_condition(self, condition: Dict, trigger_data: Dict) -> bool:
        """Evaluate data-based condition."""
        field_path = condition.get("field")
        operator = condition.get("operator")
        expected_value = condition.get("value")
        
        # Navigate nested field path
        current_data = trigger_data
        for field in field_path.split("."):
            if isinstance(current_data, dict) and field in current_data:
                current_data = current_data[field]
            else:
                return False
        
        # Evaluate condition
        if operator == "equals":
            return current_data == expected_value
        elif operator == "greater_than":
            return current_data > expected_value
        elif operator == "less_than":
            return current_data < expected_value
        elif operator == "contains":
            return expected_value in current_data
        
        return False
    
    async def _evaluate_ml_condition(self, condition: Dict, trigger_data: Dict) -> bool:
        """Evaluate ML-based condition."""
        try:
            ml_type = condition.get("ml_type")
            threshold = condition.get("threshold", 0.5)
            
            if ml_type == "sentiment":
                text = trigger_data.get("text", "")
                sentiment = await ml_service.analyze_sentiment(text)
                return sentiment["sentiment_score"] >= threshold
            elif ml_type == "engagement":
                user_data = trigger_data.get("user_data", {})
                engagement_history = trigger_data.get("engagement_history", [])
                prediction = await ml_service.predict_user_engagement(user_data, engagement_history)
                return prediction.prediction >= threshold
            
            return True
            
        except Exception as e:
            logger.error("ml_condition_evaluation_failed", error=str(e))
            return False
    
    async def _execute_rule_action(self, rule: AutomationRule, context: ExecutionContext) -> bool:
        """Execute the action for an automation rule."""
        try:
            if rule.action_type == ActionType.NOTIFICATION:
                return await self._execute_notification_action(rule, context)
            elif rule.action_type == ActionType.EMAIL:
                return await self._execute_email_action(rule, context)
            elif rule.action_type == ActionType.MEETING_CREATION:
                return await self._execute_meeting_creation_action(rule, context)
            elif rule.action_type == ActionType.REPORT_GENERATION:
                return await self._execute_report_generation_action(rule, context)
            elif rule.action_type == ActionType.ML_INFERENCE:
                return await self._execute_ml_inference_action(rule, context)
            elif rule.action_type == ActionType.WEBHOOK:
                return await self._execute_webhook_action(rule, context)
            
            return False
            
        except Exception as e:
            logger.error("automation_action_execution_failed", 
                        rule_id=rule.rule_id,
                        action_type=rule.action_type.value,
                        error=str(e))
            return False
    
    async def _execute_notification_action(self, rule: AutomationRule, context: ExecutionContext) -> bool:
        """Execute notification action."""
        try:
            config = rule.action_config
            template_id = config.get("template_id")
            recipient = config.get("recipient")
            
            if template_id not in self.notification_templates:
                raise ValueError(f"Template not found: {template_id}")
            
            template = self.notification_templates[template_id]
            
            # Personalize notification
            personalized_content = await self._personalize_notification(
                template, context.trigger_data, recipient
            )
            
            # Send notification (would integrate with actual notification service)
            logger.info("notification_sent", 
                       rule_id=rule.rule_id,
                       template_id=template_id,
                       recipient=recipient)
            
            return True
            
        except Exception as e:
            logger.error("notification_action_failed", rule_id=rule.rule_id, error=str(e))
            return False
    
    async def _personalize_notification(self, template: NotificationTemplate, data: Dict, recipient: str) -> Dict:
        """Personalize notification content using AI insights."""
        try:
            # Extract personalization data
            personalization_data = {}
            for field in template.personalization_fields:
                if field in data:
                    personalization_data[field] = data[field]
                else:
                    personalization_data[field] = self._generate_field_value(field, data)
            
            # Optimize timing if enabled
            if template.optimal_timing_enabled:
                optimal_time = await self._calculate_optimal_send_time(recipient, data)
                personalization_data["optimal_send_time"] = optimal_time
            
            # Add sentiment awareness
            if template.sentiment_awareness and "text" in data:
                sentiment = await ml_service.analyze_sentiment(data["text"])
                personalization_data["sentiment_context"] = sentiment
            
            # Format templates
            subject = template.subject_template.format(**personalization_data)
            body = template.body_template.format(**personalization_data)
            
            return {
                "subject": subject,
                "body": body,
                "channel": template.channel,
                "personalization_data": personalization_data
            }
            
        except Exception as e:
            logger.error("notification_personalization_failed", error=str(e))
            raise
    
    def _generate_field_value(self, field: str, data: Dict) -> str:
        """Generate default values for missing personalization fields."""
        defaults = {
            "user_name": "User",
            "meeting_title": "Upcoming Meeting",
            "ai_insights": "No insights available",
            "recommendations": "No recommendations available",
            "agenda_preview": "Agenda not available"
        }
        return defaults.get(field, f"[{field}]")
    
    async def _calculate_optimal_send_time(self, recipient: str, data: Dict) -> datetime:
        """Calculate optimal send time using ML."""
        try:
            # Simple heuristic (in production, use more sophisticated ML)
            now = datetime.now()
            
            # Prefer business hours
            if now.hour < 9:
                optimal_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
            elif now.hour > 17:
                optimal_time = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            else:
                optimal_time = now + timedelta(minutes=5)  # Send soon
            
            return optimal_time
            
        except Exception as e:
            logger.error("optimal_time_calculation_failed", error=str(e))
            return datetime.now() + timedelta(minutes=1)
    
    async def _execute_email_action(self, rule: AutomationRule, context: ExecutionContext) -> bool:
        """Execute email action."""
        # Would integrate with actual email service
        logger.info("email_action_executed", rule_id=rule.rule_id)
        return True
    
    async def _execute_meeting_creation_action(self, rule: AutomationRule, context: ExecutionContext) -> bool:
        """Execute meeting creation action."""
        # Would integrate with calendar service
        logger.info("meeting_creation_action_executed", rule_id=rule.rule_id)
        return True
    
    async def _execute_report_generation_action(self, rule: AutomationRule, context: ExecutionContext) -> bool:
        """Execute report generation action."""
        # Would generate reports using data
        logger.info("report_generation_action_executed", rule_id=rule.rule_id)
        return True
    
    async def _execute_ml_inference_action(self, rule: AutomationRule, context: ExecutionContext) -> bool:
        """Execute ML inference action."""
        try:
            config = rule.action_config
            inference_type = config.get("inference_type")
            
            if inference_type == "sentiment_analysis":
                text = context.trigger_data.get("text", "")
                result = await ml_service.analyze_sentiment(text)
                logger.info("ml_inference_completed", 
                           rule_id=rule.rule_id,
                           inference_type=inference_type,
                           result=result)
            
            return True
            
        except Exception as e:
            logger.error("ml_inference_action_failed", rule_id=rule.rule_id, error=str(e))
            return False
    
    async def _execute_webhook_action(self, rule: AutomationRule, context: ExecutionContext) -> bool:
        """Execute webhook action."""
        # Would send HTTP request to webhook URL
        logger.info("webhook_action_executed", rule_id=rule.rule_id)
        return True
    
    async def schedule_intelligent_reminders(self, meeting_data: Dict) -> List[str]:
        """Schedule intelligent meeting reminders."""
        try:
            reminder_rules = []
            meeting_id = meeting_data.get("meeting_id")
            meeting_date = datetime.fromisoformat(meeting_data.get("scheduled_date"))
            
            # 24-hour reminder
            reminder_24h = {
                "name": f"24h Reminder - {meeting_data.get('title')}",
                "description": "24-hour meeting reminder with agenda preview",
                "trigger_type": "scheduled",
                "trigger_config": {
                    "type": "date",
                    "date_params": {
                        "run_date": meeting_date - timedelta(hours=24)
                    }
                },
                "action_type": "notification",
                "action_config": {
                    "template_id": "meeting_reminder",
                    "recipient": meeting_data.get("participants", []),
                    "meeting_data": meeting_data
                }
            }
            
            # 2-hour reminder
            reminder_2h = {
                "name": f"2h Reminder - {meeting_data.get('title')}",
                "description": "2-hour meeting reminder with final preparation",
                "trigger_type": "scheduled",
                "trigger_config": {
                    "type": "date",
                    "date_params": {
                        "run_date": meeting_date - timedelta(hours=2)
                    }
                },
                "action_type": "notification",
                "action_config": {
                    "template_id": "meeting_reminder",
                    "recipient": meeting_data.get("participants", []),
                    "meeting_data": meeting_data
                }
            }
            
            # Create reminder rules
            rule_24h_id = await self.create_automation_rule(reminder_24h)
            rule_2h_id = await self.create_automation_rule(reminder_2h)
            
            reminder_rules = [rule_24h_id, rule_2h_id]
            
            logger.info("intelligent_reminders_scheduled", 
                       meeting_id=meeting_id,
                       reminder_count=len(reminder_rules))
            
            return reminder_rules
            
        except Exception as e:
            logger.error("intelligent_reminder_scheduling_failed", error=str(e))
            raise
    
    async def schedule_follow_up_automation(self, meeting_id: str, action_items: List[Dict]) -> List[str]:
        """Schedule automated follow-ups for action items."""
        try:
            followup_rules = []
            
            for action_item in action_items:
                due_date = datetime.fromisoformat(action_item.get("due_date"))
                
                # Follow-up reminder before due date
                followup_rule = {
                    "name": f"Action Item Follow-up - {action_item.get('item')}",
                    "description": "Automated follow-up for action item",
                    "trigger_type": "scheduled",
                    "trigger_config": {
                        "type": "date",
                        "date_params": {
                            "run_date": due_date - timedelta(days=1)
                        }
                    },
                    "action_type": "notification",
                    "action_config": {
                        "template_id": "action_followup",
                        "recipient": action_item.get("assignee"),
                        "action_item_data": action_item
                    }
                }
                
                rule_id = await self.create_automation_rule(followup_rule)
                followup_rules.append(rule_id)
            
            logger.info("followup_automation_scheduled", 
                       meeting_id=meeting_id,
                       followup_count=len(followup_rules))
            
            return followup_rules
            
        except Exception as e:
            logger.error("followup_automation_scheduling_failed", error=str(e))
            raise
    
    async def get_automation_analytics(self) -> Dict[str, Any]:
        """Get analytics for automation performance."""
        try:
            total_rules = len(self.rules)
            active_rules = len([r for r in self.rules.values() if r.status == AutomationStatus.ACTIVE])
            total_executions = sum(r.execution_count for r in self.rules.values())
            total_errors = sum(r.error_count for r in self.rules.values())
            
            success_rate = (total_executions - total_errors) / max(total_executions, 1)
            
            # Rule type distribution
            trigger_types = {}
            action_types = {}
            
            for rule in self.rules.values():
                trigger_type = rule.trigger_type.value
                action_type = rule.action_type.value
                
                trigger_types[trigger_type] = trigger_types.get(trigger_type, 0) + 1
                action_types[action_type] = action_types.get(action_type, 0) + 1
            
            analytics = {
                "total_rules": total_rules,
                "active_rules": active_rules,
                "total_executions": total_executions,
                "success_rate": success_rate,
                "error_rate": total_errors / max(total_executions, 1),
                "trigger_type_distribution": trigger_types,
                "action_type_distribution": action_types,
                "execution_history_count": len(self.execution_history),
                "templates_count": len(self.notification_templates)
            }
            
            logger.info("automation_analytics_generated", 
                       total_rules=total_rules,
                       success_rate=success_rate)
            
            return analytics
            
        except Exception as e:
            logger.error("automation_analytics_failed", error=str(e))
            raise

# Global automation service instance
automation_service = AutomationService()