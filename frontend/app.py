"""
Dashboard en Streamlit para el Micro-SaaS de Reputación Local y Reseñas.
Permite visualizar métricas, supervisar alertas críticas y gestionar respuestas generadas con IA.
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import os
import sys

# Configuración de página
st.set_page_config(
    page_title="RepuShield AI - Monitor de Reputación Local",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constantes de conexión
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


# ============================================================================
# FUNCIONES AUXILIARES DE COMUNICACIÓN CON FASTAPI
# ============================================================================

def check_api_health():
    """Comprueba si el servidor FastAPI está en línea."""
    try:
        r = requests.get(f"{API_BASE_URL}/health", timeout=3.0)
        if r.status_code == 200:
            return True, r.json()
        return False, None
    except Exception:
        return False, None


def fetch_stats():
    """Recupera estadísticas agregadas desde la API."""
    try:
        r = requests.get(f"{API_BASE_URL}/api/v1/stats", timeout=5.0)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None


def fetch_reviews(sentiment=None, rating=None, status=None, search=None):
    """Consulta la lista de reseñas con filtros."""
    params = {}
    if sentiment and sentiment != "Todos":
        params["sentiment"] = sentiment
    if rating and rating != "Todas":
        params["rating"] = int(rating)
    if status and status != "Todos":
        params["response_status"] = status
    if search:
        params["search"] = search

    try:
        r = requests.get(f"{API_BASE_URL}/api/v1/reviews", params=params, timeout=6.0)
        if r.status_code == 200:
            return r.json()
        return []
    except Exception:
        return []


def trigger_scan(count=5, force_negative=False):
    """Dispara un escaneo / simulación de nuevas reseñas."""
    try:
        payload = {"count": count, "force_negative": force_negative}
        r = requests.post(f"{API_BASE_URL}/api/v1/reviews/scan", json=payload, timeout=20.0)
        if r.status_code == 200:
            return True, r.json()
        return False, f"Error {r.status_code}: {r.text}"
    except Exception as e:
        return False, str(e)


def send_manual_webhook(author, rating, text, business_name=None):
    """Envía una reseña manual simulando un webhook entrante."""
    payload = {
        "author_name": author,
        "rating": rating,
        "text": text,
        "business_name": business_name or "Restaurante Parrilla Los Olivos",
        "source": "Webhook Manual"
    }
    try:
        r = requests.post(f"{API_BASE_URL}/api/v1/reviews/webhook", json=payload, timeout=15.0)
        if r.status_code == 201:
            return True, r.json()
        return False, f"Error: {r.text}"
    except Exception as e:
        return False, str(e)


def update_response(review_id, final_response, response_status="Aprobada"):
    """Actualiza y aprueba la respuesta para una reseña."""
    payload = {
        "final_response": final_response,
        "response_status": response_status
    }
    try:
        r = requests.post(f"{API_BASE_URL}/api/v1/reviews/{review_id}/approve", json=payload, timeout=8.0)
        if r.status_code == 200:
            return True, r.json()
        return False, f"Error: {r.text}"
    except Exception as e:
        return False, str(e)


def regenerate_ai(review_id):
    """Solicita a la IA volver a generar una respuesta diplomática."""
    try:
        r = requests.post(f"{API_BASE_URL}/api/v1/reviews/{review_id}/regenerate-ai", timeout=15.0)
        if r.status_code == 200:
            return True, r.json()
        return False, f"Error: {r.text}"
    except Exception as e:
        return False, str(e)


def test_telegram():
    """Envía mensaje de prueba al bot de Telegram."""
    try:
        r = requests.post(f"{API_BASE_URL}/api/v1/notifications/test-telegram", timeout=8.0)
        if r.status_code == 200:
            return r.json()
        return {"success": False, "message": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ============================================================================
# ESTILOS CSS PERSONALIZADOS
# ============================================================================

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 24px;
        border-radius: 12px;
        color: white;
        margin-bottom: 24px;
        border: 1px solid #334155;
    }
    .metric-card {
        background-color: #f8fafc;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .critical-badge {
        background-color: #fee2e2;
        color: #991b1b;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        display: inline-block;
    }
    .neutral-badge {
        background-color: #fef3c7;
        color: #92400e;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        display: inline-block;
    }
    .positive-badge {
        background-color: #dcfce7;
        color: #166534;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        display: inline-block;
    }
    .response-box {
        background-color: #f0fdf4;
        border-left: 4px solid #22c55e;
        padding: 14px;
        border-radius: 6px;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# VERIFICACIÓN DE ESTADO DEL BACKEND
# ============================================================================

is_online, health_info = check_api_health()

# Encabezado Principal
st.markdown("""
<div class="main-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="margin: 0; font-size: 28px; font-weight: 700;">🛡️ RepuShield AI — Monitor de Reputación Local</h1>
            <p style="margin: 6px 0 0 0; color: #94a3b8; font-size: 14px;">
                Detección inmediata de reseñas negativas, alertas prioritarias vía Telegram y redacción de respuestas diplomáticas con IA.
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

