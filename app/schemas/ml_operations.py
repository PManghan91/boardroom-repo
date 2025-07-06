"""Schemas for ML Operations and AI/ML features."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum
from pydantic import BaseModel, Field, validator

class MLModelType(str, Enum):
    """ML Model types available in the system."""
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    TOPIC_EXTRACTION = "topic_extraction"
    ATTENDANCE_PREDICTION = "attendance_prediction"
    OUTCOME_FORECASTING = "outcome_forecasting"
    ENGAGEMENT_OPTIMIZATION = "engagement_optimization"
    CONSENSUS_PREDICTION = "consensus_prediction"
    RISK_ANALYSIS = "risk_analysis"
    SCHEDULE_OPTIMIZATION = "schedule_optimization"

class MLOperationStatus(str, Enum):
    """Status of ML operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class RiskLevel(str, Enum):
    """Risk levels for decision analysis."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SentimentLabel(str, Enum):
    """Sentiment analysis labels."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"

class ConsensusLevel(str, Enum):
    """Consensus levels for group decisions."""
    HIGH_CONSENSUS = "high_consensus"
    MODERATE_CONSENSUS = "moderate_consensus"
    LOW_CONSENSUS = "low_consensus"
    NO_CONSENSUS = "no_consensus"

class EngagementLevel(str, Enum):
    """User engagement levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INACTIVE = "inactive"

# Base Models
class BaseMLResponse(BaseModel):
    """Base response model for ML operations."""
    operation_id: str = Field(..., description="Unique operation identifier")
    status: MLOperationStatus = Field(..., description="Operation status")
    timestamp: datetime = Field(..., description="Operation timestamp")
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")
    confidence_score: Optional[float] = Field(None, description="Confidence score 0-1")
    error_message: Optional[str] = Field(None, description="Error message if failed")

class MLModelInfo(BaseModel):
    """ML Model information."""
    model_type: MLModelType = Field(..., description="Type of ML model")
    model_name: str = Field(..., description="Name of the model")
    version: str = Field(..., description="Model version")
    accuracy: Optional[float] = Field(None, description="Model accuracy")
    last_trained: Optional[datetime] = Field(None, description="Last training timestamp")
    training_data_size: Optional[int] = Field(None, description="Training data size")
    
class TokenUsage(BaseModel):
    """Token usage information."""
    prompt_tokens: int = Field(0, description="Number of prompt tokens")
    completion_tokens: int = Field(0, description="Number of completion tokens")
    total_tokens: int = Field(0, description="Total tokens used")
    
    def calculate_total(self):
        """Calculate total tokens."""
        self.total_tokens = self.prompt_tokens + self.completion_tokens

# Meeting Intelligence Models
class MeetingTranscription(BaseModel):
    """Meeting transcription data."""
    meeting_id: str = Field(..., description="Unique meeting identifier")
    transcription_text: str = Field(..., description="Transcribed text")
    language: str = Field(default="en", description="Language of transcription")
    confidence_score: float = Field(..., description="Transcription confidence")
    duration_seconds: float = Field(..., description="Audio duration")
    word_count: int = Field(..., description="Number of words")
    speaker_segments: Optional[List[Dict]] = Field(None, description="Speaker segments")
    timestamp: datetime = Field(..., description="Transcription timestamp")

class MeetingSummary(BaseModel):
    """Meeting summary data."""
    meeting_id: str = Field(..., description="Unique meeting identifier")
    summary_text: str = Field(..., description="Meeting summary")
    key_points: List[str] = Field(..., description="Key discussion points")
    decisions_made: List[str] = Field(..., description="Decisions made")
    action_items: List[str] = Field(..., description="Action items identified")
    next_steps: List[str] = Field(..., description="Next steps")
    summary_quality_score: float = Field(..., description="Summary quality score")
    timestamp: datetime = Field(..., description="Summary timestamp")

class MeetingAgenda(BaseModel):
    """Intelligent meeting agenda."""
    agenda_id: str = Field(..., description="Unique agenda identifier")
    meeting_topic: str = Field(..., description="Main meeting topic")
    duration_minutes: int = Field(..., description="Planned duration")
    participants: List[str] = Field(..., description="Meeting participants")
    agenda_items: List[Dict] = Field(..., description="Agenda items with timing")
    ai_suggestions: List[str] = Field(..., description="AI-generated suggestions")
    previous_meeting_insights: Optional[Dict] = Field(None, description="Insights from previous meetings")
    optimization_score: float = Field(..., description="Agenda optimization score")
    timestamp: datetime = Field(..., description="Generation timestamp")

class MeetingEffectiveness(BaseModel):
    """Meeting effectiveness analysis."""
    meeting_id: str = Field(..., description="Unique meeting identifier")
    effectiveness_score: float = Field(..., description="Overall effectiveness score 0-1")
    participation_score: float = Field(..., description="Participation score 0-1")
    decision_making_score: float = Field(..., description="Decision making score 0-1")
    time_efficiency_score: float = Field(..., description="Time efficiency score 0-1")
    action_item_score: float = Field(..., description="Action item score 0-1")
    improvement_suggestions: List[str] = Field(..., description="Improvement suggestions")
    strengths: List[str] = Field(..., description="Meeting strengths")
    weaknesses: List[str] = Field(..., description="Areas for improvement")
    timestamp: datetime = Field(..., description="Analysis timestamp")

# Decision Support Models
class RiskFactor(BaseModel):
    """Risk factor analysis."""
    factor_name: str = Field(..., description="Name of risk factor")
    risk_level: RiskLevel = Field(..., description="Risk level")
    probability: float = Field(..., description="Risk probability 0-1")
    impact: float = Field(..., description="Risk impact 0-1")
    mitigation_strategies: List[str] = Field(..., description="Mitigation strategies")
    owner: Optional[str] = Field(None, description="Risk owner")

class DecisionRiskAnalysis(BaseModel):
    """Decision risk analysis."""
    decision_id: str = Field(..., description="Unique decision identifier")
    decision_topic: str = Field(..., description="Decision topic")
    overall_risk_score: float = Field(..., description="Overall risk score 0-1")
    risk_level: RiskLevel = Field(..., description="Overall risk level")
    risk_factors: List[RiskFactor] = Field(..., description="Individual risk factors")
    financial_impact: Optional[float] = Field(None, description="Financial impact")
    timeline_impact: Optional[int] = Field(None, description="Timeline impact in days")
    recommendations: List[str] = Field(..., description="Risk recommendations")
    contingency_plans: List[str] = Field(..., description="Contingency plans")
    timestamp: datetime = Field(..., description="Analysis timestamp")

class StakeholderAnalysis(BaseModel):
    """Stakeholder analysis for decisions."""
    stakeholder_id: str = Field(..., description="Stakeholder identifier")
    name: str = Field(..., description="Stakeholder name")
    role: str = Field(..., description="Stakeholder role")
    influence_level: float = Field(..., description="Influence level 0-1")
    support_level: float = Field(..., description="Support level 0-1")
    interest_level: float = Field(..., description="Interest level 0-1")
    concerns: List[str] = Field(..., description="Stakeholder concerns")
    engagement_strategy: str = Field(..., description="Engagement strategy")

class ConsensusAnalysis(BaseModel):
    """Consensus analysis for group decisions."""
    decision_id: str = Field(..., description="Unique decision identifier")
    consensus_probability: float = Field(..., description="Consensus probability 0-1")
    consensus_level: ConsensusLevel = Field(..., description="Consensus level")
    stakeholder_alignment: float = Field(..., description="Stakeholder alignment 0-1")
    supporting_stakeholders: List[str] = Field(..., description="Supporting stakeholders")
    neutral_stakeholders: List[str] = Field(..., description="Neutral stakeholders")
    opposing_stakeholders: List[str] = Field(..., description="Opposing stakeholders")
    consensus_building_strategies: List[str] = Field(..., description="Consensus building strategies")
    timeline_estimate: Optional[int] = Field(None, description="Timeline to consensus in days")
    timestamp: datetime = Field(..., description="Analysis timestamp")

# Predictive Analytics Models
class PredictionInput(BaseModel):
    """Input for predictive analytics."""
    prediction_type: str = Field(..., description="Type of prediction")
    features: Dict[str, Any] = Field(..., description="Feature values")
    historical_data: Optional[List[Dict]] = Field(None, description="Historical data")
    context: Optional[Dict] = Field(None, description="Additional context")

class PredictionResult(BaseModel):
    """Prediction result."""
    prediction_id: str = Field(..., description="Unique prediction identifier")
    prediction_type: str = Field(..., description="Type of prediction")
    predicted_value: Union[float, int, str, bool] = Field(..., description="Predicted value")
    confidence_score: float = Field(..., description="Confidence score 0-1")
    confidence_interval: Optional[Tuple[float, float]] = Field(None, description="Confidence interval")
    feature_importance: Optional[Dict[str, float]] = Field(None, description="Feature importance scores")
    prediction_factors: List[str] = Field(..., description="Factors affecting prediction")
    recommendations: List[str] = Field(..., description="Recommendations based on prediction")
    timestamp: datetime = Field(..., description="Prediction timestamp")
    expires_at: Optional[datetime] = Field(None, description="Prediction expiration")

class AttendancePrediction(BaseModel):
    """Meeting attendance prediction."""
    meeting_id: str = Field(..., description="Unique meeting identifier")
    predicted_attendance_rate: float = Field(..., description="Predicted attendance rate 0-1")
    expected_attendees: int = Field(..., description="Expected number of attendees")
    total_invited: int = Field(..., description="Total number invited")
    prediction_factors: List[str] = Field(..., description="Factors affecting attendance")
    optimization_suggestions: List[str] = Field(..., description="Suggestions to improve attendance")
    confidence_score: float = Field(..., description="Prediction confidence 0-1")
    timestamp: datetime = Field(..., description="Prediction timestamp")

class EngagementPrediction(BaseModel):
    """User engagement prediction."""
    user_id: str = Field(..., description="User identifier")
    predicted_engagement: EngagementLevel = Field(..., description="Predicted engagement level")
    engagement_score: float = Field(..., description="Engagement score 0-1")
    engagement_factors: List[str] = Field(..., description="Factors affecting engagement")
    improvement_strategies: List[str] = Field(..., description="Strategies to improve engagement")
    historical_trend: Optional[str] = Field(None, description="Historical engagement trend")
    confidence_score: float = Field(..., description="Prediction confidence 0-1")
    timestamp: datetime = Field(..., description="Prediction timestamp")

# Natural Language Processing Models
class SentimentAnalysis(BaseModel):
    """Sentiment analysis result."""
    text_id: str = Field(..., description="Text identifier")
    sentiment_label: SentimentLabel = Field(..., description="Sentiment label")
    sentiment_score: float = Field(..., description="Sentiment score -1 to 1")
    confidence_score: float = Field(..., description="Confidence score 0-1")
    positive_score: float = Field(..., description="Positive sentiment score")
    negative_score: float = Field(..., description="Negative sentiment score")
    neutral_score: float = Field(..., description="Neutral sentiment score")
    emotions: Optional[Dict[str, float]] = Field(None, description="Emotion scores")
    key_phrases: List[str] = Field(..., description="Key phrases")
    timestamp: datetime = Field(..., description="Analysis timestamp")

class TopicAnalysis(BaseModel):
    """Topic analysis result."""
    text_id: str = Field(..., description="Text identifier")
    topics: List[Dict[str, Any]] = Field(..., description="Extracted topics")
    topic_distribution: Dict[str, float] = Field(..., description="Topic distribution")
    main_topic: str = Field(..., description="Main topic")
    topic_confidence: float = Field(..., description="Topic confidence score")
    keywords: List[str] = Field(..., description="Key topic keywords")
    categories: List[str] = Field(..., description="Topic categories")
    timestamp: datetime = Field(..., description="Analysis timestamp")

class SemanticSearchResult(BaseModel):
    """Semantic search result."""
    query: str = Field(..., description="Search query")
    document_id: str = Field(..., description="Document identifier")
    document_title: Optional[str] = Field(None, description="Document title")
    document_content: str = Field(..., description="Document content")
    similarity_score: float = Field(..., description="Similarity score 0-1")
    relevance_level: str = Field(..., description="Relevance level")
    highlighted_passages: List[str] = Field(..., description="Highlighted relevant passages")
    semantic_tags: List[str] = Field(..., description="Semantic tags")
    timestamp: datetime = Field(..., description="Search timestamp")

# Automation Models
class AutomationRule(BaseModel):
    """Automation rule definition."""
    rule_id: str = Field(..., description="Unique rule identifier")
    rule_name: str = Field(..., description="Rule name")
    rule_type: str = Field(..., description="Type of automation rule")
    trigger_conditions: Dict[str, Any] = Field(..., description="Trigger conditions")
    actions: List[Dict[str, Any]] = Field(..., description="Actions to execute")
    priority: int = Field(default=1, description="Rule priority")
    is_active: bool = Field(default=True, description="Whether rule is active")
    created_at: datetime = Field(..., description="Rule creation timestamp")
    last_executed: Optional[datetime] = Field(None, description="Last execution timestamp")
    execution_count: int = Field(default=0, description="Number of executions")

class NotificationSchedule(BaseModel):
    """Intelligent notification schedule."""
    schedule_id: str = Field(..., description="Unique schedule identifier")
    user_id: str = Field(..., description="Target user identifier")
    notification_type: str = Field(..., description="Type of notification")
    content: str = Field(..., description="Notification content")
    scheduled_time: datetime = Field(..., description="Scheduled delivery time")
    optimal_time: Optional[datetime] = Field(None, description="AI-optimized delivery time")
    delivery_channel: str = Field(..., description="Delivery channel")
    priority: int = Field(default=1, description="Notification priority")
    personalization_data: Optional[Dict] = Field(None, description="Personalization data")
    status: str = Field(default="scheduled", description="Notification status")

class ScheduleOptimization(BaseModel):
    """Schedule optimization result."""
    optimization_id: str = Field(..., description="Unique optimization identifier")
    original_schedule: List[Dict] = Field(..., description="Original schedule")
    optimized_schedule: List[Dict] = Field(..., description="Optimized schedule")
    optimization_score: float = Field(..., description="Optimization score 0-1")
    improvements: List[str] = Field(..., description="Optimization improvements")
    conflicts_resolved: int = Field(..., description="Number of conflicts resolved")
    efficiency_gain: float = Field(..., description="Efficiency gain percentage")
    recommendations: List[str] = Field(..., description="Schedule recommendations")
    timestamp: datetime = Field(..., description="Optimization timestamp")

# Model Management Models
class ModelTrainingRequest(BaseModel):
    """ML model training request."""
    model_type: MLModelType = Field(..., description="Type of model to train")
    training_data: Dict[str, Any] = Field(..., description="Training data")
    hyperparameters: Optional[Dict[str, Any]] = Field(None, description="Model hyperparameters")
    validation_split: float = Field(default=0.2, description="Validation split ratio")
    training_notes: Optional[str] = Field(None, description="Training notes")

class ModelTrainingResult(BaseModel):
    """ML model training result."""
    training_id: str = Field(..., description="Unique training identifier")
    model_type: MLModelType = Field(..., description="Type of model trained")
    model_version: str = Field(..., description="New model version")
    training_accuracy: float = Field(..., description="Training accuracy")
    validation_accuracy: float = Field(..., description="Validation accuracy")
    training_loss: float = Field(..., description="Training loss")
    validation_loss: float = Field(..., description="Validation loss")
    training_duration: float = Field(..., description="Training duration in seconds")
    model_size: int = Field(..., description="Model size in bytes")
    deployment_ready: bool = Field(..., description="Whether model is ready for deployment")
    timestamp: datetime = Field(..., description="Training completion timestamp")

class ModelDeploymentRequest(BaseModel):
    """ML model deployment request."""
    model_type: MLModelType = Field(..., description="Type of model to deploy")
    model_version: str = Field(..., description="Model version to deploy")
    deployment_environment: str = Field(..., description="Deployment environment")
    rollout_strategy: str = Field(default="blue_green", description="Rollout strategy")
    health_check_url: Optional[str] = Field(None, description="Health check URL")

class ModelDeploymentResult(BaseModel):
    """ML model deployment result."""
    deployment_id: str = Field(..., description="Unique deployment identifier")
    model_type: MLModelType = Field(..., description="Type of model deployed")
    model_version: str = Field(..., description="Model version deployed")
    deployment_status: str = Field(..., description="Deployment status")
    endpoint_url: Optional[str] = Field(None, description="Model endpoint URL")
    deployment_environment: str = Field(..., description="Deployment environment")
    health_status: str = Field(..., description="Model health status")
    timestamp: datetime = Field(..., description="Deployment timestamp")

class ModelMetrics(BaseModel):
    """ML model performance metrics."""
    model_type: MLModelType = Field(..., description="Type of model")
    model_version: str = Field(..., description="Model version")
    accuracy: float = Field(..., description="Model accuracy")
    precision: float = Field(..., description="Model precision")
    recall: float = Field(..., description="Model recall")
    f1_score: float = Field(..., description="F1 score")
    inference_time_ms: float = Field(..., description="Average inference time")
    throughput_per_second: float = Field(..., description="Throughput per second")
    memory_usage_mb: float = Field(..., description="Memory usage in MB")
    error_rate: float = Field(..., description="Error rate")
    last_updated: datetime = Field(..., description="Last metrics update")

# Batch Processing Models
class BatchProcessingRequest(BaseModel):
    """Batch processing request."""
    batch_id: str = Field(..., description="Unique batch identifier")
    processing_type: str = Field(..., description="Type of batch processing")
    items: List[Dict[str, Any]] = Field(..., description="Items to process")
    processing_options: Optional[Dict] = Field(None, description="Processing options")
    priority: int = Field(default=1, description="Batch priority")
    callback_url: Optional[str] = Field(None, description="Callback URL for results")

class BatchProcessingResult(BaseModel):
    """Batch processing result."""
    batch_id: str = Field(..., description="Unique batch identifier")
    processing_type: str = Field(..., description="Type of batch processing")
    total_items: int = Field(..., description="Total items processed")
    successful_items: int = Field(..., description="Successfully processed items")
    failed_items: int = Field(..., description="Failed items")
    processing_time_seconds: float = Field(..., description="Total processing time")
    results: List[Dict[str, Any]] = Field(..., description="Processing results")
    errors: List[Dict[str, str]] = Field(..., description="Processing errors")
    timestamp: datetime = Field(..., description="Completion timestamp")

# Analytics Dashboard Models
class AIAnalyticsDashboard(BaseModel):
    """AI analytics dashboard data."""
    dashboard_id: str = Field(..., description="Dashboard identifier")
    ai_operations_summary: Dict[str, Any] = Field(..., description="AI operations summary")
    model_performance_summary: Dict[str, Any] = Field(..., description="Model performance summary")
    usage_statistics: Dict[str, Any] = Field(..., description="Usage statistics")
    trend_analysis: Dict[str, Any] = Field(..., description="Trend analysis")
    alerts: List[Dict[str, str]] = Field(..., description="System alerts")
    recommendations: List[str] = Field(..., description="System recommendations")
    last_updated: datetime = Field(..., description="Last dashboard update")

# Validation helpers
class BaseMLRequest(BaseModel):
    """Base request model for ML operations."""
    
    @validator('*', pre=True)
    def empty_str_to_none(cls, v):
        if v == '':
            return None
        return v

class MLHealthCheck(BaseModel):
    """ML service health check."""
    service_status: str = Field(..., description="Service status")
    models_loaded: int = Field(..., description="Number of models loaded")
    active_operations: int = Field(..., description="Active operations count")
    total_operations: int = Field(..., description="Total operations processed")
    error_rate: float = Field(..., description="Error rate")
    average_response_time: float = Field(..., description="Average response time")
    last_health_check: datetime = Field(..., description="Last health check timestamp")
    system_resources: Dict[str, Any] = Field(..., description="System resource usage")
    model_statuses: Dict[str, str] = Field(..., description="Individual model statuses")