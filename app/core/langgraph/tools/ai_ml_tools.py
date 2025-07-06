"""Advanced AI/ML tools for LangGraph integration."""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.core.metrics import ai_tool_executions_total, ai_tool_duration_seconds
from app.core.exceptions import raise_tool_execution_error
from app.services.ml_service import ml_service, MLModelType

# Input Models for AI/ML Tools
class MeetingIntelligenceInput(BaseModel):
    """Input for meeting intelligence analysis."""
    meeting_id: str = Field(description="Unique meeting identifier")
    transcription: str = Field(description="Meeting transcription text")
    participants: List[str] = Field(description="List of meeting participants")
    duration_minutes: int = Field(description="Meeting duration in minutes")
    meeting_type: Optional[str] = Field(default="regular", description="Type of meeting")

class DecisionAnalysisInput(BaseModel):
    """Input for decision analysis."""
    decision_topic: str = Field(description="Decision topic to analyze")
    options: List[str] = Field(description="Available decision options")
    criteria: Optional[List[str]] = Field(default=None, description="Decision criteria")
    budget_impact: Optional[float] = Field(default=0, description="Budget impact")
    timeline_months: Optional[int] = Field(default=6, description="Timeline in months")
    stakeholders: Optional[List[Dict]] = Field(default=None, description="Stakeholder information")

class PredictiveAnalysisInput(BaseModel):
    """Input for predictive analysis."""
    prediction_type: str = Field(description="Type of prediction (attendance, engagement, etc.)")
    target_data: Dict[str, Any] = Field(description="Target data for prediction")
    historical_data: List[Dict] = Field(description="Historical data for context")
    features: Optional[Dict[str, Any]] = Field(default=None, description="Additional features")

class SentimentAnalysisInput(BaseModel):
    """Input for sentiment analysis."""
    text: str = Field(description="Text to analyze for sentiment")
    context: Optional[str] = Field(default=None, description="Additional context")
    language: Optional[str] = Field(default="en", description="Text language")

class TopicExtractionInput(BaseModel):
    """Input for topic extraction."""
    text: str = Field(description="Text to extract topics from")
    num_topics: int = Field(default=5, description="Number of topics to extract")
    min_topic_size: int = Field(default=2, description="Minimum topic size")

class SemanticSearchInput(BaseModel):
    """Input for semantic search."""
    query: str = Field(description="Search query")
    documents: List[str] = Field(description="Documents to search")
    max_results: int = Field(default=10, description="Maximum results to return")
    similarity_threshold: float = Field(default=0.1, description="Minimum similarity threshold")

class EngagementAnalysisInput(BaseModel):
    """Input for engagement analysis."""
    user_id: str = Field(description="User identifier")
    user_data: Dict[str, Any] = Field(description="User data")
    engagement_history: List[Dict] = Field(description="Historical engagement data")
    analysis_period: int = Field(default=30, description="Analysis period in days")

class ScheduleOptimizationInput(BaseModel):
    """Input for schedule optimization."""
    meeting_requests: List[Dict] = Field(description="Meeting requests to optimize")
    participants: List[Dict] = Field(description="Participant availability data")
    constraints: Optional[Dict] = Field(default=None, description="Scheduling constraints")
    optimization_goal: str = Field(default="maximize_attendance", description="Optimization goal")