if not is_online:
    st.error(
        f"⚠️ **El servidor backend FastAPI no responde en `{API_BASE_URL}`**.\n\n"
        "Asegúrate de iniciarlo en una terminal con:\n"
        "```bash\n"
        "python -m uvicorn app.main:app --reload --port 8000\n"
        "```"
    )
    st.stop()


# ============================================================================
# BARRA LATERAL: CONTROL DE INGESTA Y CONFIGURACIÓN
# ============================================================================

with st.sidebar:
    st.image("https://images.unsplash.com/photo-1552664730-d307ca884978?w=500&auto=format&fit=crop&q=60", use_container_width=True)
    st.title("⚡ Panel de Control")

    st.subheader("📥 Ingesta de Reseñas")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 Escaneo Mixto", help="Simula 5 reseñas normales con distribución estándar"):
            with st.spinner("Rastreando reseñas..."):
                ok, res = trigger_scan(count=5, force_negative=False)
                if ok:
                    st.success(f"¡Listo! {res.get('new_imported')} nuevas reseñas.")
                    st.rerun()
                else:
                    st.error(f"Error: {res}")

    with col_btn2:
        if st.button("🚨 Alerta Crítica", help="Genera reseñas de 1 o 2 estrellas para comprobar alertas inmediatas"):
            with st.spinner("Simulando queja de cliente..."):
                ok, res = trigger_scan(count=2, force_negative=True)
                if ok:
                    st.warning(f"¡Alerta disparada! {res.get('critical_alerts_triggered')} alertas.")
                    st.rerun()
                else:
                    st.error(f"Error: {res}")

    st.divider()

    # Formulario para inyectar una reseña manual
    with st.expander("✍️ Probar Reseña Manual (Webhook)", expanded=False):
        with st.form("manual_review_form"):
            man_author = st.text_input("Nombre del Cliente", value="Valeria Domínguez")
            man_rating = st.slider("Estrellas (Rating)", min_value=1, max_value=5, value=1)
            man_text = st.text_area(
                "Texto de la Reseña",
                value="El servicio fue pésimo. Tardaron 45 minutos en traer un plato frío y el camarero nos contestó con muy mala educación."
            )
            submitted = st.form_submit_button("🚀 Enviar al Webhook")
            if submitted:
                with st.spinner("Procesando con IA y verificando alertas..."):
                    ok, resp = send_manual_webhook(man_author, man_rating, man_text)
                    if ok:
                        st.success("¡Reseña procesada e indexada!")
                        st.rerun()
                    else:
                        st.error(f"Error: {resp}")

    st.divider()

    st.subheader("🔌 Estado de Integraciones")
    if health_info:
        g_ready = health_info.get("groq_ready")
        o_ready = health_info.get("openai_ready")
        t_ready = health_info.get("telegram_ready")

        st.write(f"🧠 **Groq AI:** {'✅ Configurado' if g_ready else '⚠️ Modo Heurístico'}")
        st.write(f"🤖 **OpenAI:** {'✅ Configurado' if o_ready else '⚪ No activo'}")
        st.write(f"📲 **Telegram Bot:** {'✅ Conectado' if t_ready else '⚠️ No configurado'}")

    if st.button("🔔 Probar Bot de Telegram"):
        with st.spinner("Enviando mensaje de prueba..."):
            res = test_telegram()
            if res.get("success"):
                st.success("¡Mensaje recibido en Telegram!")
            else:
                st.error(f"Fallo: {res.get('message')}")


