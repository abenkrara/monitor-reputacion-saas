"""
Módulo de configuración centralizada de la aplicación.
Carga variables de entorno desde .env y expone parámetros validados.
"""

from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Configuración del Servidor FastAPI
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    DATABASE_URL: str = "sqlite:///./data/reviews.db"

    # Datos del Comercio Local a Monitorizar
    BUSINESS_NAME: str = "Restaurante Parrilla Los Olivos"
    BUSINESS_PLACE_ID: str = "ChIJN1t_tDeuEmsRUsoyG83frY4"
    GOOGLE_PLACES_API_KEY: str = ""

    # Configuración del Proveedor de IA
    AI_PROVIDER: str = "groq"  # "groq" o "openai"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Alertas y Notificaciones (Telegram Bot)
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    ALERT_ON_STARS_LEQ: int = 2  # Disparar alerta en <= 2 estrellas

    # Notificaciones Email SMTP (Opcional)
    EMAIL_NOTIFICATIONS_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_RECIPIENT: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def is_groq_configured(self) -> bool:
        """Verifica si la API de Groq está lista con clave válida."""
        return bool(self.GROQ_API_KEY and self.GROQ_API_KEY.strip())

    @property
    def is_openai_configured(self) -> bool:
        """Verifica si la API de OpenAI está lista con clave válida."""
        return bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY.strip())

    @property
    def is_telegram_configured(self) -> bool:
        """Verifica si Telegram cuenta con token y chatId."""
        return bool(
            self.TELEGRAM_BOT_TOKEN
            and self.TELEGRAM_BOT_TOKEN.strip()
            and self.TELEGRAM_CHAT_ID
            and self.TELEGRAM_CHAT_ID.strip()
        )

    @property
    def is_email_configured(self) -> bool:
        """Verifica si el servicio de email cuenta con los parámetros mínimos."""
        return bool(
            self.EMAIL_NOTIFICATIONS_ENABLED
            and self.SMTP_USER
            and self.SMTP_PASSWORD
            and self.EMAIL_RECIPIENT
        )


@lru_cache()
def get_settings() -> Settings:
    """Retorna una instancia única cacheada de las configuraciones."""
    return Settings()