# AI/ML Tools Implementation
class MeetingIntelligenceTool(BaseTool):
    """Tool for comprehensive meeting intelligence analysis."""
    
    name: str = "meeting_intelligence_analyzer"
    description: str = "Analyzes meetings to extract intelligence including summary, topics, sentiment, and effectiveness"
    args_schema: type = MeetingIntelligenceInput

    def _run(self, **kwargs) -> str:
        """Execute the tool synchronously."""
        return asyncio.run(self._arun(**kwargs))

    async def _arun(self, **kwargs) -> str:
        """Execute the tool asynchronously."""
        return await self._analyze_meeting_intelligence(**kwargs)

    async def _analyze_meeting_intelligence(
        self,
        meeting_id: str,
        transcription: str,
        participants: List[str],
        duration_minutes: int,
        meeting_type: str = "regular"
    ) -> str:
        """Analyze meeting intelligence."""
        
        with ai_tool_duration_seconds.labels(tool_name=self.name).time():
            try:
                ai_tool_executions_total.labels(tool_name=self.name, status="started").inc()
                
                # Generate summary
                summary = await ml_service.summarize_meeting(transcription, meeting_id)
                
                # Extract topics
                topics = await ml_service.extract_topics(transcription, num_topics=5)
                key_topics = [topic['topic'] for topic in topics]
                
                # Analyze sentiment
                sentiment = await ml_service.analyze_sentiment(transcription)
                
                # Extract action items
                action_items = await ml_service.extract_action_items(transcription)
                
                # Calculate effectiveness
                meeting_data = {
                    'meeting_id': meeting_id,
                    'participants': participants,
                    'duration_minutes': duration_minutes,
                    'action_items': action_items,
                    'decisions_made': [],  # Would be extracted from transcription
                    'meeting_type': meeting_type
                }
                effectiveness_score = await ml_service.calculate_meeting_effectiveness(meeting_data)
                
                # Generate recommendations
                recommendations = []
                if effectiveness_score < 0.6:
                    recommendations.append("Consider improving meeting structure and agenda")
                if len(action_items) == 0:
                    recommendations.append("Ensure concrete action items are defined")
                if sentiment['sentiment_label'] == 'negative':
                    recommendations.append("Address concerns raised during the meeting")
                
                intelligence = {
                    "meeting_id": meeting_id,
                    "summary": summary,
                    "key_topics": key_topics,
                    "sentiment_analysis": sentiment,
                    "action_items": action_items,
                    "effectiveness_score": effectiveness_score,
                    "participation_rate": len(participants) / max(len(participants), 1),
                    "recommendations": recommendations,
                    "meeting_insights": {
                        "duration_efficiency": "optimal" if 30 <= duration_minutes <= 90 else "suboptimal",
                        "topic_diversity": len(key_topics),
                        "sentiment_trend": sentiment['sentiment_label'],
                        "action_item_density": len(action_items) / max(duration_minutes, 1)
                    }
                }
                
                ai_tool_executions_total.labels(tool_name=self.name, status="success").inc()
                logger.info("meeting_intelligence_analyzed", 
                           meeting_id=meeting_id, 
                           effectiveness=effectiveness_score,
                           topics_count=len(key_topics))
                
                return json.dumps(intelligence, indent=2)
                
            except Exception as e:
                ai_tool_executions_total.labels(tool_name=self.name, status="error").inc()
                logger.error("meeting_intelligence_analysis_failed", 
                            meeting_id=meeting_id, 
                            error=str(e))
                raise_tool_execution_error(f"Failed to analyze meeting intelligence: {str(e)}", self.name)

