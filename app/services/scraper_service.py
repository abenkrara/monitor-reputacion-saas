"""
Servicio de ingesta y scraping de reseñas para negocios locales.
Permite consultar la API oficial de Google Places o ejecutar un simulador
avanzado y realista de reseñas en español.
"""

import uuid
import random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Banco de reseñas simuladas con tono realista para negocios locales
SAMPLE_REVIEWS_CATALOG = {
    1: [
        {
            "author": "Carlos Mendoza",
            "text": "Pésima experiencia. Esperamos más de 55 minutos por dos platos principales y cuando llegaron estaban completamente fríos. El camarero mostró mala actitud cuando se lo comentamos y ni siquiera ofrecieron una disculpa. No volveremos jamás.",
        },
        {
            "author": "Lucía Fernández",
            "text": "Muy decepcionada. Teníamos reserva para 6 personas a las 21:30 y nos hicieron esperar de pie 40 minutos. Además, la cuenta incluía dos bebidas que jamás consumimos. Una falta de respeto total hacia el cliente.",
        },
        {
            "author": "Javier Morales",
            "text": "La comida llegó cruda en el centro. Al avisar al personal nos dijeron de mala gana que 'así se sirve'. Terminamos con dolor de estómago y arruinaron nuestra celebración familiar.",
        },
        {
            "author": "Marina Gómez",
            "text": "Atención al cliente nefasta. Llamé para consultar sobre alérgenos antes de ir y me aseguraron que no habría problema. Al llegar nadie sabía nada y el responsable ni dio la cara. Muy poco profesionales.",
        }
    ],
    2: [
        {
            "author": "Andrés Soto",
            "text": "La comida es aceptable, pero el servicio es sumamente lento y desorganizado. Tuvimos que pedir los cubiertos tres veces y la música estaba tan alta que no se podía mantener una conversación.",
        },
        {
            "author": "Elena Romero",
            "text": "Solía ser mi lugar favorito, pero la calidad ha bajado mucho. Las raciones son notablemente más pequeñas y los precios han aumentado un 25%. Una pena, no creo que vuelva pronto.",
        },
        {
            "author": "Roberto Navarro",
            "text": "El local estaba sucio y con mesas sin recoger. El personal parecía desbordado a pesar de que el local estaba a media capacidad. Mucho margen de mejora.",
        }
    ],
    3: [
        {
            "author": "Patricia Vega",
            "text": "Un lugar normal, sin pena ni gloria. La comida correcta pero nada memorable. El servicio cumplió lo justo. Por ese precio hay mejores alternativas en la zona.",
        },
        {
            "author": "Marcos Gil",
            "text": "El entrante estuvo muy rico, pero el plato de fondo llegó tibio. Los camareros fueron amables pero tardaron bastante en traer la cuenta. Regular.",
        }
    ],
    4: [
        {
            "author": "David Ortiz",
            "text": "Muy buena experiencia general. La comida sabrosa y el punto de la carne perfecto. Tuvimos que esperar 10 minutos por la mesa a pesar de tener reserva, pero lo compensaron con un café de cortesía.",
        },
        {
            "author": "Silvia Campos",
            "text": "Gran ambiente y platos bien presentados. El personal es atento y educado. Totalmente recomendable para una cena en pareja o con amigos.",
        }
    ],
    5: [
        {
            "author": "Alejandro Ruiz",
            "text": "¡Extraordinario de principio a fin! La atención de Juanjo fue impecable, recomendándonos el vino perfecto. La comida exquisita y el postre casero sublime. Sin duda nuestro nuevo sitio de referencia.",
        },
        {
            "author": "Beatriz Herrera",
            "text": "10 de 10. Calidad de producto insuperable, tiempos de espera mínimos y un trato cercano y profesional. Se nota el cariño y la pasión que ponen en cada detalle.",
        },
        {
            "author": "Gonzalo Domínguez",
            "text": "Excelente relación calidad-precio. Local impecable, personal amable y comida deliciosa. Volveremos muy pronto con toda la familia.",
        }
    ]
}


