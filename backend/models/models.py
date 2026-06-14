from sqlalchemy import Column, Integer, String, Text, Float, TIMESTAMP, Boolean, JSON
from sqlalchemy.sql import func

from backend.database.db import Base


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    raw_log = Column(Text, nullable=False)
    source = Column(String, nullable=True, index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(Integer, nullable=False, index=True)

    classification = Column(String, nullable=False, index=True)
    confidence = Column(Float, nullable=True)

    prediction_source = Column(String, nullable=False, index=True)

    severity = Column(String, nullable=True, index=True)

    reasoning = Column(Text, nullable=True)
    solution = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(Integer, nullable=False, index=True)
    original_label = Column(String, nullable=True)
    correct_label = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class AlertConfig(Base):
    __tablename__ = "alert_configs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=True)
    min_severity = Column(String, nullable=False, default="critical")
    email = Column(String, nullable=True)
    webhook_url = Column(String, nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    sources = Column(JSON, nullable=False)
    severity = Column(String, nullable=False)
    log_ids = Column(JSON, nullable=False)
    window_start = Column(TIMESTAMP(timezone=True), nullable=False)
    window_end = Column(TIMESTAMP(timezone=True), nullable=False)
    resolved = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())