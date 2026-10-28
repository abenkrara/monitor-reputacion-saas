"""
Definición de modelos de datos relacionales con SQLAlchemy.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime
from app.database import Base


class Review(Base):
    """
    Modelo representativo de una reseña de cliente recopilada de Google Places,
    webhooks o servicios externos de reputación online.
    """
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    external_review_id = Column(String(128), unique=True, index=True, nullable=False)
    business_name = Column(String(255), nullable=False, default="Comercio Local")
    author_name = Column(String(255), nullable=False)
    author_photo_url = Column(String(500), nullable=True)
    rating = Column(Integer, nullable=False, index=True)  # De 1 a 5 estrellas
    text = Column(Text, nullable=False)
    published_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    source = Column(String(64), default="Google Maps")  # Google Maps, Webhook, Mock Simulator

    # Análisis de Sentimiento con IA
    sentiment = Column(String(32), default="Pendiente", index=True)  # Positiva, Neutra, Negativa
    sentiment_score = Column(Float, default=0.0)  # De -1.0 (muy negativa) a 1.0 (muy positiva)
    urgency_level = Column(String(32), default="Baja")  # Alta, Media, Baja
    key_issues = Column(Text, nullable=True)  # Problemas clave detectados (ej: 'demora, calidad comida')

    # Generación y Gestión de Respuesta
    suggested_response = Column(Text, nullable=True)  # Propuesta diplomática generada por IA
    response_status = Column(String(32), default="Pendiente", index=True)  # Pendiente, Aprobada, Publicada, Descartada
    final_response = Column(Text, nullable=True)  # Texto final aprobado/editado por el propietario

    # Notificaciones y Auditoría
    alert_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Convierte la entidad en un diccionario legible."""
        return {
            "id": self.id,
            "external_review_id": self.external_review_id,
            "business_name": self.business_name,
            "author_name": self.author_name,
            "author_photo_url": self.author_photo_url,
            "rating": self.rating,
            "text": self.text,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "source": self.source,
            "sentiment": self.sentiment,
            "sentiment_score": self.sentiment_score,
            "urgency_level": self.urgency_level,
            "key_issues": self.key_issues,
            "suggested_response": self.suggested_response,
            "response_status": self.response_status,
            "final_response": self.final_response,
            "alert_sent": self.alert_sent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