class DecisionSupportTool(BaseTool):
    """Tool for AI-powered decision support analysis."""
    
    name: str = "decision_support_analyzer"
    description: str = "Provides comprehensive decision support including risk analysis and consensus prediction"
    args_schema: type = DecisionAnalysisInput

    def _run(self, **kwargs) -> str:
        """Execute the tool synchronously."""
        return asyncio.run(self._arun(**kwargs))

    async def _arun(self, **kwargs) -> str:
        """Execute the tool asynchronously."""
        return await self._analyze_decision_support(**kwargs)

    async def _analyze_decision_support(
        self,
        decision_topic: str,
        options: List[str],
        criteria: Optional[List[str]] = None,
        budget_impact: float = 0,
        timeline_months: int = 6,
        stakeholders: Optional[List[Dict]] = None
    ) -> str:
        """Analyze decision support."""
        
        with ai_tool_duration_seconds.labels(tool_name=self.name).time():
            try:
                ai_tool_executions_total.labels(tool_name=self.name, status="started").inc()
                
                # Prepare decision data
                decision_data = {
                    'budget_impact': budget_impact,
                    'complexity_score': min(len(options) * 2, 10),
                    'strategic_impact': 'high' if budget_impact > 100000 else 'medium',
                    'timeline_months': timeline_months
                }
                
                # Analyze risk
                risk_analysis = await ml_service.analyze_decision_risk(decision_data)
                
                # Predict consensus if stakeholders provided
                consensus_prediction = None
                if stakeholders:
                    consensus_prediction = await ml_service.predict_consensus(decision_data, stakeholders)
                
                # Generate decision matrix
                decision_matrix = []
                for option in options:
                    option_analysis = {
                        'option': option,
                        'risk_score': risk_analysis['overall_risk_score'],
                        'feasibility': 0.8,  # Would be calculated based on real criteria
                        'cost_impact': budget_impact / len(options),
                        'timeline_impact': timeline_months,
                        'stakeholder_support': 0.7 if consensus_prediction else 0.5
                    }
                    decision_matrix.append(option_analysis)
                
                # Generate recommendations
                recommendations = []
                if risk_analysis['overall_risk_score'] > 0.7:
                    recommendations.append("High risk decision - recommend thorough review")
                if consensus_prediction and consensus_prediction['consensus_probability'] < 0.5:
                    recommendations.append("Low consensus predicted - engage stakeholders")
                if budget_impact > 500000:
                    recommendations.append("High budget impact - consider phased approach")
                
                decision_support = {
                    "decision_topic": decision_topic,
                    "options": options,
                    "criteria": criteria or ["Cost", "Risk", "Timeline", "Feasibility"],
                    "risk_analysis": risk_analysis,
                    "consensus_prediction": consensus_prediction,
                    "decision_matrix": decision_matrix,
                    "recommendations": recommendations,
                    "decision_complexity": "high" if len(options) > 4 else "medium",
                    "urgency_level": "high" if timeline_months < 3 else "medium",
                    "stakeholder_impact": {
                        "affected_stakeholders": len(stakeholders) if stakeholders else 0,
                        "impact_level": "high" if budget_impact > 100000 else "medium"
                    }
                }
                
                ai_tool_executions_total.labels(tool_name=self.name, status="success").inc()
                logger.info("decision_support_analyzed", 
                           topic=decision_topic,
                           options_count=len(options),
                           risk_score=risk_analysis['overall_risk_score'])
                
                return json.dumps(decision_support, indent=2)
                
            except Exception as e:
                ai_tool_executions_total.labels(tool_name=self.name, status="error").inc()
                logger.error("decision_support_analysis_failed", 
                            topic=decision_topic,
                            error=str(e))
                raise_tool_execution_error(f"Failed to analyze decision support: {str(e)}", self.name)

class PredictiveAnalyticsTool(BaseTool):
    """Tool for predictive analytics using ML models."""
    
    name: str = "predictive_analytics_engine"
    description: str = "Performs predictive analytics for various business scenarios"
    args_schema: type = PredictiveAnalysisInput

    def _run(self, **kwargs) -> str:
        """Execute the tool synchronously."""
        return asyncio.run(self._arun(**kwargs))

    async def _arun(self, **kwargs) -> str:
        """Execute the tool asynchronously."""
        return await self._perform_predictive_analysis(**kwargs)

    async def _perform_predictive_analysis(
        self,
        prediction_type: str,
        target_data: Dict[str, Any],
        historical_data: List[Dict],
        features: Optional[Dict[str, Any]] = None
    ) -> str:
        """Perform predictive analysis."""
        
        with ai_tool_duration_seconds.labels(tool_name=self.name).time():
            try:
                ai_tool_executions_total.labels(tool_name=self.name, status="started").inc()
                
                predictions = {}
                
                # Attendance prediction
                if prediction_type in ["attendance", "all"]:
                    if 'scheduled_date' in target_data:
                        attendance_prediction = await ml_service.predict_meeting_attendance(
                            target_data, historical_data
                        )
                        predictions["attendance"] = attendance_prediction.__dict__
                
                # Engagement prediction
                if prediction_type in ["engagement", "all"]:
                    if 'user_id' in target_data:
                        user_data = target_data
                        engagement_prediction = await ml_service.predict_user_engagement(
                            user_data, historical_data
                        )
                        predictions["engagement"] = engagement_prediction.__dict__
                
                # Outcome forecasting
                if prediction_type in ["outcome", "all"]:
                    outcome_prediction = {
                        "success_probability": 0.75,
                        "completion_timeline": f"{target_data.get('timeline_months', 6)} months",
                        "resource_requirements": "medium",
                        "risk_factors": ["budget", "timeline", "stakeholder alignment"],
                        "success_factors": ["clear objectives", "stakeholder support", "adequate resources"]
                    }
                    predictions["outcome"] = outcome_prediction
                
                # Generate insights
                insights = []
                if predictions:
                    for pred_type, pred_data in predictions.items():
                        if pred_type == "attendance":
                            if pred_data.get('prediction_value', 0) < 0.6:
                                insights.append(f"Low attendance predicted for {pred_type}")
                        elif pred_type == "engagement":
                            if pred_data.get('prediction', 0) < 0.5:
                                insights.append(f"Low engagement predicted for {pred_type}")
                
                predictive_analysis = {
                    "prediction_type": prediction_type,
                    "target_data": target_data,
                    "predictions": predictions,
                    "insights": insights,
                    "confidence_level": "high" if len(historical_data) > 10 else "medium",
                    "data_quality": "good" if len(historical_data) > 5 else "limited",
                    "recommendations": [
                        "Monitor actual results against predictions",
                        "Update models with new data regularly",
                        "Consider external factors not captured in historical data"
                    ]
                }
                
                ai_tool_executions_total.labels(tool_name=self.name, status="success").inc()
                logger.info("predictive_analysis_completed", 
                           prediction_type=prediction_type,
                           predictions_count=len(predictions))
                
                return json.dumps(predictive_analysis, indent=2)
                
            except Exception as e:
                ai_tool_executions_total.labels(tool_name=self.name, status="error").inc()
                logger.error("predictive_analysis_failed", 
                            prediction_type=prediction_type,
                            error=str(e))
                raise_tool_execution_error(f"Failed to perform predictive analysis: {str(e)}", self.name)

