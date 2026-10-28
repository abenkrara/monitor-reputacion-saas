"""
Servidor principal FastAPI para el Micro-SaaS de Reputación Local y Reseñas.
Expone endpoints REST y Webhooks para ingesta, análisis y gestión de respuestas con IA.
"""

import logging
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.config import get_settings
from app.database import init_db, get_db
from app.models import Review
from app.schemas import (
    ReviewCreateWebhook,
    ReviewRead,
    ReviewUpdateResponse,
    ScanRequest,
    ScanResponse,
    StatsResponse,
)
from app.services.scraper_service import scraper_service
from app.services.ai_service import ai_service
from app.services.notification_service import notification_service

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("reputation_app")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación: inicialización de la base de datos al arrancar."""
    logger.info("Iniciando Micro-SaaS de Monitor de Reputación Local...")
    init_db()
    logger.info(f"Base de datos lista en: {settings.DATABASE_URL}")
    yield
    logger.info("Cerrando aplicación...")


app = FastAPI(
    title="API de Monitor de Reputación Local y Reseñas Negativas",
    description="Micro-SaaS B2B para monitorear reseñas críticas, disparar alertas y generar respuestas con IA.",
    version="1.0.0",
    lifespan=lifespan
)

# Permitir CORS para integración con dashboards o frontends externos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# ENDPOINTS GENERALES Y SALUD
# ============================================================================

@app.get("/", tags=["General"])
def root():
    """Ruta raíz de bienvenida con información del servicio."""
    return {
        "service": "Monitor de Reputación Local y Reseñas B2B",
        "status": "online",
        "business": settings.BUSINESS_NAME,
        "ai_provider": settings.AI_PROVIDER,
        "docs_url": "/docs"
    }


@app.get("/health", tags=["General"])
def health_check():
    """Chequeo de salud del servicio y estado de configuración."""
    return {
        "status": "healthy",
        "database": "connected",
        "groq_ready": settings.is_groq_configured,
        "openai_ready": settings.is_openai_configured,
        "telegram_ready": settings.is_telegram_configured,
        "email_ready": settings.is_email_configured
    }


# ============================================================================
# INGESTA: WEBHOOKS Y RASTREADOR (SCRAPER)
# ============================================================================

async def process_and_save_review(review_dict: dict, db: Session) -> Review:
    """
    Función auxiliar: analiza el sentimiento con IA, verifica si debe enviar alertas
    y persiste la reseña en la base de datos.
    """
    ext_id = review_dict.get("external_review_id")
    existing = db.query(Review).filter(Review.external_review_id == ext_id).first()
    if existing:
        return existing

    biz_name = review_dict.get("business_name") or settings.BUSINESS_NAME
    author = review_dict.get("author_name", "Cliente")
    rating = int(review_dict.get("rating", 3))
    text = review_dict.get("text", "")
    source = review_dict.get("source", "Webhook")
    photo = review_dict.get("author_photo_url")
    published_at = review_dict.get("published_at")

    # 1. Análisis con IA de sentimiento y generación de respuesta diplomática
    ai_result = await ai_service.analyze_and_draft_response(
        business_name=biz_name,
        author_name=author,
        rating=rating,
        text=text
    )

    # 2. Despachar alerta si la reseña es crítica (1 o 2 estrellas)
    alert_success = False
    if rating <= settings.ALERT_ON_STARS_LEQ:
        alert_success = await notification_service.dispatch_negative_alert(
            business_name=biz_name,
            author_name=author,
            rating=rating,
            text=text,
            urgency=ai_result.urgency_level,
            suggested_response=ai_result.suggested_response,
            source=source
        )

    # 3. Guardar en Base de Datos
    new_review = Review(
        external_review_id=ext_id,
        business_name=biz_name,
        author_name=author,
        author_photo_url=photo,
        rating=rating,
        text=text,
        published_at=published_at,
        source=source,
        sentiment=ai_result.sentiment,
        sentiment_score=ai_result.sentiment_score,
        urgency_level=ai_result.urgency_level,
        key_issues=", ".join(ai_result.key_issues) if ai_result.key_issues else None,
        suggested_response=ai_result.suggested_response,
        response_status="Pendiente",
        final_response=None,
        alert_sent=alert_success
    )

    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    return new_review


@app.post("/api/v1/reviews/webhook", response_model=ReviewRead, status_code=status.HTTP_201_CREATED, tags=["Ingesta"])
async def receive_review_webhook(
    payload: ReviewCreateWebhook,
    db: Session = Depends(get_db)
):
    """
    Webhook público para recibir eventos en tiempo real de nuevas reseñas desde
    Make, Zapier, Google Cloud Pub/Sub o extensiones de scraping externas.
    """
    ext_id = payload.external_review_id or f"hook_{func.random()}"

    review_dict = {
        "external_review_id": ext_id,
        "business_name": payload.business_name or settings.BUSINESS_NAME,
        "author_name": payload.author_name,
        "author_photo_url": payload.author_photo_url,
        "rating": payload.rating,
        "text": payload.text,
        "published_at": payload.published_at,
        "source": payload.source or "Webhook"
    }

    created = await process_and_save_review(review_dict, db)
    return created


@app.post("/api/v1/reviews/scan", response_model=ScanResponse, tags=["Ingesta"])
async def trigger_scraper_scan(
    request: ScanRequest,
    db: Session = Depends(get_db)
):
    """
    Ejecuta el rastreador o el simulador estructurado de Google Places para ingerir
    nuevas reseñas, analizarlas con IA y alertar si hay quejas graves.
    """
    raw_reviews = await scraper_service.ingest_reviews(
        count=request.count,
        force_negative=request.force_negative,
        place_id=request.place_id
    )

    new_count = 0
    alerts_count = 0

    for r in raw_reviews:
        existing = db.query(Review).filter(Review.external_review_id == r["external_review_id"]).first()
        if not existing:
            saved = await process_and_save_review(r, db)
            new_count += 1
            if saved.alert_sent:
                alerts_count += 1

    msg = f"Sincronización completada: {new_count} nuevas reseñas procesadas."
    if alerts_count > 0:
        msg += f" Se dispararon {alerts_count} alertas críticas inmediatas."

    return ScanResponse(
        status="success",
        scanned_total=len(raw_reviews),
        new_imported=new_count,
        critical_alerts_triggered=alerts_count,
        message=msg
    )


# ============================================================================
# CONSULTA Y GESTIÓN DE RESEÑAS
# ============================================================================

@app.get("/api/v1/reviews", response_model=List[ReviewRead], tags=["Reseñas"])
def list_reviews(
    sentiment: Optional[str] = Query(None, description="Filtrar por Positiva, Neutra, Negativa"),
    rating: Optional[int] = Query(None, ge=1, le=5, description="Filtrar por número exacto de estrellas"),
    response_status: Optional[str] = Query(None, description="Filtrar por estado de respuesta: Pendiente, Aprobada, Publicada"),
    search: Optional[str] = Query(None, description="Buscar por autor o contenido"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Retorna el listado paginado de reseñas registradas con filtros avanzados."""
    query = db.query(Review)

    if sentiment:
        query = query.filter(Review.sentiment.ilike(sentiment))
    if rating:
        query = query.filter(Review.rating == rating)
    if response_status:
        query = query.filter(Review.response_status.ilike(response_status))
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Review.author_name.ilike(search_filter)) | (Review.text.ilike(search_filter))
        )

    # Ordenar por fecha de publicación descendente (más recientes primero)
    reviews = query.order_by(desc(Review.published_at), desc(Review.id)).offset(skip).limit(limit).all()
    return reviews


