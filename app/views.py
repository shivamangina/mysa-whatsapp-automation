import logging

import threading

from flask import Blueprint, request, current_app

from .utils.whatsapp_utils import (
    process_whatsapp_message,
    is_valid_whatsapp_message,
)

webhook_blueprint = Blueprint("webhook", __name__)


def _process_async(data):
    """Optional: offload heavy processing so we ACK quickly."""
    try:
        if is_valid_whatsapp_message(data):
            process_whatsapp_message(data)
        else:
            print("Webhook: not a valid whatsapp message", flush=True)
    except Exception as e:
        # log exceptions but don't crash the main request thread
        logging.exception("Error processing whatsapp message:")
        print(f"Error processing: {e}", flush=True)


@webhook_blueprint.route("/webhook", methods=["GET", "POST"])
@webhook_blueprint.route("/webhook/", methods=["GET", "POST"])
def webhook():
    # 1) Verification (GET)
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == current_app.config.get("VERIFY_TOKEN"):
            print("WEBHOOK_VERIFIED", flush=True)
            return challenge, 200
        else:
            print("VERIFICATION_FAILED", flush=True)
            return "Verification token mismatch", 403

    # 2) Incoming Messages (POST)
    if request.method == "POST":
        # Log headers + raw body (useful if JSON parsing fails)
        try:
            print("---- WEBHOOK CALL RECEIVED ----", flush=True)
            print("Headers:", dict(request.headers), flush=True)
            raw_body = request.get_data(as_text=True)
            print("Raw body:", raw_body, flush=True)
        except Exception as e:
            print(f"Error reading request data: {e}", flush=True)

        # Use silent=True so it returns None instead of raising on malformed content
        data = request.get_json(silent=True)
        print("Parsed JSON:", data, flush=True)

        # Acknowledge quickly (must return 200)
        # Return before heavy processing to avoid timeouts (Meta expects a fast 200)
        response = ("EVENT_RECEIVED", 200)

        # Process in background thread to avoid blocking and to ensure we already returned 200
        # If you prefer synchronous processing, remove threading and call _process_async(data) directly.
        try:
            t = threading.Thread(target=_process_async, args=(data,))
            t.daemon = True
            t.start()
        except Exception as e:
            # If threading fails, still attempt to process synchronously but keep it guarded
            logging.exception("Background thread failed, processing inline.")
            _process_async(data)

        return response