class SentimentAnalysisTool(BaseTool):
    """Tool for sentiment analysis of text content."""
    
    name: str = "sentiment_analyzer"
    description: str = "Analyzes sentiment of text content with detailed insights"
    args_schema: type = SentimentAnalysisInput

    def _run(self, **kwargs) -> str:
        """Execute the tool synchronously."""
        return asyncio.run(self._arun(**kwargs))

    async def _arun(self, **kwargs) -> str:
        """Execute the tool asynchronously."""
        return await self._analyze_sentiment(**kwargs)

    async def _analyze_sentiment(
        self,
        text: str,
        context: Optional[str] = None,
        language: str = "en"
    ) -> str:
        """Analyze sentiment of text."""
        
        with ai_tool_duration_seconds.labels(tool_name=self.name).time():
            try:
                ai_tool_executions_total.labels(tool_name=self.name, status="started").inc()
                
                # Analyze sentiment
                sentiment = await ml_service.analyze_sentiment(text)
                
                # Add context-aware insights
                if context:
                    context_sentiment = await ml_service.analyze_sentiment(context)
                    sentiment['context_sentiment'] = context_sentiment
                
                # Generate insights
                insights = []
                if sentiment['sentiment_label'] == 'negative':
                    insights.append("Negative sentiment detected - may require attention")
                elif sentiment['sentiment_label'] == 'positive':
                    insights.append("Positive sentiment detected - good engagement")
                
                if abs(sentiment['sentiment_score']) < 0.2:
                    insights.append("Neutral sentiment - content may benefit from more engaging language")
                
                sentiment_analysis = {
                    "text_preview": text[:100] + "..." if len(text) > 100 else text,
                    "sentiment_result": sentiment,
                    "language": language,
                    "text_length": len(text),
                    "word_count": len(text.split()),
                    "insights": insights,
                    "recommendations": [
                        "Monitor sentiment trends over time",
                        "Address negative sentiment promptly",
                        "Leverage positive sentiment for engagement"
                    ]
                }
                
                ai_tool_executions_total.labels(tool_name=self.name, status="success").inc()
                logger.info("sentiment_analyzed", 
                           sentiment=sentiment['sentiment_label'],
                           score=sentiment['sentiment_score'])
                
                return json.dumps(sentiment_analysis, indent=2)
                
            except Exception as e:
                ai_tool_executions_total.labels(tool_name=self.name, status="error").inc()
                logger.error("sentiment_analysis_failed", error=str(e))
                raise_tool_execution_error(f"Failed to analyze sentiment: {str(e)}", self.name)