# ============================================================================
# TARJETAS DE MÉTRICAS GLOBALES
# ============================================================================

stats = fetch_stats()
if stats:
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric(
            label="Total Reseñas",
            value=stats.get("total_reviews", 0)
        )
    with col2:
        avg = stats.get("average_rating", 0.0)
        stars_str = "⭐" * int(round(avg)) if avg > 0 else "—"
        st.metric(
            label="Puntuación Media",
            value=f"{avg:.2f} / 5.0",
            delta=f"{stars_str}"
        )
    with col3:
        neg = stats.get("negative_reviews_count", 0)
        st.metric(
            label="Reseñas Críticas (1-2★)",
            value=neg,
            delta="Requieren atención",
            delta_color="inverse" if neg > 0 else "normal"
        )
    with col4:
        pending = stats.get("pending_responses_count", 0)
        st.metric(
            label="Respuestas Pendientes",
            value=pending,
            delta="Por aprobar" if pending > 0 else "Al día",
            delta_color="inverse" if pending > 0 else "normal"
        )
    with col5:
        alerts = stats.get("alerts_triggered_count", 0)
        st.metric(
            label="Alertas Disparadas",
            value=alerts,
            delta="Telegram / Email"
        )

st.markdown("<br>", unsafe_allow_html=True)


# ============================================================================
# PESTAÑAS PRINCIPALES DE GESTIÓN
# ============================================================================

tab_critical, tab_all, tab_analytics, tab_config = st.tabs([
    "🚨 Bandeja Crítica (Alertas 1-2★)",
    "📋 Historial de Reseñas",
    "📊 Analítica de Reputación",
    "⚙️ Guía de Integración"
])


