"""
Esquemas de validación y serialización con Pydantic.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ReviewCreateWebhook(BaseModel):
    """Esquema para recepción de eventos de nuevas reseñas vía Webhook."""
    external_review_id: Optional[str] = Field(None, description="Identificador único externo de la reseña")
    business_name: Optional[str] = Field(None, description="Nombre del negocio evaluado")
    author_name: str = Field(..., description="Nombre del autor de la reseña")
    author_photo_url: Optional[str] = Field(None, description="URL del avatar del autor")
    rating: int = Field(..., ge=1, le=5, description="Calificación de 1 a 5 estrellas")
    text: str = Field(..., min_length=1, description="Texto de la reseña del cliente")
    published_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Fecha de publicación")
    source: Optional[str] = Field("Webhook", description="Origen de la reseña (Google Maps, Webhook, etc.)")


class ReviewUpdateResponse(BaseModel):
    """Esquema para actualizar la respuesta y el estado de una reseña."""
    final_response: str = Field(..., min_length=3, description="Texto final de la respuesta al cliente")
    response_status: str = Field("Aprobada", description="Estado: Pendiente, Aprobada, Publicada, Descartada")


class ReviewRead(BaseModel):
    """Esquema de salida completo para una reseña."""
    id: int
    external_review_id: str
    business_name: str
    author_name: str
    author_photo_url: Optional[str]
    rating: int
    text: str
    published_at: datetime
    source: str
    sentiment: str
    sentiment_score: float
    urgency_level: str
    key_issues: Optional[str]
    suggested_response: Optional[str]
    response_status: str
    final_response: Optional[str]
    alert_sent: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScanRequest(BaseModel):
    """Parámetros de solicitud para ejecutar una sincronización o rastreo de reseñas."""
    count: int = Field(5, ge=1, le=20, description="Cantidad de reseñas a sincronizar/simular")
    force_negative: bool = Field(False, description="Forzar generación de reseñas negativas para probar alertas")
    place_id: Optional[str] = Field(None, description="Google Place ID opcional para consulta real")


class ScanResponse(BaseModel):
    """Resultado de la sincronización de reseñas."""
    status: str
    scanned_total: int
    new_imported: int
    critical_alerts_triggered: int
    message: str


class AISentimentAnalysisResult(BaseModel):
    """Estructura normalizada del resultado del análisis de IA."""
    sentiment: str = Field(..., description="Positiva, Neutra o Negativa")
    sentiment_score: float = Field(..., description="Puntuación de -1.0 a 1.0")
    urgency_level: str = Field(..., description="Alta, Media o Baja")
    key_issues: List[str] = Field(default_factory=list, description="Lista de problemas o halagos detectados")
    suggested_response: str = Field(..., description="Respuesta diplomática sugerida")


class StatsResponse(BaseModel):
    """Estadísticas globales de reputación para el panel de control."""
    total_reviews: int
    average_rating: float
    negative_reviews_count: int
    neutral_reviews_count: int
    positive_reviews_count: int
    pending_responses_count: int
    alerts_triggered_count: int
    rating_distribution: dict