class TopicExtractionTool(BaseTool):
    """Tool for extracting topics from text using NLP."""
    
    name: str = "topic_extractor"
    description: str = "Extracts and categorizes topics from text content"
    args_schema: type = TopicExtractionInput

    def _run(self, **kwargs) -> str:
        """Execute the tool synchronously."""
        return asyncio.run(self._arun(**kwargs))

    async def _arun(self, **kwargs) -> str:
        """Execute the tool asynchronously."""
        return await self._extract_topics(**kwargs)

    async def _extract_topics(
        self,
        text: str,
        num_topics: int = 5,
        min_topic_size: int = 2
    ) -> str:
        """Extract topics from text."""
        
        with ai_tool_duration_seconds.labels(tool_name=self.name).time():
            try:
                ai_tool_executions_total.labels(tool_name=self.name, status="started").inc()
                
                # Extract topics
                topics = await ml_service.extract_topics(text, num_topics)
                
                # Filter by minimum size
                filtered_topics = [topic for topic in topics if topic['frequency'] >= min_topic_size]
                
                # Categorize topics
                topic_categories = {}
                for topic in filtered_topics:
                    category = topic.get('category', 'general')
                    if category not in topic_categories:
                        topic_categories[category] = []
                    topic_categories[category].append(topic)
                
                # Generate insights
                insights = []
                if len(filtered_topics) > 8:
                    insights.append("High topic diversity detected")
                elif len(filtered_topics) < 3:
                    insights.append("Low topic diversity - content may be too focused")
                
                most_frequent_category = max(topic_categories.keys(), 
                                           key=lambda k: len(topic_categories[k]),
                                           default='general')
                insights.append(f"Primary topic category: {most_frequent_category}")
                
                topic_extraction = {
                    "text_preview": text[:100] + "..." if len(text) > 100 else text,
                    "extracted_topics": filtered_topics,
                    "topic_categories": topic_categories,
                    "topic_statistics": {
                        "total_topics": len(filtered_topics),
                        "categories_count": len(topic_categories),
                        "most_frequent_category": most_frequent_category,
                        "topic_diversity_score": len(filtered_topics) / max(num_topics, 1)
                    },
                    "insights": insights,
                    "recommendations": [
                        "Focus on high-frequency topics for key messaging",
                        "Address underrepresented important topics",
                        "Monitor topic trends over time"
                    ]
                }
                
                ai_tool_executions_total.labels(tool_name=self.name, status="success").inc()
                logger.info("topics_extracted", 
                           topics_count=len(filtered_topics),
                           categories_count=len(topic_categories))
                
                return json.dumps(topic_extraction, indent=2)
                
            except Exception as e:
                ai_tool_executions_total.labels(tool_name=self.name, status="error").inc()
                logger.error("topic_extraction_failed", error=str(e))
                raise_tool_execution_error(f"Failed to extract topics: {str(e)}", self.name)

class SemanticSearchTool(BaseTool):
    """Tool for semantic search across documents."""
    
    name: str = "semantic_search_engine"
    description: str = "Performs semantic search to find relevant documents and content"
    args_schema: type = SemanticSearchInput

    def _run(self, **kwargs) -> str:
        """Execute the tool synchronously."""
        return asyncio.run(self._arun(**kwargs))

    async def _arun(self, **kwargs) -> str:
        """Execute the tool asynchronously."""
        return await self._perform_semantic_search(**kwargs)

    async def _perform_semantic_search(
        self,
        query: str,
        documents: List[str],
        max_results: int = 10,
        similarity_threshold: float = 0.1
    ) -> str:
        """Perform semantic search."""
        
        with ai_tool_duration_seconds.labels(tool_name=self.name).time():
            try:
                ai_tool_executions_total.labels(tool_name=self.name, status="started").inc()
                
                # Perform semantic search
                results = await ml_service.semantic_search(query, documents)
                
                # Filter by similarity threshold
                filtered_results = [
                    result for result in results 
                    if result['similarity_score'] >= similarity_threshold
                ]
                
                # Limit results
                limited_results = filtered_results[:max_results]
                
                # Generate insights
                insights = []
                if len(limited_results) == 0:
                    insights.append("No relevant documents found - consider broadening search terms")
                elif len(limited_results) == len(documents):
                    insights.append("All documents are relevant - query may be too broad")
                
                avg_similarity = sum(r['similarity_score'] for r in limited_results) / max(len(limited_results), 1)
                insights.append(f"Average relevance score: {avg_similarity:.2f}")
                
                search_results = {
                    "query": query,
                    "total_documents_searched": len(documents),
                    "results_found": len(limited_results),
                    "results": limited_results,
                    "search_statistics": {
                        "average_similarity": avg_similarity,
                        "highest_similarity": max([r['similarity_score'] for r in limited_results]) if limited_results else 0,
                        "relevance_distribution": {
                            "high": len([r for r in limited_results if r['similarity_score'] > 0.5]),
                            "medium": len([r for r in limited_results if 0.2 <= r['similarity_score'] <= 0.5]),
                            "low": len([r for r in limited_results if r['similarity_score'] < 0.2])
                        }
                    },
                    "insights": insights,
                    "recommendations": [
                        "Review high-similarity results first",
                        "Refine query if results are too broad or narrow",
                        "Consider document preprocessing for better results"
                    ]
                }
                
                ai_tool_executions_total.labels(tool_name=self.name, status="success").inc()
                logger.info("semantic_search_completed", 
                           query=query,
                           results_count=len(limited_results))
                
                return json.dumps(search_results, indent=2)
                
            except Exception as e:
                ai_tool_executions_total.labels(tool_name=self.name, status="error").inc()
                logger.error("semantic_search_failed", query=query, error=str(e))
                raise_tool_execution_error(f"Failed to perform semantic search: {str(e)}", self.name)

