"""
Pruebas de integración de endpoints con TestClient de FastAPI.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_endpoints():
    print("1. Probando GET /health...")
    r = client.get("/health")
    assert r.status_code == 200
    print("   ->", r.json())

    print("2. Probando POST /api/v1/reviews/scan (simular 3 reseñas)...")
    r = client.post("/api/v1/reviews/scan", json={"count": 3, "force_negative": False})
    assert r.status_code == 200
    print("   ->", r.json())

    print("3. Probando POST /api/v1/reviews/webhook...")
    payload = {
        "author_name": "Marcos Test",
        "rating": 1,
        "text": "Comida fria y pesima atencion del camarero.",
        "business_name": "Restaurante Parrilla Los Olivos",
        "source": "Webhook Test"
    }
    r = client.post("/api/v1/reviews/webhook", json=payload)
    assert r.status_code == 201
    created_review = r.json()
    review_id = created_review["id"]
    print(f"   -> Reseña creada con ID={review_id}, Sentimiento={created_review['sentiment']}")

    print("4. Probando GET /api/v1/reviews...")
    r = client.get("/api/v1/reviews")
    assert r.status_code == 200
    reviews = r.json()
    print(f"   -> Total reseñas recuperadas: {len(reviews)}")

    print(f"5. Probando POST /api/v1/reviews/{review_id}/approve...")
    approve_payload = {
        "final_response": "Estimado Marcos, lamentamos profundamente el inconveniente. Le invitamos a contactar con gerencia.",
        "response_status": "Publicada"
    }
    r = client.post(f"/api/v1/reviews/{review_id}/approve", json=approve_payload)
    assert r.status_code == 200
    assert r.json()["response_status"] == "Publicada"
    print("   -> Respuesta aprobada con éxito.")

    print("6. Probando GET /api/v1/stats...")
    r = client.get("/api/v1/stats")
    assert r.status_code == 200
    stats = r.json()
    print(f"   -> Estadísticas: Total={stats['total_reviews']}, Media={stats['average_rating']}, Negativas={stats['negative_reviews_count']}")

    print("\n[EXITO] Todos los endpoints de la API respondieron correctamente!")

if __name__ == "__main__":
    test_endpoints()

