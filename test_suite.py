"""
Script de verificación de extremo a extremo para el MVP.
"""

import asyncio
from app.database import init_db, SessionLocal
from app.models import Review
from app.services.scraper_service import scraper_service
from app.services.ai_service import ai_service
from app.services.notification_service import notification_service
from app.main import process_and_save_review

async def main():
    print("1. Inicializando base de datos...")
    init_db()

    print("2. Probando generador de reseñas...")
    reviews = scraper_service.generate_simulated_reviews(count=2, force_negative=True)
    assert len(reviews) == 2
    print(f"   -> Generadas {len(reviews)} reseñas de {reviews[0]['author_name']} ({reviews[0]['rating']} estrellas)")

    print("3. Probando análisis de IA y generación de respuesta...")
    ai_res = await ai_service.analyze_and_draft_response(
        business_name=reviews[0]['business_name'],
        author_name=reviews[0]['author_name'],
        rating=reviews[0]['rating'],
        text=reviews[0]['text']
    )
    print(f"   -> Sentimiento: {ai_res.sentiment} (Score: {ai_res.sentiment_score})")
    print(f"   -> Urgencia: {ai_res.urgency_level}")
    print(f"   -> Respuesta sugerida:\n---\n{ai_res.suggested_response}\n---")

    print("4. Probando guardado en Base de Datos e Ingesta...")
    db = SessionLocal()
    try:
        saved = await process_and_save_review(reviews[0], db)
        print(f"   -> Reseña guardada con ID={saved.id}, Status={saved.response_status}, Sentiment={saved.sentiment}")
        
        # Validar persistencia
        found = db.query(Review).filter(Review.id == saved.id).first()
        assert found is not None
        print(f"   -> Reseña verificada en DB: {found.author_name} - {found.rating} estrellas")
    finally:
        db.close()

    print("\n[EXITO] Todos los modulos del nucleo funcionan a la perfeccion!")

if __name__ == "__main__":
    asyncio.run(main())