class EngagementAnalysisTool(BaseTool):
    """Tool for analyzing and predicting user engagement."""
    
    name: str = "engagement_analyzer"
    description: str = "Analyzes user engagement patterns and predicts future engagement"
    args_schema: type = EngagementAnalysisInput

    def _run(self, **kwargs) -> str:
        """Execute the tool synchronously."""
        return asyncio.run(self._arun(**kwargs))

    async def _arun(self, **kwargs) -> str:
        """Execute the tool asynchronously."""
        return await self._analyze_engagement(**kwargs)

    async def _analyze_engagement(
        self,
        user_id: str,
        user_data: Dict[str, Any],
        engagement_history: List[Dict],
        analysis_period: int = 30
    ) -> str:
        """Analyze user engagement."""
        
        with ai_tool_duration_seconds.labels(tool_name=self.name).time():
            try:
                ai_tool_executions_total.labels(tool_name=self.name, status="started").inc()
                
                # Predict engagement
                engagement_prediction = await ml_service.predict_user_engagement(
                    user_data, engagement_history
                )
                
                # Analyze engagement trends
                recent_engagement = engagement_history[-analysis_period:] if len(engagement_history) > analysis_period else engagement_history
                
                engagement_scores = [e.get('engagement_score', 0.5) for e in recent_engagement]
                avg_engagement = sum(engagement_scores) / max(len(engagement_scores), 1)
                
                # Calculate trend
                if len(engagement_scores) >= 2:
                    trend = "improving" if engagement_scores[-1] > engagement_scores[0] else "declining"
                else:
                    trend = "stable"
                
                # Generate insights
                insights = []
                if avg_engagement < 0.4:
                    insights.append("Low engagement detected - intervention recommended")
                elif avg_engagement > 0.8:
                    insights.append("High engagement - excellent participation")
                
                if trend == "declining":
                    insights.append("Engagement is declining - investigate causes")
                elif trend == "improving":
                    insights.append("Engagement is improving - maintain current strategies")
                
                engagement_analysis = {
                    "user_id": user_id,
                    "engagement_prediction": engagement_prediction.__dict__,
                    "historical_analysis": {
                        "average_engagement": avg_engagement,
                        "engagement_trend": trend,
                        "data_points": len(engagement_history),
                        "analysis_period_days": analysis_period
                    },
                    "engagement_factors": {
                        "role_influence": user_data.get('role', 'unknown'),
                        "activity_level": "high" if len(engagement_history) > 20 else "medium",
                        "participation_consistency": "consistent" if len(set(engagement_scores)) < 3 else "variable"
                    },
                    "insights": insights,
                    "recommendations": engagement_prediction.metadata.get('recommendations', [])
                }
                
                ai_tool_executions_total.labels(tool_name=self.name, status="success").inc()
                logger.info("engagement_analyzed", 
                           user_id=user_id,
                           predicted_engagement=engagement_prediction.prediction)
                
                return json.dumps(engagement_analysis, indent=2)
                
            except Exception as e:
                ai_tool_executions_total.labels(tool_name=self.name, status="error").inc()
                logger.error("engagement_analysis_failed", user_id=user_id, error=str(e))
                raise_tool_execution_error(f"Failed to analyze engagement: {str(e)}", self.name)