class ScraperService:
    """Servicio encargado de recuperar reseñas vía API oficial o generador simulado."""

    def __init__(self):
        self.api_key = settings.GOOGLE_PLACES_API_KEY
        self.default_place_id = settings.BUSINESS_PLACE_ID
        self.business_name = settings.BUSINESS_NAME

    async def fetch_real_google_places_reviews(self, place_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Consulta la API de Google Places (Place Details) si se proporciona una API Key válida.
        Documentación: https://developers.google.com/maps/documentation/places/web-service/details
        """
        target_place_id = place_id or self.default_place_id
        if not self.api_key or not target_place_id:
            logger.warning("No hay Google Places API Key configurada. Usando simulador.")
            return []

        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": target_place_id,
            "fields": "name,rating,reviews",
            "language": "es",
            "key": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                data = response.json()

                if data.get("status") != "OK":
                    logger.error(f"Error al consultar Google Places API: {data.get('status')} - {data.get('error_message')}")
                    return []

                result = data.get("result", {})
                biz_name = result.get("name", self.business_name)
                raw_reviews = result.get("reviews", [])

                formatted = []
                for r in raw_reviews:
                    # El timestamp de Google Places viene en segundos Unix
                    pub_time = datetime.utcfromtimestamp(r.get("time", int(datetime.utcnow().timestamp())))
                    formatted.append({
                        "external_review_id": f"gplaces_{r.get('author_url', '').split('/')[-1] or uuid.uuid4().hex[:12]}",
                        "business_name": biz_name,
                        "author_name": r.get("author_name", "Usuario de Google"),
                        "author_photo_url": r.get("profile_photo_url"),
                        "rating": int(r.get("rating", 3)),
                        "text": r.get("text", ""),
                        "published_at": pub_time,
                        "source": "Google Places API"
                    })
                return formatted
        except Exception as e:
            logger.error(f"Excepción al conectar con Google Places API: {e}", exc_info=True)
            return []

    def generate_simulated_reviews(
        self,
        count: int = 5,
        force_negative: bool = False,
        business_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Genera reseñas sintéticas hiperrealistas para pruebas de estrés, demostraciones y MVP.
        Permite simular tanto flujo orgánico mixto como ataques/incidentes de reseñas negativas.
        """
        target_name = business_name or self.business_name
        generated: List[Dict[str, Any]] = []

        for i in range(count):
            if force_negative:
                # 1 o 2 estrellas para disparar alertas inmediatas
                rating = random.choice([1, 1, 2])
            else:
                # Distribución realista: 65% positivas, 15% neutras, 20% negativas
                rating = random.choices([1, 2, 3, 4, 5], weights=[0.12, 0.08, 0.15, 0.25, 0.40])[0]

            candidate_templates = SAMPLE_REVIEWS_CATALOG.get(rating, SAMPLE_REVIEWS_CATALOG[3])
            template = random.choice(candidate_templates)

            # Generar fecha reciente en los últimos 7 días
            minutes_ago = random.randint(5, 7 * 24 * 60)
            published_at = datetime.utcnow() - timedelta(minutes=minutes_ago)

            external_id = f"sim_{uuid.uuid4().hex[:12]}"

            generated.append({
                "external_review_id": external_id,
                "business_name": target_name,
                "author_name": template["author"],
                "author_photo_url": f"https://api.dicebear.com/7.x/initials/svg?seed={template['author']}",
                "rating": rating,
                "text": template["text"],
                "published_at": published_at,
                "source": "Mock Simulator"
            })

        return generated

    async def ingest_reviews(
        self,
        count: int = 5,
        force_negative: bool = False,
        place_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Punto de entrada principal: intenta obtener reseñas reales de Google Places
        si hay API Key; en caso contrario, utiliza el simulador avanzado.
        """
        if self.api_key and (place_id or self.default_place_id):
            real_reviews = await self.fetch_real_google_places_reviews(place_id=place_id)
            if real_reviews:
                return real_reviews[:count]

        # Modo simulador estructurado
        return self.generate_simulated_reviews(
            count=count,
            force_negative=force_negative,
            business_name=self.business_name
        )


scraper_service = ScraperService()

