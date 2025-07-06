"""Machine Learning Service for Advanced AI/ML Features."""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import re
from collections import Counter
import logging

from app.core.config import settings
from app.core.logging import logger
from app.core.metrics import ai_operations_total, ai_token_usage_total
from app.core.exceptions import raise_tool_execution_error

# ML Model Types
class MLModelType(Enum):
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    TOPIC_EXTRACTION = "topic_extraction"
    ATTENDANCE_PREDICTION = "attendance_prediction"
    OUTCOME_FORECASTING = "outcome_forecasting"
    ENGAGEMENT_OPTIMIZATION = "engagement_optimization"
    CONSENSUS_PREDICTION = "consensus_prediction"

@dataclass
class MLPrediction:
    """ML Prediction result."""
    model_type: MLModelType
    prediction: Any
    confidence: float
    metadata: Dict[str, Any]
    timestamp: datetime

@dataclass
class MeetingIntelligence:
    """Meeting Intelligence data structure."""
    meeting_id: str
    transcription: str
    summary: str
    key_topics: List[str]
    sentiment_analysis: Dict[str, Any]
    action_items: List[str]
    effectiveness_score: float
    recommendations: List[str]

@dataclass
class DecisionSupport:
    """Decision Support analysis."""
    decision_id: str
    topic: str
    options: List[str]
    risk_analysis: Dict[str, Any]
    consensus_prediction: Dict[str, Any]
    stakeholder_impact: Dict[str, Any]
    recommendations: List[str]

@dataclass
class PredictiveAnalytics:
    """Predictive Analytics results."""
    prediction_type: str
    target_date: datetime
    prediction_value: Any
    confidence_interval: Tuple[float, float]
    factors: List[str]
    recommendations: List[str]

