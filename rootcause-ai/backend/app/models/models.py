from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    service = Column(String(100), nullable=False)
    severity = Column(String(20), default="warning")   # critical | warning | info
    status = Column(String(20), default="active")      # active | resolved
    error_message = Column(Text, default="")
    logs = Column(JSON, default=list)      # [{ts, service, level, message}]
    metrics = Column(JSON, default=list)   # [{ts, cpu, memory, latency, error_rate, db_conn}]
    events = Column(JSON, default=list)    # [{ts, type, description}]
    is_demo = Column(Integer, default=0)
    resolution_notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    analyses = relationship("Analysis", back_populates="incident", cascade="all, delete-orphan",
                            order_by="Analysis.id.desc()")

class Analysis(Base):
    __tablename__ = "analyses"
    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    result = Column(JSON, nullable=False)
    explanation = Column(JSON, nullable=True)
    explanation_source = Column(String(20), default="local")
    created_at = Column(DateTime, default=datetime.utcnow)
    incident = relationship("Incident", back_populates="analyses")
