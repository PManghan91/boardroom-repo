"""ML Pipeline Service for model training, versioning, and deployment."""

import asyncio
import json
import pickle
import hashlib
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import joblib
import redis
from sqlalchemy import create_engine, Column, String, DateTime, Float, Integer, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.logging import logger
from app.core.metrics import ai_operations_total
from app.services.ml_service import MLModelType

Base = declarative_base()

class ModelStatus(Enum):
    """Model deployment status."""
    TRAINING = "training"
    TRAINED = "trained"
    TESTING = "testing"
    DEPLOYED = "deployed"
    DEPRECATED = "deprecated"
    FAILED = "failed"

class DeploymentEnvironment(Enum):
    """Deployment environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass
class ModelMetrics:
    """Model performance metrics."""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    training_time: float
    inference_time: float
    model_size: int
    data_version: str

@dataclass
class TrainingConfig:
    """Model training configuration."""
    model_type: MLModelType
    hyperparameters: Dict[str, Any]
    training_data_path: str
    validation_split: float
    random_state: int
    max_training_time: int  # seconds

class MLModel(Base):
    """Database model for ML models."""
    __tablename__ = "ml_models"
    
    id = Column(String, primary_key=True)
    model_type = Column(String, nullable=False)
    version = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    trained_at = Column(DateTime)
    deployed_at = Column(DateTime)
    model_path = Column(String)
    metrics = Column(Text)  # JSON string
    config = Column(Text)  # JSON string
    environment = Column(String)
    is_active = Column(Boolean, default=False)

class TrainingJob(Base):
    """Database model for training jobs."""
    __tablename__ = "training_jobs"
    
    id = Column(String, primary_key=True)
    model_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    config = Column(Text)  # JSON string
    metrics = Column(Text)  # JSON string
    error_message = Column(Text)
    created_by = Column(String)

class MLPipelineService:
    """Service for managing ML model pipeline."""
    
    def __init__(self):
        """Initialize ML pipeline service."""
        self.model_storage_path = Path(settings.ML_MODEL_STORAGE_PATH if hasattr(settings, 'ML_MODEL_STORAGE_PATH') else "/tmp/ml_models")
        self.model_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.engine = create_engine(settings.POSTGRES_URL)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Initialize Redis for model cache
        self.redis_client = redis.Redis.from_url(settings.REDIS_URL) if hasattr(settings, 'REDIS_URL') else None
        
        self.active_training_jobs = {}
        self.deployed_models = {}
        
    async def start_training_job(self, training_config: TrainingConfig, user_id: str = None) -> str:
        """Start a new model training job."""
        try:
            ai_operations_total.labels(operation="model_training", model=training_config.model_type.value, status="started").inc()
            
            job_id = self._generate_job_id(training_config)
            
            # Create training job record
            with self.SessionLocal() as session:
                training_job = TrainingJob(
                    id=job_id,
                    model_type=training_config.model_type.value,
                    status="queued",
                    config=json.dumps(asdict(training_config)),
                    created_by=user_id
                )
                session.add(training_job)
                session.commit()
            
            # Start training in background
            asyncio.create_task(self._run_training_job(job_id, training_config))
            
            logger.info("training_job_started", 
                       job_id=job_id,
                       model_type=training_config.model_type.value)
            
            return job_id
            
        except Exception as e:
            ai_operations_total.labels(operation="model_training", model=training_config.model_type.value, status="error").inc()
            logger.error("training_job_start_failed", error=str(e))
            raise
    
    def _generate_job_id(self, config: TrainingConfig) -> str:
        """Generate unique job ID."""
        config_str = json.dumps(asdict(config), sort_keys=True)
        timestamp = datetime.now().isoformat()
        return hashlib.md5(f"{config_str}_{timestamp}".encode()).hexdigest()[:16]
    
    async def _run_training_job(self, job_id: str, config: TrainingConfig):
        """Run training job asynchronously."""
        try:
            self.active_training_jobs[job_id] = {
                "status": "running",
                "started_at": datetime.now(),
                "config": config
            }
            
            # Update job status
            with self.SessionLocal() as session:
                job = session.query(TrainingJob).filter(TrainingJob.id == job_id).first()
                job.status = "running"
                session.commit()
            
            # Load and prepare data
            training_data, labels = await self._load_training_data(config.training_data_path)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                training_data, labels,
                test_size=config.validation_split,
                random_state=config.random_state
            )
            
            # Train model
            start_time = datetime.now()
            model, training_metrics = await self._train_model(config, X_train, y_train, X_test, y_test)
            training_time = (datetime.now() - start_time).total_seconds()
            
            # Calculate metrics
            metrics = ModelMetrics(
                accuracy=training_metrics["accuracy"],
                precision=training_metrics["precision"],
                recall=training_metrics["recall"],
                f1_score=training_metrics["f1_score"],
                training_time=training_time,
                inference_time=training_metrics.get("inference_time", 0.1),
                model_size=training_metrics.get("model_size", 0),
                data_version=self._get_data_version(config.training_data_path)
            )
            
            # Save model
            model_path = await self._save_model(model, config.model_type, metrics)
            
            # Create model version
            model_version = await self._create_model_version(config.model_type, model_path, metrics, config)
            
            # Update job completion
            with self.SessionLocal() as session:
                job = session.query(TrainingJob).filter(TrainingJob.id == job_id).first()
                job.status = "completed"
                job.completed_at = datetime.now()
                job.metrics = json.dumps(asdict(metrics))
                session.commit()
            
            # Clean up
            if job_id in self.active_training_jobs:
                del self.active_training_jobs[job_id]
            
            ai_operations_total.labels(operation="model_training", model=config.model_type.value, status="success").inc()
            logger.info("training_job_completed", 
                       job_id=job_id,
                       model_version=model_version,
                       accuracy=metrics.accuracy)
            
        except Exception as e:
            # Update job status
            with self.SessionLocal() as session:
                job = session.query(TrainingJob).filter(TrainingJob.id == job_id).first()
                job.status = "failed"
                job.completed_at = datetime.now()
                job.error_message = str(e)
                session.commit()
            
            # Clean up
            if job_id in self.active_training_jobs:
                del self.active_training_jobs[job_id]
            
            ai_operations_total.labels(operation="model_training", model=config.model_type.value, status="error").inc()
            logger.error("training_job_failed", job_id=job_id, error=str(e))
    
    async def _load_training_data(self, data_path: str) -> Tuple[np.ndarray, np.ndarray]:
        """Load training data from path."""
        try:
            # Simulate loading data (in production, load actual data)
            # This would typically load from files, databases, or APIs
            np.random.seed(42)
            X = np.random.randn(1000, 10)  # 1000 samples, 10 features
            y = np.random.randint(0, 2, 1000)  # Binary classification
            
            logger.info("training_data_loaded", samples=len(X), features=X.shape[1])
            return X, y
            
        except Exception as e:
            logger.error("training_data_loading_failed", data_path=data_path, error=str(e))
            raise
    
    async def _train_model(self, config: TrainingConfig, X_train, y_train, X_test, y_test) -> Tuple[Any, Dict]:
        """Train ML model."""
        try:
            # Import model based on type
            if config.model_type == MLModelType.SENTIMENT_ANALYSIS:
                from sklearn.naive_bayes import MultinomialNB
                model = MultinomialNB(**config.hyperparameters)
            elif config.model_type == MLModelType.ATTENDANCE_PREDICTION:
                from sklearn.linear_model import LogisticRegression
                model = LogisticRegression(**config.hyperparameters)
            else:
                from sklearn.ensemble import RandomForestClassifier
                model = RandomForestClassifier(**config.hyperparameters)
            
            # Train model
            model.fit(X_train, y_train)
            
            # Evaluate model
            y_pred = model.predict(X_test)
            
            metrics = {
                "accuracy": accuracy_score(y_test, y_pred),
                "precision": precision_score(y_test, y_pred, average='weighted'),
                "recall": recall_score(y_test, y_pred, average='weighted'),
                "f1_score": f1_score(y_test, y_pred, average='weighted'),
                "model_size": self._calculate_model_size(model)
            }
            
            logger.info("model_trained", 
                       model_type=config.model_type.value,
                       accuracy=metrics["accuracy"])
            
            return model, metrics
            
        except Exception as e:
            logger.error("model_training_failed", error=str(e))
            raise
    
    def _calculate_model_size(self, model) -> int:
        """Calculate model size in bytes."""
        try:
            model_bytes = pickle.dumps(model)
            return len(model_bytes)
        except:
            return 0
    
    async def _save_model(self, model, model_type: MLModelType, metrics: ModelMetrics) -> str:
        """Save trained model to storage."""
        try:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_filename = f"{model_type.value}_{version}.joblib"
            model_path = self.model_storage_path / model_filename
            
            # Save model
            joblib.dump(model, model_path)
            
            # Cache model metadata in Redis
            if self.redis_client:
                metadata = {
                    "model_type": model_type.value,
                    "version": version,
                    "path": str(model_path),
                    "metrics": asdict(metrics),
                    "created_at": datetime.now().isoformat()
                }
                self.redis_client.setex(
                    f"model_metadata:{model_type.value}:{version}",
                    timedelta(days=30),
                    json.dumps(metadata)
                )
            
            logger.info("model_saved", 
                       model_type=model_type.value,
                       version=version,
                       path=str(model_path))
            
            return str(model_path)
            
        except Exception as e:
            logger.error("model_saving_failed", error=str(e))
            raise
    
    async def _create_model_version(self, model_type: MLModelType, model_path: str, metrics: ModelMetrics, config: TrainingConfig) -> str:
        """Create model version record."""
        try:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            with self.SessionLocal() as session:
                # Deactivate previous versions
                previous_models = session.query(MLModel).filter(
                    MLModel.model_type == model_type.value,
                    MLModel.is_active == True
                ).all()
                
                for prev_model in previous_models:
                    prev_model.is_active = False
                
                # Create new model version
                ml_model = MLModel(
                    id=f"{model_type.value}_{version}",
                    model_type=model_type.value,
                    version=version,
                    status=ModelStatus.TRAINED.value,
                    trained_at=datetime.now(),
                    model_path=model_path,
                    metrics=json.dumps(asdict(metrics)),
                    config=json.dumps(asdict(config)),
                    environment=DeploymentEnvironment.DEVELOPMENT.value,
                    is_active=True
                )
                
                session.add(ml_model)
                session.commit()
            
            logger.info("model_version_created", 
                       model_type=model_type.value,
                       version=version)
            
            return version
            
        except Exception as e:
            logger.error("model_version_creation_failed", error=str(e))
            raise
    
    def _get_data_version(self, data_path: str) -> str:
        """Get data version hash."""
        try:
            # In production, this would calculate actual data hash
            return hashlib.md5(data_path.encode()).hexdigest()[:8]
        except:
            return "unknown"
    
    async def deploy_model(self, model_type: MLModelType, version: str, environment: DeploymentEnvironment) -> bool:
        """Deploy model to specified environment."""
        try:
            ai_operations_total.labels(operation="model_deployment", model=model_type.value, status="started").inc()
            
            with self.SessionLocal() as session:
                # Get model version
                model = session.query(MLModel).filter(
                    MLModel.model_type == model_type.value,
                    MLModel.version == version
                ).first()
                
                if not model:
                    raise ValueError(f"Model version not found: {model_type.value}:{version}")
                
                # Load model for validation
                loaded_model = joblib.load(model.model_path)
                
                # Validate model
                is_valid = await self._validate_model(loaded_model, model_type)
                if not is_valid:
                    raise ValueError("Model validation failed")
                
                # Update deployment status
                model.status = ModelStatus.DEPLOYED.value
                model.deployed_at = datetime.now()
                model.environment = environment.value
                
                # Deactivate other versions in this environment
                other_models = session.query(MLModel).filter(
                    MLModel.model_type == model_type.value,
                    MLModel.environment == environment.value,
                    MLModel.id != model.id
                ).all()
                
                for other_model in other_models:
                    other_model.is_active = False
                
                session.commit()
            
            # Cache deployed model
            self.deployed_models[f"{model_type.value}:{environment.value}"] = {
                "model": loaded_model,
                "version": version,
                "deployed_at": datetime.now()
            }
            
            ai_operations_total.labels(operation="model_deployment", model=model_type.value, status="success").inc()
            logger.info("model_deployed", 
                       model_type=model_type.value,
                       version=version,
                       environment=environment.value)
            
            return True
            
        except Exception as e:
            ai_operations_total.labels(operation="model_deployment", model=model_type.value, status="error").inc()
            logger.error("model_deployment_failed", 
                        model_type=model_type.value,
                        version=version,
                        error=str(e))
            return False
    
    async def _validate_model(self, model, model_type: MLModelType) -> bool:
        """Validate model before deployment."""
        try:
            # Basic validation checks
            if not hasattr(model, 'predict'):
                return False
            
            # Create test data
            if model_type == MLModelType.SENTIMENT_ANALYSIS:
                test_data = np.random.randn(10, 5000)  # TF-IDF features
            else:
                test_data = np.random.randn(10, 10)
            
            # Test prediction
            predictions = model.predict(test_data)
            
            # Validate prediction shape
            if len(predictions) != len(test_data):
                return False
            
            logger.info("model_validation_passed", model_type=model_type.value)
            return True
            
        except Exception as e:
            logger.error("model_validation_failed", model_type=model_type.value, error=str(e))
            return False
    
    async def get_model_for_inference(self, model_type: MLModelType, environment: DeploymentEnvironment = DeploymentEnvironment.PRODUCTION):
        """Get deployed model for inference."""
        try:
            cache_key = f"{model_type.value}:{environment.value}"
            
            # Check cache first
            if cache_key in self.deployed_models:
                return self.deployed_models[cache_key]["model"]
            
            # Load from database
            with self.SessionLocal() as session:
                model_record = session.query(MLModel).filter(
                    MLModel.model_type == model_type.value,
                    MLModel.environment == environment.value,
                    MLModel.is_active == True,
                    MLModel.status == ModelStatus.DEPLOYED.value
                ).first()
                
                if not model_record:
                    logger.warning("no_deployed_model_found", 
                                 model_type=model_type.value,
                                 environment=environment.value)
                    return None
                
                # Load model
                model = joblib.load(model_record.model_path)
                
                # Cache model
                self.deployed_models[cache_key] = {
                    "model": model,
                    "version": model_record.version,
                    "deployed_at": model_record.deployed_at
                }
                
                return model
            
        except Exception as e:
            logger.error("model_loading_for_inference_failed", 
                        model_type=model_type.value,
                        error=str(e))
            return None
    
    async def rollback_model(self, model_type: MLModelType, environment: DeploymentEnvironment) -> bool:
        """Rollback to previous model version."""
        try:
            with self.SessionLocal() as session:
                # Get current deployed model
                current_model = session.query(MLModel).filter(
                    MLModel.model_type == model_type.value,
                    MLModel.environment == environment.value,
                    MLModel.is_active == True
                ).first()
                
                if not current_model:
                    raise ValueError("No current model to rollback from")
                
                # Get previous version
                previous_model = session.query(MLModel).filter(
                    MLModel.model_type == model_type.value,
                    MLModel.environment == environment.value,
                    MLModel.id != current_model.id
                ).order_by(MLModel.deployed_at.desc()).first()
                
                if not previous_model:
                    raise ValueError("No previous version available for rollback")
                
                # Perform rollback
                current_model.is_active = False
                previous_model.is_active = True
                previous_model.status = ModelStatus.DEPLOYED.value
                previous_model.deployed_at = datetime.now()
                
                session.commit()
            
            # Clear cache
            cache_key = f"{model_type.value}:{environment.value}"
            if cache_key in self.deployed_models:
                del self.deployed_models[cache_key]
            
            logger.info("model_rollback_completed", 
                       model_type=model_type.value,
                       environment=environment.value,
                       rollback_to=previous_model.version)
            
            return True
            
        except Exception as e:
            logger.error("model_rollback_failed", error=str(e))
            return False
    
    async def get_model_metrics(self, model_type: MLModelType, environment: DeploymentEnvironment) -> Optional[Dict]:
        """Get metrics for deployed model."""
        try:
            with self.SessionLocal() as session:
                model = session.query(MLModel).filter(
                    MLModel.model_type == model_type.value,
                    MLModel.environment == environment.value,
                    MLModel.is_active == True
                ).first()
                
                if not model:
                    return None
                
                metrics = json.loads(model.metrics) if model.metrics else {}
                config = json.loads(model.config) if model.config else {}
                
                return {
                    "model_id": model.id,
                    "version": model.version,
                    "status": model.status,
                    "metrics": metrics,
                    "config": config,
                    "deployed_at": model.deployed_at.isoformat() if model.deployed_at else None,
                    "environment": model.environment
                }
            
        except Exception as e:
            logger.error("model_metrics_retrieval_failed", error=str(e))
            return None
    
    async def list_model_versions(self, model_type: MLModelType) -> List[Dict]:
        """List all versions of a model type."""
        try:
            with self.SessionLocal() as session:
                models = session.query(MLModel).filter(
                    MLModel.model_type == model_type.value
                ).order_by(MLModel.created_at.desc()).all()
                
                versions = []
                for model in models:
                    version_info = {
                        "id": model.id,
                        "version": model.version,
                        "status": model.status,
                        "created_at": model.created_at.isoformat(),
                        "trained_at": model.trained_at.isoformat() if model.trained_at else None,
                        "deployed_at": model.deployed_at.isoformat() if model.deployed_at else None,
                        "environment": model.environment,
                        "is_active": model.is_active
                    }
                    
                    if model.metrics:
                        version_info["metrics"] = json.loads(model.metrics)
                    
                    versions.append(version_info)
                
                return versions
            
        except Exception as e:
            logger.error("model_versions_listing_failed", error=str(e))
            return []
    
    async def get_training_job_status(self, job_id: str) -> Optional[Dict]:
        """Get status of training job."""
        try:
            # Check active jobs first
            if job_id in self.active_training_jobs:
                return self.active_training_jobs[job_id]
            
            # Check database
            with self.SessionLocal() as session:
                job = session.query(TrainingJob).filter(TrainingJob.id == job_id).first()
                
                if not job:
                    return None
                
                job_status = {
                    "id": job.id,
                    "model_type": job.model_type,
                    "status": job.status,
                    "started_at": job.started_at.isoformat(),
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "error_message": job.error_message
                }
                
                if job.config:
                    job_status["config"] = json.loads(job.config)
                
                if job.metrics:
                    job_status["metrics"] = json.loads(job.metrics)
                
                return job_status
            
        except Exception as e:
            logger.error("training_job_status_retrieval_failed", job_id=job_id, error=str(e))
            return None
    
    async def cleanup_old_models(self, retention_days: int = 30):
        """Clean up old model versions."""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            with self.SessionLocal() as session:
                # Get old inactive models
                old_models = session.query(MLModel).filter(
                    MLModel.created_at < cutoff_date,
                    MLModel.is_active == False,
                    MLModel.status != ModelStatus.DEPLOYED.value
                ).all()
                
                cleaned_count = 0
                for model in old_models:
                    try:
                        # Remove model file
                        if model.model_path and os.path.exists(model.model_path):
                            os.remove(model.model_path)
                        
                        # Remove database record
                        session.delete(model)
                        cleaned_count += 1
                        
                    except Exception as e:
                        logger.error("model_cleanup_failed", model_id=model.id, error=str(e))
                
                session.commit()
            
            logger.info("model_cleanup_completed", cleaned_count=cleaned_count)
            return cleaned_count
            
        except Exception as e:
            logger.error("model_cleanup_failed", error=str(e))
            return 0

# Global ML pipeline service instance
ml_pipeline_service = MLPipelineService()