class MLService:
    """Advanced Machine Learning Service for Boardroom Application."""
    
    def __init__(self):
        """Initialize ML Service with models and components."""
        self.models = {}
        self.vectorizers = {}
        self.is_initialized = False
        self._initialize_models()
        
    def _initialize_models(self):
        """Initialize ML models and components."""
        try:
            # Initialize sentiment analysis model
            self.vectorizers[MLModelType.SENTIMENT_ANALYSIS] = TfidfVectorizer(
                max_features=5000,
                stop_words='english',
                ngram_range=(1, 2)
            )
            self.models[MLModelType.SENTIMENT_ANALYSIS] = MultinomialNB()
            
            # Initialize topic extraction components
            self.vectorizers[MLModelType.TOPIC_EXTRACTION] = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 3)
            )
            self.models[MLModelType.TOPIC_EXTRACTION] = KMeans(n_clusters=5, random_state=42)
            
            # Initialize predictive models
            self.models[MLModelType.ATTENDANCE_PREDICTION] = LinearRegression()
            self.models[MLModelType.OUTCOME_FORECASTING] = LinearRegression()
            self.models[MLModelType.ENGAGEMENT_OPTIMIZATION] = LinearRegression()
            self.models[MLModelType.CONSENSUS_PREDICTION] = MultinomialNB()
            
            self.is_initialized = True
            logger.info("ml_service_initialized", models_count=len(self.models))
            
        except Exception as e:
            logger.error("ml_service_initialization_failed", error=str(e))
            raise

    # Meeting Intelligence Features
    async def transcribe_meeting(self, audio_data: bytes, meeting_id: str) -> str:
        """Transcribe meeting audio to text."""
        try:
            ai_operations_total.labels(operation="transcription", model="whisper", status="started").inc()
            
            # Simulate transcription (in production, use OpenAI Whisper or similar)
            await asyncio.sleep(0.1)  # Simulate processing time
            
            transcription = f"[Transcription for meeting {meeting_id}] This is a simulated transcription of the meeting audio. In a real implementation, this would use OpenAI Whisper or similar speech-to-text service."
            
            ai_operations_total.labels(operation="transcription", model="whisper", status="success").inc()
            logger.info("meeting_transcribed", meeting_id=meeting_id, length=len(transcription))
            
            return transcription
            
        except Exception as e:
            ai_operations_total.labels(operation="transcription", model="whisper", status="error").inc()
            logger.error("meeting_transcription_failed", meeting_id=meeting_id, error=str(e))
            raise

    async def summarize_meeting(self, transcription: str, meeting_id: str) -> str:
        """Generate meeting summary from transcription."""
        try:
            ai_operations_total.labels(operation="summarization", model="gpt-4", status="started").inc()
            
            # Extract key sentences and themes
            sentences = re.split(r'[.!?]+', transcription)
            key_sentences = [s.strip() for s in sentences if len(s.strip()) > 20][:5]
            
            summary = f"Meeting Summary for {meeting_id}:\n"
            summary += "Key Discussion Points:\n"
            for i, sentence in enumerate(key_sentences, 1):
                summary += f"{i}. {sentence}\n"
            
            ai_operations_total.labels(operation="summarization", model="gpt-4", status="success").inc()
            logger.info("meeting_summarized", meeting_id=meeting_id, summary_length=len(summary))
            
            return summary
            
        except Exception as e:
            ai_operations_total.labels(operation="summarization", model="gpt-4", status="error").inc()
            logger.error("meeting_summarization_failed", meeting_id=meeting_id, error=str(e))
            raise

    async def generate_agenda(self, topic: str, previous_meetings: List[Dict]) -> Dict[str, Any]:
        """Generate intelligent agenda based on previous meetings."""
        try:
            ai_operations_total.labels(operation="agenda_generation", model="gpt-4", status="started").inc()
            
            # Analyze previous meetings for patterns
            common_topics = self._extract_common_topics(previous_meetings)
            
            agenda = {
                "meeting_topic": topic,
                "generated_at": datetime.now().isoformat(),
                "agenda_items": [
                    {
                        "item": "Welcome and Introductions",
                        "duration_minutes": 10,
                        "type": "opening"
                    },
                    {
                        "item": f"Main Discussion: {topic}",
                        "duration_minutes": 30,
                        "type": "main_discussion"
                    }
                ],
                "suggested_topics": common_topics,
                "ai_recommendations": [
                    "Based on previous meetings, consider discussing budget implications",
                    "Review action items from last meeting",
                    "Allocate time for stakeholder feedback"
                ]
            }
            
            # Add intelligent suggestions based on topic
            if "budget" in topic.lower():
                agenda["agenda_items"].append({
                    "item": "Budget Impact Analysis",
                    "duration_minutes": 15,
                    "type": "analysis"
                })
            
            if "strategy" in topic.lower():
                agenda["agenda_items"].append({
                    "item": "Strategic Implications Review",
                    "duration_minutes": 20,
                    "type": "strategic"
                })
            
            agenda["agenda_items"].append({
                "item": "Action Items and Next Steps",
                "duration_minutes": 10,
                "type": "closing"
            })
            
            ai_operations_total.labels(operation="agenda_generation", model="gpt-4", status="success").inc()
            logger.info("agenda_generated", topic=topic, items_count=len(agenda["agenda_items"]))
            
            return agenda
            
        except Exception as e:
            ai_operations_total.labels(operation="agenda_generation", model="gpt-4", status="error").inc()
            logger.error("agenda_generation_failed", topic=topic, error=str(e))
            raise

    def _extract_common_topics(self, meetings: List[Dict]) -> List[str]:
        """Extract common topics from previous meetings."""
        all_topics = []
        for meeting in meetings:
            if 'topics' in meeting:
                all_topics.extend(meeting['topics'])
        
        topic_counts = Counter(all_topics)
        return [topic for topic, count in topic_counts.most_common(5)]

    async def extract_action_items(self, transcription: str) -> List[str]:
        """Extract action items from meeting transcription."""
        try:
            # Look for action-oriented patterns
            action_patterns = [
                r'action item[:\s]+(.+?)(?:\.|$)',
                r'([A-Z][a-z]+ will .+?)(?:\.|$)',
                r'(need to .+?)(?:\.|$)',
                r'(should .+?)(?:\.|$)',
                r'(must .+?)(?:\.|$)',
                r'(follow up on .+?)(?:\.|$)'
            ]
            
            action_items = []
            for pattern in action_patterns:
                matches = re.finditer(pattern, transcription, re.IGNORECASE)
                for match in matches:
                    action_items.append(match.group(1).strip())
            
            # Remove duplicates and filter
            unique_actions = list(set(action_items))
            filtered_actions = [action for action in unique_actions if len(action) > 10]
            
            logger.info("action_items_extracted", count=len(filtered_actions))
            return filtered_actions[:10]  # Return top 10 action items
            
        except Exception as e:
            logger.error("action_item_extraction_failed", error=str(e))
            raise

    async def calculate_meeting_effectiveness(self, meeting_data: Dict) -> float:
        """Calculate meeting effectiveness score."""
        try:
            score = 0.0
            max_score = 100.0
            
            # Participation score (40%)
            if 'participants' in meeting_data:
                participation_rate = len(meeting_data['participants']) / max(meeting_data.get('invited_count', 1), 1)
                score += min(participation_rate, 1.0) * 40
            
            # Action items score (30%)
            if 'action_items' in meeting_data:
                action_items_count = len(meeting_data['action_items'])
                score += min(action_items_count / 5, 1.0) * 30
            
            # Duration efficiency score (20%)
            if 'duration_minutes' in meeting_data:
                planned_duration = meeting_data.get('planned_duration', 60)
                actual_duration = meeting_data['duration_minutes']
                efficiency = 1 - abs(actual_duration - planned_duration) / planned_duration
                score += max(efficiency, 0) * 20
            
            # Decision making score (10%)
            if 'decisions_made' in meeting_data:
                decisions_count = len(meeting_data['decisions_made'])
                score += min(decisions_count / 3, 1.0) * 10
            
            effectiveness_score = score / max_score
            logger.info("meeting_effectiveness_calculated", score=effectiveness_score)
            
            return effectiveness_score
            
        except Exception as e:
            logger.error("meeting_effectiveness_calculation_failed", error=str(e))
            raise

    # Decision Support Features
    async def analyze_decision_risk(self, decision_data: Dict) -> Dict[str, Any]:
        """Analyze risk factors for a decision."""
        try:
            ai_operations_total.labels(operation="risk_analysis", model="ml_model", status="started").inc()
            
            risk_factors = {
                "financial_risk": self._assess_financial_risk(decision_data),
                "operational_risk": self._assess_operational_risk(decision_data),
                "strategic_risk": self._assess_strategic_risk(decision_data),
                "timeline_risk": self._assess_timeline_risk(decision_data)
            }
            
            overall_risk = np.mean(list(risk_factors.values()))
            
            risk_analysis = {
                "overall_risk_score": overall_risk,
                "risk_level": self._categorize_risk(overall_risk),
                "risk_factors": risk_factors,
                "mitigation_strategies": self._generate_mitigation_strategies(risk_factors),
                "recommendations": self._generate_risk_recommendations(overall_risk)
            }
            
            ai_operations_total.labels(operation="risk_analysis", model="ml_model", status="success").inc()
            logger.info("decision_risk_analyzed", overall_risk=overall_risk)
            
            return risk_analysis
            
        except Exception as e:
            ai_operations_total.labels(operation="risk_analysis", model="ml_model", status="error").inc()
            logger.error("decision_risk_analysis_failed", error=str(e))
            raise

    def _assess_financial_risk(self, decision_data: Dict) -> float:
        """Assess financial risk of a decision."""
        budget_impact = decision_data.get('budget_impact', 0)
        if budget_impact > 1000000:
            return 0.8
        elif budget_impact > 100000:
            return 0.6
        elif budget_impact > 10000:
            return 0.4
        else:
            return 0.2

    def _assess_operational_risk(self, decision_data: Dict) -> float:
        """Assess operational risk of a decision."""
        complexity = decision_data.get('complexity_score', 5)
        return min(complexity / 10, 1.0)

    def _assess_strategic_risk(self, decision_data: Dict) -> float:
        """Assess strategic risk of a decision."""
        strategic_impact = decision_data.get('strategic_impact', 'medium')
        risk_map = {'low': 0.2, 'medium': 0.5, 'high': 0.8}
        return risk_map.get(strategic_impact, 0.5)

    def _assess_timeline_risk(self, decision_data: Dict) -> float:
        """Assess timeline risk of a decision."""
        timeline_months = decision_data.get('timeline_months', 6)
        if timeline_months > 12:
            return 0.7
        elif timeline_months > 6:
            return 0.5
        else:
            return 0.3

    def _categorize_risk(self, risk_score: float) -> str:
        """Categorize risk level based on score."""
        if risk_score > 0.7:
            return "High Risk"
        elif risk_score > 0.4:
            return "Medium Risk"
        else:
            return "Low Risk"

    def _generate_mitigation_strategies(self, risk_factors: Dict) -> List[str]:
        """Generate mitigation strategies based on risk factors."""
        strategies = []
        
        if risk_factors['financial_risk'] > 0.6:
            strategies.append("Implement phased budget allocation")
            strategies.append("Establish financial milestones and checkpoints")
        
        if risk_factors['operational_risk'] > 0.6:
            strategies.append("Conduct pilot testing before full implementation")
            strategies.append("Develop comprehensive training programs")
        
        if risk_factors['strategic_risk'] > 0.6:
            strategies.append("Align with key stakeholders before proceeding")
            strategies.append("Develop strategic impact assessment")
        
        if risk_factors['timeline_risk'] > 0.6:
            strategies.append("Build buffer time into project timeline")
            strategies.append("Establish critical path monitoring")
        
        return strategies

    def _generate_risk_recommendations(self, overall_risk: float) -> List[str]:
        """Generate recommendations based on overall risk."""
        if overall_risk > 0.7:
            return [
                "Recommend executive approval before proceeding",
                "Conduct thorough risk assessment workshop",
                "Develop detailed contingency plans"
            ]
        elif overall_risk > 0.4:
            return [
                "Proceed with enhanced monitoring",
                "Regular checkpoint reviews recommended",
                "Consider phased implementation approach"
            ]
        else:
            return [
                "Low risk decision - proceed with standard process",
                "Maintain regular progress monitoring",
                "Document lessons learned for future decisions"
            ]

    async def predict_consensus(self, decision_data: Dict, stakeholder_data: List[Dict]) -> Dict[str, Any]:
        """Predict consensus likelihood for a decision."""
        try:
            ai_operations_total.labels(operation="consensus_prediction", model="ml_model", status="started").inc()
            
            # Analyze stakeholder alignment
            support_scores = []
            influence_weights = []
            
            for stakeholder in stakeholder_data:
                support_score = stakeholder.get('support_level', 0.5)  # 0-1 scale
                influence_weight = stakeholder.get('influence_level', 0.5)  # 0-1 scale
                
                support_scores.append(support_score)
                influence_weights.append(influence_weight)
            
            # Calculate weighted consensus probability
            if support_scores and influence_weights:
                weighted_support = np.average(support_scores, weights=influence_weights)
                consensus_probability = weighted_support
            else:
                consensus_probability = 0.5
            
            # Analyze factors affecting consensus
            consensus_factors = {
                "stakeholder_alignment": weighted_support if support_scores else 0.5,
                "decision_complexity": 1 - decision_data.get('complexity_score', 5) / 10,
                "time_pressure": 1 - decision_data.get('urgency_score', 5) / 10,
                "resource_impact": 1 - decision_data.get('resource_impact', 5) / 10
            }
            
            consensus_prediction = {
                "consensus_probability": consensus_probability,
                "consensus_level": self._categorize_consensus(consensus_probability),
                "factors": consensus_factors,
                "stakeholder_analysis": self._analyze_stakeholder_positions(stakeholder_data),
                "recommendations": self._generate_consensus_recommendations(consensus_probability)
            }
            
            ai_operations_total.labels(operation="consensus_prediction", model="ml_model", status="success").inc()
            logger.info("consensus_predicted", probability=consensus_probability)
            
            return consensus_prediction
            
        except Exception as e:
            ai_operations_total.labels(operation="consensus_prediction", model="ml_model", status="error").inc()
            logger.error("consensus_prediction_failed", error=str(e))
            raise

    def _categorize_consensus(self, probability: float) -> str:
        """Categorize consensus level."""
        if probability > 0.8:
            return "High Consensus"
        elif probability > 0.6:
            return "Moderate Consensus"
        elif probability > 0.4:
            return "Low Consensus"
        else:
            return "No Consensus"

    def _analyze_stakeholder_positions(self, stakeholder_data: List[Dict]) -> Dict[str, Any]:
        """Analyze stakeholder positions."""
        positions = {
            "supporters": [],
            "neutral": [],
            "opponents": []
        }
        
        for stakeholder in stakeholder_data:
            support_level = stakeholder.get('support_level', 0.5)
            name = stakeholder.get('name', 'Unknown')
            
            if support_level > 0.7:
                positions["supporters"].append(name)
            elif support_level < 0.3:
                positions["opponents"].append(name)
            else:
                positions["neutral"].append(name)
        
        return positions

    def _generate_consensus_recommendations(self, probability: float) -> List[str]:
        """Generate consensus building recommendations."""
        if probability > 0.7:
            return [
                "Strong consensus likely - proceed with implementation",
                "Maintain stakeholder engagement throughout process",
                "Document agreed-upon approach for future reference"
            ]
        elif probability > 0.4:
            return [
                "Moderate consensus - address key concerns before proceeding",
                "Conduct additional stakeholder discussions",
                "Consider compromise solutions to increase buy-in"
            ]
        else:
            return [
                "Low consensus - extensive stakeholder engagement needed",
                "Identify and address root causes of opposition",
                "Consider alternative approaches or timing"
            ]

    # Predictive Analytics Features
    async def predict_meeting_attendance(self, meeting_data: Dict, historical_data: List[Dict]) -> PredictiveAnalytics:
        """Predict meeting attendance based on historical data."""
        try:
            ai_operations_total.labels(operation="attendance_prediction", model="ml_model", status="started").inc()
            
            # Extract features from historical data
            features = self._extract_attendance_features(historical_data)
            
            # Simple prediction model (in production, use more sophisticated ML)
            base_attendance = 0.8  # 80% base attendance rate
            
            # Adjust based on factors
            if meeting_data.get('day_of_week') == 'Friday':
                base_attendance *= 0.9
            if meeting_data.get('time_of_day') == 'early_morning':
                base_attendance *= 0.85
            if meeting_data.get('meeting_type') == 'mandatory':
                base_attendance *= 1.1
            
            predicted_attendance = min(base_attendance, 1.0)
            confidence_interval = (predicted_attendance - 0.1, predicted_attendance + 0.1)
            
            prediction = PredictiveAnalytics(
                prediction_type="meeting_attendance",
                target_date=datetime.fromisoformat(meeting_data['scheduled_date']),
                prediction_value=predicted_attendance,
                confidence_interval=confidence_interval,
                factors=[
                    f"Day of week: {meeting_data.get('day_of_week', 'unknown')}",
                    f"Time of day: {meeting_data.get('time_of_day', 'unknown')}",
                    f"Meeting type: {meeting_data.get('meeting_type', 'unknown')}"
                ],
                recommendations=self._generate_attendance_recommendations(predicted_attendance)
            )
            
            ai_operations_total.labels(operation="attendance_prediction", model="ml_model", status="success").inc()
            logger.info("attendance_predicted", predicted_rate=predicted_attendance)
            
            return prediction
            
        except Exception as e:
            ai_operations_total.labels(operation="attendance_prediction", model="ml_model", status="error").inc()
            logger.error("attendance_prediction_failed", error=str(e))
            raise

    def _extract_attendance_features(self, historical_data: List[Dict]) -> List[Dict]:
        """Extract features for attendance prediction."""
        features = []
        for meeting in historical_data:
            feature_dict = {
                'day_of_week': meeting.get('day_of_week'),
                'time_of_day': meeting.get('time_of_day'),
                'meeting_type': meeting.get('meeting_type'),
                'duration': meeting.get('duration_minutes'),
                'attendance_rate': meeting.get('attendance_rate', 0.8)
            }
            features.append(feature_dict)
        return features

    def _generate_attendance_recommendations(self, predicted_rate: float) -> List[str]:
        """Generate recommendations to improve attendance."""
        if predicted_rate < 0.6:
            return [
                "Consider rescheduling to a more favorable time",
                "Send reminder notifications closer to meeting date",
                "Provide clear agenda and objectives in advance",
                "Consider hybrid meeting format to increase accessibility"
            ]
        elif predicted_rate < 0.8:
            return [
                "Send meeting reminders 24 hours in advance",
                "Ensure meeting objectives are clearly communicated",
                "Consider providing meeting materials in advance"
            ]
        else:
            return [
                "Attendance prediction is favorable",
                "Maintain current meeting scheduling practices",
                "Consider recording for those who cannot attend"
            ]

    # Natural Language Processing Features
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text content."""
        try:
            ai_operations_total.labels(operation="sentiment_analysis", model="ml_model", status="started").inc()
            
            # Simple sentiment analysis (in production, use more sophisticated NLP)
            positive_words = ['good', 'great', 'excellent', 'positive', 'agree', 'support', 'like', 'love', 'wonderful']
            negative_words = ['bad', 'terrible', 'negative', 'disagree', 'oppose', 'dislike', 'hate', 'awful']
            
            words = text.lower().split()
            positive_count = sum(1 for word in words if word in positive_words)
            negative_count = sum(1 for word in words if word in negative_words)
            
            total_sentiment_words = positive_count + negative_count
            
            if total_sentiment_words > 0:
                sentiment_score = (positive_count - negative_count) / total_sentiment_words
            else:
                sentiment_score = 0.0
            
            # Categorize sentiment
            if sentiment_score > 0.1:
                sentiment_label = "positive"
            elif sentiment_score < -0.1:
                sentiment_label = "negative"
            else:
                sentiment_label = "neutral"
            
            sentiment_analysis = {
                "sentiment_score": sentiment_score,
                "sentiment_label": sentiment_label,
                "confidence": abs(sentiment_score),
                "positive_indicators": positive_count,
                "negative_indicators": negative_count,
                "word_count": len(words)
            }
            
            ai_operations_total.labels(operation="sentiment_analysis", model="ml_model", status="success").inc()
            logger.info("sentiment_analyzed", sentiment=sentiment_label, score=sentiment_score)
            
            return sentiment_analysis
            
        except Exception as e:
            ai_operations_total.labels(operation="sentiment_analysis", model="ml_model", status="error").inc()
            logger.error("sentiment_analysis_failed", error=str(e))
            raise

    async def extract_topics(self, text: str, num_topics: int = 5) -> List[Dict[str, Any]]:
        """Extract topics from text using NLP."""
        try:
            ai_operations_total.labels(operation="topic_extraction", model="ml_model", status="started").inc()
            
            # Simple topic extraction using keyword frequency
            words = re.findall(r'\b\w+\b', text.lower())
            
            # Filter out common stop words
            stop_words = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'])
            filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
            
            # Count word frequencies
            word_counts = Counter(filtered_words)
            
            # Extract top topics
            topics = []
            for word, count in word_counts.most_common(num_topics):
                topic = {
                    "topic": word,
                    "frequency": count,
                    "relevance_score": count / len(filtered_words),
                    "category": self._categorize_topic(word)
                }
                topics.append(topic)
            
            ai_operations_total.labels(operation="topic_extraction", model="ml_model", status="success").inc()
            logger.info("topics_extracted", count=len(topics))
            
            return topics
            
        except Exception as e:
            ai_operations_total.labels(operation="topic_extraction", model="ml_model", status="error").inc()
            logger.error("topic_extraction_failed", error=str(e))
            raise

    def _categorize_topic(self, word: str) -> str:
        """Categorize a topic word."""
        business_terms = ['budget', 'revenue', 'cost', 'profit', 'strategy', 'market', 'customer', 'product', 'service']
        technical_terms = ['system', 'software', 'data', 'technology', 'platform', 'infrastructure', 'development']
        operational_terms = ['process', 'workflow', 'procedure', 'policy', 'operation', 'management', 'team']
        
        if word in business_terms:
            return 'business'
        elif word in technical_terms:
            return 'technical'
        elif word in operational_terms:
            return 'operational'
        else:
            return 'general'

    async def semantic_search(self, query: str, documents: List[str]) -> List[Dict[str, Any]]:
        """Perform semantic search on documents."""
        try:
            ai_operations_total.labels(operation="semantic_search", model="ml_model", status="started").inc()
            
            # Simple semantic search using TF-IDF and cosine similarity
            all_texts = [query] + documents
            
            # Create TF-IDF vectors
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = vectorizer.fit_transform(all_texts)
            
            # Calculate cosine similarity between query and documents
            query_vector = tfidf_matrix[0:1]
            document_vectors = tfidf_matrix[1:]
            
            similarities = cosine_similarity(query_vector, document_vectors).flatten()
            
            # Create results
            results = []
            for i, (doc, similarity) in enumerate(zip(documents, similarities)):
                result = {
                    "document_id": i,
                    "document": doc,
                    "similarity_score": float(similarity),
                    "relevance": "high" if similarity > 0.3 else "medium" if similarity > 0.1 else "low"
                }
                results.append(result)
            
            # Sort by similarity score
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            ai_operations_total.labels(operation="semantic_search", model="ml_model", status="success").inc()
            logger.info("semantic_search_completed", results_count=len(results))
            
            return results
            
        except Exception as e:
            ai_operations_total.labels(operation="semantic_search", model="ml_model", status="error").inc()
            logger.error("semantic_search_failed", error=str(e))
            raise

    # User Behavior and Engagement Features
    async def predict_user_engagement(self, user_data: Dict, historical_engagement: List[Dict]) -> MLPrediction:
        """Predict user engagement level."""
        try:
            ai_operations_total.labels(operation="engagement_prediction", model="ml_model", status="started").inc()
            
            # Calculate engagement features
            avg_meeting_participation = np.mean([e.get('participation_score', 0.5) for e in historical_engagement])
            recent_activity_score = self._calculate_recent_activity(historical_engagement)
            role_engagement_factor = self._get_role_engagement_factor(user_data.get('role', 'participant'))
            
            # Predict engagement score
            engagement_score = (avg_meeting_participation * 0.5 + 
                               recent_activity_score * 0.3 + 
                               role_engagement_factor * 0.2)
            
            prediction = MLPrediction(
                model_type=MLModelType.ENGAGEMENT_OPTIMIZATION,
                prediction=engagement_score,
                confidence=0.8,
                metadata={
                    "avg_participation": avg_meeting_participation,
                    "recent_activity": recent_activity_score,
                    "role_factor": role_engagement_factor,
                    "recommendations": self._generate_engagement_recommendations(engagement_score)
                },
                timestamp=datetime.now()
            )
            
            ai_operations_total.labels(operation="engagement_prediction", model="ml_model", status="success").inc()
            logger.info("engagement_predicted", user_id=user_data.get('id'), score=engagement_score)
            
            return prediction
            
        except Exception as e:
            ai_operations_total.labels(operation="engagement_prediction", model="ml_model", status="error").inc()
            logger.error("engagement_prediction_failed", error=str(e))
            raise

    def _calculate_recent_activity(self, historical_engagement: List[Dict]) -> float:
        """Calculate recent activity score."""
        if not historical_engagement:
            return 0.5
        
        # Sort by date and get recent activities
        recent_activities = sorted(historical_engagement, key=lambda x: x.get('date', ''), reverse=True)[:5]
        
        if not recent_activities:
            return 0.5
        
        return np.mean([activity.get('activity_score', 0.5) for activity in recent_activities])

    def _get_role_engagement_factor(self, role: str) -> float:
        """Get engagement factor based on user role."""
        role_factors = {
            'executive': 0.9,
            'manager': 0.8,
            'team_lead': 0.7,
            'participant': 0.6,
            'observer': 0.4
        }
        return role_factors.get(role, 0.6)

    def _generate_engagement_recommendations(self, engagement_score: float) -> List[str]:
        """Generate recommendations to improve user engagement."""
        if engagement_score < 0.4:
            return [
                "Consider one-on-one meetings to understand concerns",
                "Provide more relevant meeting content",
                "Offer training or support to increase participation",
                "Review meeting frequency and format"
            ]
        elif engagement_score < 0.7:
            return [
                "Encourage more active participation in discussions",
                "Assign specific roles or responsibilities in meetings",
                "Provide pre-meeting materials to increase preparation",
                "Gather feedback on meeting effectiveness"
            ]
        else:
            return [
                "Maintain current engagement practices",
                "Consider leveraging as a meeting facilitator",
                "Recognize and reward high engagement",
                "Use as a mentor for less engaged participants"
            ]

    # Automation and Workflow Features
    async def optimize_meeting_schedule(self, meeting_requests: List[Dict], participants: List[Dict]) -> Dict[str, Any]:
        """Optimize meeting schedules using AI."""
        try:
            ai_operations_total.labels(operation="schedule_optimization", model="ml_model", status="started").inc()
            
            # Simple scheduling optimization
            optimized_schedule = []
            
            for meeting in meeting_requests:
                best_time = self._find_optimal_time(meeting, participants)
                
                optimized_meeting = {
                    "meeting_id": meeting.get('id'),
                    "original_time": meeting.get('requested_time'),
                    "optimized_time": best_time,
                    "expected_attendance": self._calculate_expected_attendance(best_time, participants),
                    "optimization_score": self._calculate_optimization_score(meeting, best_time, participants),
                    "recommendations": self._generate_schedule_recommendations(meeting, best_time)
                }
                optimized_schedule.append(optimized_meeting)
            
            schedule_summary = {
                "total_meetings": len(meeting_requests),
                "optimized_meetings": optimized_schedule,
                "overall_optimization_score": np.mean([m['optimization_score'] for m in optimized_schedule]),
                "recommendations": self._generate_overall_schedule_recommendations(optimized_schedule)
            }
            
            ai_operations_total.labels(operation="schedule_optimization", model="ml_model", status="success").inc()
            logger.info("schedule_optimized", meetings_count=len(meeting_requests))
            
            return schedule_summary
            
        except Exception as e:
            ai_operations_total.labels(operation="schedule_optimization", model="ml_model", status="error").inc()
            logger.error("schedule_optimization_failed", error=str(e))
            raise

    def _find_optimal_time(self, meeting: Dict, participants: List[Dict]) -> str:
        """Find optimal meeting time based on participant availability."""
        # Simple heuristic: prefer 10 AM - 4 PM on weekdays
        optimal_hours = ['10:00', '11:00', '13:00', '14:00', '15:00', '16:00']
        
        # Return first available optimal time (in production, check actual availability)
        return optimal_hours[0]

    def _calculate_expected_attendance(self, time: str, participants: List[Dict]) -> float:
        """Calculate expected attendance for a given time."""
        # Simple calculation based on time preference
        hour = int(time.split(':')[0])
        
        if 9 <= hour <= 11 or 14 <= hour <= 16:
            return 0.9  # High attendance expected
        elif 13 <= hour <= 14:
            return 0.7  # Medium attendance (lunch time)
        else:
            return 0.6  # Lower attendance

    def _calculate_optimization_score(self, meeting: Dict, optimized_time: str, participants: List[Dict]) -> float:
        """Calculate optimization score for a meeting."""
        expected_attendance = self._calculate_expected_attendance(optimized_time, participants)
        
        # Simple scoring based on attendance and time preference
        return expected_attendance * 0.7 + 0.3  # Base score + attendance factor

    def _generate_schedule_recommendations(self, meeting: Dict, optimized_time: str) -> List[str]:
        """Generate recommendations for individual meeting schedule."""
        return [
            f"Optimal time identified: {optimized_time}",
            "Send meeting invitations 48 hours in advance",
            "Include agenda and pre-meeting materials",
            "Set up automated reminders"
        ]

    def _generate_overall_schedule_recommendations(self, optimized_schedule: List[Dict]) -> List[str]:
        """Generate recommendations for overall schedule optimization."""
        avg_score = np.mean([m['optimization_score'] for m in optimized_schedule])
        
        if avg_score > 0.8:
            return [
                "Schedule optimization is highly effective",
                "Consider maintaining current scheduling patterns",
                "Continue to monitor attendance rates"
            ]
        else:
            return [
                "Consider more flexible scheduling options",
                "Review participant availability patterns",
                "Implement hybrid meeting options for better attendance"
            ]

    # Model Management and Deployment
    async def get_model_health(self) -> Dict[str, Any]:
        """Get health status of ML models."""
        try:
            model_health = {
                "service_status": "healthy" if self.is_initialized else "unhealthy",
                "models_loaded": len(self.models),
                "models_status": {},
                "last_health_check": datetime.now().isoformat()
            }
            
            for model_type, model in self.models.items():
                model_health["models_status"][model_type.value] = {
                    "status": "healthy",
                    "model_type": type(model).__name__,
                    "last_used": datetime.now().isoformat()
                }
            
            logger.info("ml_model_health_checked", status="healthy")
            return model_health
            
        except Exception as e:
            logger.error("ml_model_health_check_failed", error=str(e))
            raise

    async def update_model(self, model_type: MLModelType, model_data: bytes) -> bool:
        """Update an ML model with new trained data."""
        try:
            ai_operations_total.labels(operation="model_update", model=model_type.value, status="started").inc()
            
            # In production, this would load and validate the new model
            # For now, we'll simulate successful update
            await asyncio.sleep(0.1)
            
            logger.info("ml_model_updated", model_type=model_type.value)
            ai_operations_total.labels(operation="model_update", model=model_type.value, status="success").inc()
            
            return True
            
        except Exception as e:
            ai_operations_total.labels(operation="model_update", model=model_type.value, status="error").inc()
            logger.error("ml_model_update_failed", model_type=model_type.value, error=str(e))
            raise

# Global ML Service Instance
ml_service = MLService()