@app.get("/api/v1/reviews/{review_id}", response_model=ReviewRead, tags=["Reseñas"])
def get_review_detail(review_id: int, db: Session = Depends(get_db)):
    """Obtiene el detalle completo de una reseña específica por ID."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Reseña no encontrada.")
    return review


@app.post("/api/v1/reviews/{review_id}/approve", response_model=ReviewRead, tags=["Gestión de Respuestas"])
def approve_and_update_response(
    review_id: int,
    payload: ReviewUpdateResponse,
    db: Session = Depends(get_db)
):
    """
    Permite al dueño o community manager aprobar, editar y marcar como lista/publicada
    la respuesta generada por IA.
    """
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Reseña no encontrada.")

    review.final_response = payload.final_response
    review.response_status = payload.response_status
    db.commit()
    db.refresh(review)
    return review


@app.post("/api/v1/reviews/{review_id}/regenerate-ai", response_model=ReviewRead, tags=["Gestión de Respuestas"])
async def regenerate_ai_response(
    review_id: int,
    db: Session = Depends(get_db)
):
    """Vuelve a consultar a la IA para obtener un nuevo borrador de respuesta."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Reseña no encontrada.")

    ai_res = await ai_service.analyze_and_draft_response(
        business_name=review.business_name,
        author_name=review.author_name,
        rating=review.rating,
        text=review.text
    )

    review.suggested_response = ai_res.suggested_response
    review.sentiment = ai_res.sentiment
    review.sentiment_score = ai_res.sentiment_score
    review.urgency_level = ai_res.urgency_level
    if ai_res.key_issues:
        review.key_issues = ", ".join(ai_res.key_issues)

    db.commit()
    db.refresh(review)
    return review


# ============================================================================
# ESTADÍSTICAS Y AUDITORÍA
# ============================================================================

@app.get("/api/v1/stats", response_model=StatsResponse, tags=["Analítica"])
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Calcula las métricas clave de reputación para el panel de control."""
    total_reviews = db.query(Review).count()
    if total_reviews == 0:
        return StatsResponse(
            total_reviews=0,
            average_rating=0.0,
            negative_reviews_count=0,
            neutral_reviews_count=0,
            positive_reviews_count=0,
            pending_responses_count=0,
            alerts_triggered_count=0,
            rating_distribution={"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        )

    avg_rating = db.query(func.avg(Review.rating)).scalar() or 0.0
    neg_count = db.query(Review).filter(Review.rating <= 2).count()
    neu_count = db.query(Review).filter(Review.rating == 3).count()
    pos_count = db.query(Review).filter(Review.rating >= 4).count()
    pending_resp = db.query(Review).filter(Review.response_status == "Pendiente").count()
    alerts_count = db.query(Review).filter(Review.alert_sent == True).count()

    # Distribución por estrellas
    distribution = {}
    for star in range(1, 6):
        count_star = db.query(Review).filter(Review.rating == star).count()
        distribution[str(star)] = count_star

    return StatsResponse(
        total_reviews=total_reviews,
        average_rating=round(float(avg_rating), 2),
        negative_reviews_count=neg_count,
        neutral_reviews_count=neu_count,
        positive_reviews_count=pos_count,
        pending_responses_count=pending_resp,
        alerts_triggered_count=alerts_count,
        rating_distribution=distribution
    )


# ============================================================================
# DIAGNÓSTICO DE NOTIFICACIONES
# ============================================================================

@app.post("/api/v1/notifications/test-telegram", tags=["Diagnóstico"])
async def test_telegram_alert():
    """Envía un mensaje de prueba al bot de Telegram configurado."""
    result = await notification_service.test_telegram_connection()
    return result

