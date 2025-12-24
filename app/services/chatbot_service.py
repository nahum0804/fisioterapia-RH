# app/services/chatbot_service.py
import json
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class ChatbotService:
    _data = None
    _intents_path = Path(__file__).parent / "chatbot" / "intents.json"

    @classmethod
    def _load_data(cls) -> dict:
        if cls._data is None:
            try:
                with open(cls._intents_path, "r", encoding="utf-8") as f:
                    cls._data = json.load(f)
            except FileNotFoundError:
                cls._data = {"intents": []}
        return cls._data

    @classmethod
    def get_best_response(cls, message: str, threshold: float = 0.25) -> str:
        data = cls._load_data()

        if not message or not message.strip():
            return "Decime tu consulta para poder ayudarte 🙂"

        intents = data.get("intents", [])
        if not intents:
            return "El chatbot no tiene conocimiento cargado (intents.json vacío)."

        # 1) Preparar datos
        all_patterns = []
        mapped_responses = []

        for intent in intents:
            patterns = intent.get("patterns", [])
            responses = intent.get("responses", [])
            if not patterns or not responses:
                continue

            for p in patterns:
                all_patterns.append(str(p).lower())
                mapped_responses.append(str(responses[0]))

        if not all_patterns:
            return "No hay patrones configurados en intents.json."

        # 2) Agregar mensaje del usuario
        all_patterns.append(message.lower())

        # 3) Vectorización + similitud
        try:
            vectorizer = TfidfVectorizer()
            tfidf = vectorizer.fit_transform(all_patterns)
            sims = cosine_similarity(tfidf[-1], tfidf[:-1])

            idx = sims.argsort()[0][-1]
            score = float(sims[0][idx])
        except ValueError:
            score = 0.0
            idx = None

        # 4) Fallback por baja confianza
        if idx is None or score < threshold:
            return (
                "Disculpa, no tengo esa información específica en mi memoria por el momento. "
                "Para esa consulta, por favor contacta directamente al consultorio al: +506 8748 4854"
            )

        return mapped_responses[idx]