# ----------------------------------------------------------------------------
# PESTAÑA 1: BANDEJA DE RESEÑAS CRÍTICAS (1 Y 2 ESTRELLAS)
# ----------------------------------------------------------------------------
with tab_critical:
    st.subheader("🚨 Bandeja de Intervención Rápida")
    st.caption("Reseñas con 1 o 2 estrellas que dañan la reputación de tu negocio. Revisa la propuesta de la IA y responde de inmediato.")

    critical_reviews = fetch_reviews(rating=None)
    # Filtrar localmente las de 1 y 2 estrellas
    critical_reviews = [r for r in critical_reviews if r["rating"] <= 2]

    if not critical_reviews:
        st.info("🎉 ¡Excelente! No tienes reseñas críticas pendientes de atención.")
    else:
        for rev in critical_reviews:
            r_id = rev["id"]
            stars = "⭐" * rev["rating"] + "☆" * (5 - rev["rating"])
            badge_class = "critical-badge" if rev["rating"] <= 2 else "neutral-badge"

            with st.container():
                st.markdown(f"""
                <div style="border: 1px solid #fca5a5; background-color: #fffaf0; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <div>
                            <span style="font-size: 16px; font-weight: bold; color: #1e293b;">{rev['author_name']}</span>
                            <span style="color: #64748b; font-size: 13px; margin-left: 8px;">• {rev['published_at'][:10]} ({rev['source']})</span>
                        </div>
                        <div>
                            <span style="font-size: 16px; color: #dc2626; margin-right: 10px;">{stars} ({rev['rating']}/5)</span>
                            <span class="{badge_class}">Urgencia: {rev['urgency_level'].upper()}</span>
                        </div>
                    </div>
                    <div style="font-style: italic; color: #334155; margin-bottom: 12px; font-size: 15px;">
                        "{rev['text']}"
                    </div>
                    <div style="font-size: 12px; color: #475569; margin-bottom: 6px;">
                        <b>Problemas detectados:</b> {rev.get('key_issues') or 'Inconformidad general'}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Editor de la respuesta sugerida
                col_txt, col_actions = st.columns([4, 1])
                with col_txt:
                    current_text = rev.get("final_response") or rev.get("suggested_response") or ""
                    edited_response = st.text_area(
                        label=f"Propuesta diplomática de respuesta (IA) - Reseña #{r_id}",
                        value=current_text,
                        height=130,
                        key=f"text_area_{r_id}"
                    )

                with col_actions:
                    st.write("**Acciones:**")
                    st.caption(f"Estado: **{rev['response_status']}**")

                    if st.button("✅ Aprobar y Publicar", key=f"btn_approve_{r_id}", use_container_width=True):
                        ok, res = update_response(r_id, edited_response, response_status="Publicada")
                        if ok:
                            st.success("¡Respuesta aprobada y publicada!")
                            st.rerun()
                        else:
                            st.error(res)

                    if st.button("🔄 Regenerar con IA", key=f"btn_regen_{r_id}", use_container_width=True):
                        with st.spinner("Regenerando con IA..."):
                            ok, res = regenerate_ai(r_id)
                            if ok:
                                st.success("Nueva propuesta generada.")
                                st.rerun()
                            else:
                                st.error(res)

                st.divider()


# ----------------------------------------------------------------------------
# PESTAÑA 2: HISTORIAL COMPLETO DE RESEÑAS
# ----------------------------------------------------------------------------
with tab_all:
    st.subheader("📋 Historial y Registro Completo")

    # Filtros interactivos
    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 2, 2, 4])
    with f_col1:
        filter_sentiment = st.selectbox("Sentimiento", ["Todos", "Positiva", "Neutra", "Negativa"])
    with f_col2:
        filter_rating = st.selectbox("Estrellas", ["Todas", "5", "4", "3", "2", "1"])
    with f_col3:
        filter_status = st.selectbox("Estado Respuesta", ["Todos", "Pendiente", "Aprobada", "Publicada"])
    with f_col4:
        filter_search = st.text_input("🔍 Buscar por texto o cliente", "")

    all_reviews = fetch_reviews(
        sentiment=filter_sentiment,
        rating=filter_rating,
        status=filter_status,
        search=filter_search
    )

    if not all_reviews:
        st.info("No se encontraron reseñas con los filtros seleccionados.")
    else:
        st.caption(f"Mostrando **{len(all_reviews)}** reseñas registradas.")

        for r in all_reviews:
            stars = "⭐" * r["rating"]
            sent = r["sentiment"]
            badge_class = "positive-badge" if sent == "Positiva" else ("critical-badge" if sent == "Negativa" else "neutral-badge")

            with st.expander(f"{stars} — {r['author_name']} ({r['published_at'][:10]}) — {sent}"):
                c1, c2 = st.columns([3, 2])
                with c1:
                    st.markdown(f"**Reseña original:**")
                    st.write(f"*{r['text']}*")
                    st.caption(f"Origen: `{r['source']}` | Puntuación Sentimiento: `{r['sentiment_score']}`")

                with c2:
                    st.markdown(f"**Respuesta al cliente:** ({r['response_status']})")
                    current_res = r.get("final_response") or r.get("suggested_response")
                    if current_res:
                        st.info(current_res)
                    else:
                        st.caption("Sin respuesta aún.")


# ----------------------------------------------------------------------------
# PESTAÑA 3: ANALÍTICA DE REPUTACIÓN
# ----------------------------------------------------------------------------
with tab_analytics:
    st.subheader("📊 Métricas de Reputación y Sentimiento")

    if stats and stats.get("total_reviews", 0) > 0:
        c_chart1, c_chart2 = st.columns(2)

        with c_chart1:
            st.markdown("#### Distribución de Sentimiento")
            sentiment_df = pd.DataFrame({
                "Sentimiento": ["Positivas", "Neutras", "Negativas"],
                "Total": [
                    stats["positive_reviews_count"],
                    stats["neutral_reviews_count"],
                    stats["negative_reviews_count"]
                ]
            })
            st.bar_chart(sentiment_df.set_index("Sentimiento"))

        with c_chart2:
            st.markdown("#### Calificaciones por Estrellas (1★ a 5★)")
            dist = stats.get("rating_distribution", {})
            dist_df = pd.DataFrame({
                "Estrellas": ["1★", "2★", "3★", "4★", "5★"],
                "Cantidad": [
                    dist.get("1", 0),
                    dist.get("2", 0),
                    dist.get("3", 0),
                    dist.get("4", 0),
                    dist.get("5", 0)
                ]
            })
            st.bar_chart(dist_df.set_index("Estrellas"))

        # Tabla resumen
        st.markdown("#### Resumen Operativo")
        summary_table = pd.DataFrame([
            {"Métrica": "Volumen Total de Reseñas", "Valor": stats["total_reviews"]},
            {"Métrica": "Puntuación Media", "Valor": f"{stats['average_rating']} / 5.0"},
            {"Métrica": "Tasa de Reseñas Negativas", "Valor": f"{(stats['negative_reviews_count'] / stats['total_reviews'] * 100):.1f}%"},
            {"Métrica": "Respuestas Pendientes de Aprobación", "Valor": stats["pending_responses_count"]},
            {"Métrica": "Alertas Telegram / Email Enviadas", "Valor": stats["alerts_triggered_count"]},
        ])
        st.dataframe(summary_table, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay suficientes datos para generar analíticas. Realiza un escaneo de prueba en la barra lateral.")


# ----------------------------------------------------------------------------
# PESTAÑA 4: GUÍA DE CONFIGURACIÓN E INTEGRACIÓN
# ----------------------------------------------------------------------------
with tab_config:
    st.subheader("⚙️ Configuración y Webhooks de Integración")

    st.markdown("""
    ### 1. Conexión de Webhook en Tiempo Real
    Puedes conectar este sistema con cualquier herramienta de automatización como **Make**, **Zapier**, o un bot de scraping propio apuntando a:

    **URL del Webhook:**
    """)
    st.code(f"POST {API_BASE_URL}/api/v1/reviews/webhook", language="http")

    st.markdown("""
    **Payload JSON esperado:**
    ```json
    {
      "author_name": "Nombre del Cliente",
      "rating": 1,
      "text": "La comida llegó fría y la atención fue muy deficiente.",
      "business_name": "Nombre de Tu Negocio",
      "source": "Google Places",
      "published_at": "2026-10-28T12:00:00"
    }
    ```

    ---

    ### 2. Configurar Bot de Telegram para Alertas
    1. Abre Telegram y busca **@BotFather**.
    2. Envía el comando `/newbot` y sigue las instrucciones para obtener tu **Bot Token**.
    3. Busca **@userinfobot** en Telegram para conocer tu **Chat ID** (o el ID del grupo de gerencia).
    4. Añade ambos valores en tu archivo `.env`:
    ```ini
    TELEGRAM_BOT_TOKEN="tu_token_aqui"
    TELEGRAM_CHAT_ID="tu_chat_id_aqui"
    ```

    ---

    ### 3. Configurar Motor de IA (Groq u OpenAI)
    - **Groq (Recomendado por velocidad y coste):** Obtén tu clave en [console.groq.com](https://console.groq.com/) y colócala en `GROQ_API_KEY`.
    - **OpenAI:** Obtén tu clave en [platform.openai.com](https://platform.openai.com/) y colócala en `OPENAI_API_KEY`.
    """)

