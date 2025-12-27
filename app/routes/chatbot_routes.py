# app/routes/chatbot_routes.py
from flask import Blueprint, request, jsonify
from ..services.chatbot_service import ChatbotService

bp = Blueprint("chatbot", __name__)

@bp.post("/message")
def chatbot_message():
    payload = request.get_json(force=True) or {}
    message = payload.get("message", "")
    context = payload.get("context")  # <-- nuevo

    result = ChatbotService.reply(message=message, context=context)

    return jsonify({
        "message": message,
        "response": result["response"],
        "context": result["next_context"],  # <-- devolvemos el siguiente contexto
        # opcional para debug (podés quitarlo)
        "tag": result.get("tag"),
        "score": result.get("score")
    }), 200