class ScheduleOptimizationTool(BaseTool):
    """Tool for optimizing meeting schedules using AI."""
    
    name: str = "schedule_optimizer"
    description: str = "Optimizes meeting schedules for maximum attendance and efficiency"
    args_schema: type = ScheduleOptimizationInput

    def _run(self, **kwargs) -> str:
        """Execute the tool synchronously."""
        return asyncio.run(self._arun(**kwargs))

    async def _arun(self, **kwargs) -> str:
        """Execute the tool asynchronously."""
        return await self._optimize_schedule(**kwargs)

    async def _optimize_schedule(
        self,
        meeting_requests: List[Dict],
        participants: List[Dict],
        constraints: Optional[Dict] = None,
        optimization_goal: str = "maximize_attendance"
    ) -> str:
        """Optimize meeting schedule."""
        
        with ai_tool_duration_seconds.labels(tool_name=self.name).time():
            try:
                ai_tool_executions_total.labels(tool_name=self.name, status="started").inc()
                
                # Optimize schedule
                optimization_result = await ml_service.optimize_meeting_schedule(
                    meeting_requests, participants
                )
                
                # Add constraint analysis
                constraints_analysis = {
                    "time_constraints": constraints.get('time_constraints', []) if constraints else [],
                    "participant_constraints": constraints.get('participant_constraints', []) if constraints else [],
                    "room_constraints": constraints.get('room_constraints', []) if constraints else [],
                    "constraints_satisfied": True  # Would be calculated based on actual constraints
                }
                
                # Generate optimization insights
                insights = []
                if optimization_result['overall_optimization_score'] > 0.8:
                    insights.append("High optimization score achieved")
                elif optimization_result['overall_optimization_score'] < 0.6:
                    insights.append("Optimization score is low - consider adjusting constraints")
                
                conflicts_count = sum(1 for meeting in optimization_result['optimized_meetings'] 
                                    if meeting.get('conflicts', 0) > 0)
                if conflicts_count > 0:
                    insights.append(f"{conflicts_count} scheduling conflicts detected")
                
                schedule_optimization = {
                    "optimization_goal": optimization_goal,
                    "meetings_processed": len(meeting_requests),
                    "participants_count": len(participants),
                    "optimization_result": optimization_result,
                    "constraints_analysis": constraints_analysis,
                    "optimization_metrics": {
                        "overall_score": optimization_result['overall_optimization_score'],
                        "time_efficiency": 0.85,  # Would be calculated
                        "participant_satisfaction": 0.80,  # Would be calculated
                        "resource_utilization": 0.90  # Would be calculated
                    },
                    "insights": insights,
                    "recommendations": [
                        "Review optimized schedule with stakeholders",
                        "Consider feedback for future optimizations",
                        "Monitor actual attendance vs predictions"
                    ]
                }
                
                ai_tool_executions_total.labels(tool_name=self.name, status="success").inc()
                logger.info("schedule_optimized", 
                           meetings_count=len(meeting_requests),
                           optimization_score=optimization_result['overall_optimization_score'])
                
                return json.dumps(schedule_optimization, indent=2)
                
            except Exception as e:
                ai_tool_executions_total.labels(tool_name=self.name, status="error").inc()
                logger.error("schedule_optimization_failed", error=str(e))
                raise_tool_execution_error(f"Failed to optimize schedule: {str(e)}", self.name)

# Export all AI/ML tools
meeting_intelligence_tool = MeetingIntelligenceTool()
decision_support_tool = DecisionSupportTool()
predictive_analytics_tool = PredictiveAnalyticsTool()
sentiment_analysis_tool = SentimentAnalysisTool()
topic_extraction_tool = TopicExtractionTool()
semantic_search_tool = SemanticSearchTool()
engagement_analysis_tool = EngagementAnalysisTool()
schedule_optimization_tool = ScheduleOptimizationTool()

# List of all AI/ML tools
ai_ml_tools = [
    meeting_intelligence_tool,
    decision_support_tool,
    predictive_analytics_tool,
    sentiment_analysis_tool,
    topic_extraction_tool,
    semantic_search_tool,
    engagement_analysis_tool,
    schedule_optimization_tool
]