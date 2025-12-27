# app/services/chatbot_service.py
import json
import re
import unicodedata
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class ChatbotService:
    _data = None
    _dataset_cache = None  # (patrones_norm, respuestas, tags)
    _intents_path = Path(__file__).parent / "chatbot" / "intents.json"

    # --- reglas / config ---
    STOPWORDS_ES = {
        "de", "la", "el", "los", "las", "un", "una", "unos", "unas",
        "y", "o", "u", "a", "en", "con", "por", "para", "del", "al",
        "que", "como", "donde", "cuando", "cuanto", "cuanta", "cuantos", "cuantas",
        "me", "mi", "mis", "tu", "tus", "su", "sus", "nos", "les",
        "yo", "vos", "usted", "ustedes", "ellos", "ellas",
        "es", "son", "ser", "estar", "esta", "estoy", "estan",
        "quiero", "quisiera", "puedo", "podria", "porfavor", "por favor"
    }

    AFIRMACIONES = {
        "si", "sí", "claro", "ok", "okay", "dale", "de una", "perfecto",
        "aja", "ajá", "me parece", "hagamoslo", "vamos", "quiero"
    }
    NEGACIONES = {
        "no", "nop", "no gracias", "por ahora no", "despues", "después",
        "luego", "ahorita no", "tal vez luego"
    }

    PASOS_AGENDAR = (
        "Para agendar: 1) Crea tu cuenta en nuestra web. "
        "2) Ve al apartado de 'Citas' y presiona el botón '+'. "
        "3) Indica 3 horas en las que tengas disponibilidad. "
        "La terapeuta te asignará el mejor horario y te notificará por correo o WhatsApp."
    )

    FALLBACK = (
        "Disculpa, no tengo esa información específica en mi memoria por el momento. "
        "Para esa consulta, por favor contacta directamente al consultorio al: +506 8748 4854"
    )

    # -----------------------------
    # Normalización
    # -----------------------------
    @staticmethod
    def normalizar(texto: str) -> str:
        texto = (texto or "").lower().strip()
        texto = "".join(
            c for c in unicodedata.normalize("NFD", texto)
            if unicodedata.category(c) != "Mn"
        )
        texto = re.sub(r"[^a-z0-9\s]", " ", texto)
        texto = re.sub(r"\s+", " ", texto).strip()
        return texto

    # -----------------------------
    # Cargar intents
    # -----------------------------
    @classmethod
    def _load_data(cls) -> dict:
        if cls._data is None:
            try:
                with open(cls._intents_path, "r", encoding="utf-8") as f:
                    cls._data = json.load(f)
            except FileNotFoundError:
                cls._data = {"intents": []}
            except json.JSONDecodeError:
                cls._data = {"intents": []}

        return cls._data

    @classmethod
    def _build_dataset(cls) -> Tuple[list, list, list]:
        """
        Construye y cachea:
        - patrones_norm: lista[str]
        - respuestas: lista[str]
        - tags: lista[str]
        """
        data = cls._load_data()
        intents = data.get("intents", [])

        patrones_norm, respuestas, tags = [], [], []

        for intent in intents:
            tag = str(intent.get("tag", "")).strip()
            resp_list = intent.get("responses", [])
            if not resp_list:
                continue
            resp = str(resp_list[0])

            for pattern in intent.get("patterns", []):
                p = cls.normalizar(str(pattern))
                if p:
                    patrones_norm.append(p)
                    respuestas.append(resp)
                    tags.append(tag)

        cls._dataset_cache = (patrones_norm, respuestas, tags)
        return patrones_norm, respuestas, tags

    @classmethod
    def _get_dataset(cls) -> Tuple[list, list, list]:
        # si no está cacheado o quedó vacío, construir
        if cls._dataset_cache is None:
            return cls._build_dataset()

        patrones_norm, respuestas, tags = cls._dataset_cache
        if not patrones_norm:
            return cls._build_dataset()

        return patrones_norm, respuestas, tags

    # -----------------------------
    # Core: similitud
    # -----------------------------
    @classmethod
    def _best_match(
        cls, message: str, threshold: float = 0.25
    ) -> Tuple[str, float, Optional[str]]:
        """
        Retorna (respuesta, score, tag)
        """
        msg = cls.normalizar(message)

        if not msg:
            return ("Decime tu consulta para poder ayudarte 🙂", 1.0, "empty")

        patrones_norm, respuestas, tags = cls._get_dataset()
        if not patrones_norm:
            return ("El chatbot no tiene conocimiento cargado (intents.json vacío).", 0.0, None)

        try:
            vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                stop_words=sorted(cls.STOPWORDS_ES)
            )
            tfidf = vectorizer.fit_transform(patrones_norm + [msg])
            sims = cosine_similarity(tfidf[-1], tfidf[:-1])

            idx = sims.argsort()[0][-1]
            score = float(sims[0][idx])

            if score < threshold:
                return (cls.FALLBACK, score, None)

            return (respuestas[idx], score, tags[idx])

        except ValueError:
            return (cls.FALLBACK, 0.0, None)

    # -----------------------------
    # API: respuesta + contexto
    # -----------------------------
    @classmethod
    def reply(
        cls,
        message: str,
        context: Optional[str] = None,
        threshold: float = 0.25
    ) -> Dict[str, Any]:
        """
        Entrada:
          - message: texto usuario
          - context: string opcional (guardado por frontend)
        Salida:
          - response: texto del bot
          - next_context: contexto nuevo
          - tag, score: opcional útil para debug
        """
        msg_norm = cls.normalizar(message)
        ctx = context or None

        # 1) Si venimos de pregunta_agendar, manejar sí/no sin TF-IDF
        if ctx == "pregunta_agendar":
            if msg_norm in cls.AFIRMACIONES:
                return {
                    "response": f"¡Perfecto! {cls.PASOS_AGENDAR}",
                    "next_context": None,
                    "tag": "agendar_cita",
                    "score": 1.0
                }
            if msg_norm in cls.NEGACIONES:
                return {
                    "response": "Entendido 🙂 ¿Te ayudo con horario, precio, ubicación o contacto?",
                    "next_context": None,
                    "tag": "negacion",
                    "score": 1.0
                }
            # si no fue sí/no, continuamos normal (sin perder contexto)
            # pero normalmente es mejor limpiar el contexto para evitar loops:
            ctx = None

        # 2) Normal TF-IDF
        respuesta, score, tag = cls._best_match(message, threshold=threshold)

        # 3) Si el bot acaba de preguntar por agendar, setear contexto
        next_ctx = None
        if "te gustaria agendar" in cls.normalizar(respuesta) or "te gustaría agendar" in respuesta.lower():
            next_ctx = "pregunta_agendar"

        return {
            "response": respuesta,
            "next_context": next_ctx,
            "tag": tag,
            "score": score
        }

    # Si querés mantener el método viejo:
    @classmethod
    def get_best_response(cls, message: str, threshold: float = 0.25) -> str:
        return cls.reply(message=message, context=None, threshold=threshold)["response"]
