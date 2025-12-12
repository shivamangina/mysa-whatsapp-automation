import logging

from flask import Blueprint, request, jsonify, current_app

from .utils.whatsapp_utils import (
    process_whatsapp_message,
    is_valid_whatsapp_message,
)

webhook_blueprint = Blueprint("webhook", __name__)


@webhook_blueprint.route("/webhook", methods=["GET", "POST"])
def webhook():
    # 1. Verification (GET)
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == current_app.config["VERIFY_TOKEN"]:
            logging.info("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            logging.info("VERIFICATION_FAILED")
            return "Verification token mismatch", 403

    # 2. Incoming Messages (POST)
    if request.method == "POST":
        data = request.get_json()
        logging.info(f"🔥 Incoming Webhook Data: {data}")

        # Process the message if valid
        if is_valid_whatsapp_message(data):
            process_whatsapp_message(data)

        # MUST return 200 to acknowledge receipt
        return "EVENT_RECEIVED", 200


