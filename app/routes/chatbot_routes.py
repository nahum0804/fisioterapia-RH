# app/routes/chatbot_routes.py
from flask import Blueprint, request, jsonify
from ..services.chatbot_service import ChatbotService

bp = Blueprint("chatbot", __name__)

@bp.post("/message")
def chatbot_message():
    payload = request.get_json(force=True) or {}
    message = payload.get("message", "")

    response = ChatbotService.get_best_response(message)
    return jsonify({"message": message, "response": response}), 200
