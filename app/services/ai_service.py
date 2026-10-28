"""
Servicio de Inteligencia Artificial para análisis de sentimiento y generación
de respuestas diplomáticas de desescalada con Groq y OpenAI.
"""

import json
import logging
import re
from typing import Dict, Any, List
from app.config import get_settings
from app.schemas import AISentimentAnalysisResult

logger = logging.getLogger(__name__)
settings = get_settings()


class AIService:
    """Gestiona el análisis semántico y la generación de respuestas de reputación."""

    def __init__(self):
        self.provider = settings.AI_PROVIDER.lower()
        self._groq_client = None
        self._openai_client = None

    def _get_groq_client(self):
        if self._groq_client is None:
            if not settings.is_groq_configured:
                return None
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=settings.GROQ_API_KEY)
            except Exception as e:
                logger.error(f"Error inicializando cliente Groq: {e}")
                return None
        return self._groq_client

    def _get_openai_client(self):
        if self._openai_client is None:
            if not settings.is_openai_configured:
                return None
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception as e:
                logger.error(f"Error inicializando cliente OpenAI: {e}")
                return None
        return self._openai_client

    def _build_system_prompt(self) -> str:
        return (
            "Eres un Director Senior de Reputación Online y Atención al Cliente para negocios locales y hostelería. "
            "Tu objetivo es procesar reseñas de clientes, evaluar su sentimiento con precisión y redactar "
            "respuestas diplomáticas, empáticas y altamente profesionales.\n\n"
            "Directrices para la respuesta:\n"
            "1. Si la reseña es negativa (1 o 2 estrellas):\n"
            "   - Saluda al cliente cordialmente por su nombre.\n"
            "   - Muestra empatía genuina y asume responsabilidad constructiva sin ser servil ni defensivo.\n"
            "   - Reconoce específicamente los puntos de fricción mencionados.\n"
            "   - Ofrece una vía de resolución directa e inmediata (ej: contacto con gerencia vía email o teléfono privado).\n"
            "   - Invita a dar una segunda oportunidad para demostrar el verdadero estándar del local.\n"
            "2. Si la reseña es positiva (4 o 5 estrellas):\n"
            "   - Agradece con calidez el comentario y resalta el compromiso del equipo.\n"
            "   - Invita amablemente a visitarlos de nuevo pronto.\n"
            "3. Si la reseña es neutra (3 estrellas):\n"
            "   - Agradece el feedback sincero y pregunta cómo se podría convertir su experiencia en un 5 estrellas.\n\n"
            "RESPONDE OBLIGATORIAMENTE EN FORMATO JSON ESTRICTO CON LA SIGUIENTE ESTRUCTURA:\n"
            "{\n"
            '  "sentiment": "Positiva" | "Neutra" | "Negativa",\n'
            '  "sentiment_score": float entre -1.0 y 1.0,\n'
            '  "urgency_level": "Alta" | "Media" | "Baja",\n'
            '  "key_issues": ["tema 1", "tema 2"],\n'
            '  "suggested_response": "Texto de la respuesta en español..."\n'
            "}"
        )

    def _build_user_prompt(self, business_name: str, author_name: str, rating: int, text: str) -> str:
        return (
            f"Analiza la siguiente reseña recibida en Google Places:\n"
            f"- Negocio: {business_name}\n"
            f"- Autor de la reseña: {author_name}\n"
            f"- Calificación en estrellas: {rating} / 5\n"
            f"- Contenido de la reseña: \"{text}\"\n\n"
            f"Devuelve únicamente el bloque JSON válido con el análisis y la propuesta de respuesta."
        )

    async def analyze_and_draft_response(
        self,
        business_name: str,
        author_name: str,
        rating: int,
        text: str
    ) -> AISentimentAnalysisResult:
        """
        Ejecuta el análisis y generación utilizando Groq u OpenAI según la configuración.
        Si las claves no están presentes o fallan, recurre a un motor heurístico de contingencia.
        """
        # 1. Intentar con Groq si está seleccionado o configurado
        if self.provider == "groq" and settings.is_groq_configured:
            res = await self._call_groq(business_name, author_name, rating, text)
            if res:
                return res

        # 2. Intentar con OpenAI si está configurado
        if (self.provider == "openai" or not settings.is_groq_configured) and settings.is_openai_configured:
            res = await self._call_openai(business_name, author_name, rating, text)
            if res:
                return res

        # 3. Motor heurístico de respaldo (garantiza funcionamiento sin API keys configuradas)
        logger.info("Utilizando motor heurístico de contingencia para análisis de reseña.")
        return self._heuristic_fallback(business_name, author_name, rating, text)

    async def _call_groq(
        self, business_name: str, author_name: str, rating: int, text: str
    ) -> AISentimentAnalysisResult | None:
        try:
            client = self._get_groq_client()
            if not client:
                return None

            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(business_name, author_name, rating, text)

            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=settings.GROQ_MODEL,
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            raw_content = chat_completion.choices[0].message.content
            return self._parse_json_result(raw_content, rating, author_name, business_name)
        except Exception as e:
            logger.error(f"Error invocando API de Groq: {e}", exc_info=True)
            return None

    async def _call_openai(
        self, business_name: str, author_name: str, rating: int, text: str
    ) -> AISentimentAnalysisResult | None:
        try:
            client = self._get_openai_client()
            if not client:
                return None

            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(business_name, author_name, rating, text)

            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=settings.OPENAI_MODEL,
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            raw_content = response.choices[0].message.content
            return self._parse_json_result(raw_content, rating, author_name, business_name)
        except Exception as e:
            logger.error(f"Error invocando API de OpenAI: {e}", exc_info=True)
            return None

    def _parse_json_result(
        self, raw_content: str, rating: int, author_name: str, business_name: str
    ) -> AISentimentAnalysisResult:
        """Parsea y valida la respuesta JSON retornada por el LLM."""
        try:
            data = json.loads(raw_content)
            sentiment = data.get("sentiment", "Neutra")
            if sentiment not in ["Positiva", "Neutra", "Negativa"]:
                sentiment = "Negativa" if rating <= 2 else ("Positiva" if rating >= 4 else "Neutra")

            score = float(data.get("sentiment_score", 0.0))
            urgency = data.get("urgency_level", "Alta" if rating <= 2 else "Baja")
            issues = data.get("key_issues", [])
            suggested = data.get("suggested_response", "").strip()

            if not suggested:
                suggested = self._generate_fallback_response(rating, author_name, business_name, text="")

            return AISentimentAnalysisResult(
                sentiment=sentiment,
                sentiment_score=score,
                urgency_level=urgency,
                key_issues=issues if isinstance(issues, list) else [str(issues)],
                suggested_response=suggested
            )
        except Exception as e:
            logger.error(f"Error parseando JSON de IA: {e}. Contenido crudo: {raw_content}")
            return self._heuristic_fallback(business_name, author_name, rating, "")

    def _heuristic_fallback(
        self, business_name: str, author_name: str, rating: int, text: str
    ) -> AISentimentAnalysisResult:
        """
        Generador heurístico de alta calidad.
        Permite que el sistema sea 100% operativo incluso sin conexión a Groq/OpenAI.
        """
        text_lower = text.lower()
        negative_keywords = ["pésima", "mal", "frío", "lento", "espera", "caro", "sucio", "grosero", "decepción", "dolor", "reclamo"]
        positive_keywords = ["excelente", "delicioso", "maravilloso", "increíble", "gracias", "recomiendo", "bueno", "amable"]

        neg_matches = [w for w in negative_keywords if w in text_lower]
        pos_matches = [w for w in positive_keywords if w in text_lower]

        if rating <= 2:
            sentiment = "Negativa"
            score = -0.85 if rating == 1 else -0.55
            urgency = "Alta"
            issues = neg_matches or ["inconformidad con el servicio/producto"]
        elif rating >= 4:
            sentiment = "Positiva"
            score = 0.90 if rating == 5 else 0.65
            urgency = "Baja"
            issues = pos_matches or ["satisfacción general del cliente"]
        else:
            sentiment = "Neutra"
            score = 0.05
            urgency = "Media"
            issues = ["oportunidad de mejora en el servicio"]

        suggested = self._generate_fallback_response(rating, author_name, business_name, text)

        return AISentimentAnalysisResult(
            sentiment=sentiment,
            sentiment_score=score,
            urgency_level=urgency,
            key_issues=issues,
            suggested_response=suggested
        )

    def _generate_fallback_response(
        self, rating: int, author_name: str, business_name: str, text: str
    ) -> str:
        """Plantillas diplomáticas de desescalada elaboradas por expertos en relaciones públicas."""
        name = author_name if author_name else "estimado cliente"

        if rating <= 2:
            return (
                f"Estimado/a {name},\n\n"
                f"Lamentamos profundamente leer sobre su experiencia en {business_name}. "
                f"Lo que describe no refleja en absoluto el estándar de calidad y calidez que nos esforzamos en brindar cada día. "
                f"Hemos tomado nota detallada de sus comentarios para revisar lo ocurrido con nuestro equipo de manera inmediata.\n\n"
                f"Nos gustaría tener la oportunidad de conversar con usted en persona y compensar el inconveniente. "
                f"Por favor, escríbanos directamente a gerencia@{business_name.lower().replace(' ', '')}.com para atenderle de forma prioritaria.\n\n"
                f"Atentamente,\n"
                f"La Dirección de {business_name}"
            )
        elif rating == 3:
            return (
                f"Hola {name},\n\n"
                f"Agradecemos su visita y el tiempo dedicado a dejarnos su valoración en {business_name}. "
                f"Nos alegra saber que ciertos aspectos fueron correctos, pero queremos aspirar a brindarle siempre una experiencia de 5 estrellas. "
                f"Tomamos en cuenta sus observaciones para seguir mejorando día a día.\n\n"
                f"Esperamos recibirle pronto nuevamente para superar sus expectativas.\n\n"
                f"Un cordial saludo,\n"
                f"Equipo de {business_name}"
            )
        else:
            return (
                f"¡Muchísimas gracias {name}!\n\n"
                f"Nos llena de alegría saber que disfrutó de su experiencia en {business_name}. "
                f"Comentarios tan positivos como el suyo motivan a todo nuestro equipo a seguir dando lo mejor en cada detalle.\n\n"
                f"¡Será un auténtico placer recibirle de nuevo muy pronto!\n\n"
                f"Un abrazo,\n"
                f"El equipo de {business_name}"
            )


ai_service = AIService()

