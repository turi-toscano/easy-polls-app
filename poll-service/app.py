import logging
import os
import secrets
import string
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.environ.get("MONGODB_DB", "easypolls")
ID_LENGTH = int(os.environ.get("POLL_ID_LENGTH", "7"))
MAX_OPTIONS = int(os.environ.get("POLL_MAX_OPTIONS", "10"))
MAX_QUESTION_LEN = 280
MAX_OPTION_LEN = 120

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("poll-service")

_ALPHABET = string.ascii_lowercase + string.digits

app = Flask(__name__)

_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
polls = _client[MONGODB_DB]["polls"]

def _new_id() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(ID_LENGTH))

def _serialize(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "question": doc["question"],
        "options": [
            {"id": o["id"], "text": o["text"], "votes": o["votes"]}
            for o in doc["options"]
        ],
    }

@app.post("/api/polls")
def create_poll():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    raw_options = data.get("options") or []

    if not question or len(question) > MAX_QUESTION_LEN:
        return jsonify(error="La domanda e' obbligatoria (max 280 caratteri)."), 400

    options = []
    for raw in raw_options:
        text = raw.strip() if isinstance(raw, str) else ""
        if text:
            options.append(text[:MAX_OPTION_LEN])
    if not (2 <= len(options) <= MAX_OPTIONS):
        return jsonify(error=f"Servono da 2 a {MAX_OPTIONS} opzioni."), 400

    doc = {
        "question": question,
        "options": [
            {"id": i, "text": t, "votes": 0} for i, t in enumerate(options)
        ],
        "createdAt": datetime.now(timezone.utc),
    }

    for _ in range(5):
        doc["_id"] = _new_id()
        try:
            polls.insert_one(doc)
            log.info("Creato sondaggio %s con %d opzioni", doc["_id"], len(options))
            return jsonify(_serialize(doc)), 201
        except DuplicateKeyError:
            continue
    return jsonify(error="Impossibile generare un id univoco, riprova."), 503

@app.post("/api/polls/<poll_id>/vote")
def vote(poll_id):
    data = request.get_json(silent=True) or {}
    option_id = data.get("option_id")
    if not isinstance(option_id, int) or isinstance(option_id, bool):
        return jsonify(error="option_id deve essere un intero."), 400

    result = polls.update_one(
        {"_id": poll_id, "options.id": option_id},
        {"$inc": {"options.$.votes": 1}},
    )
    if result.matched_count == 0:
        return jsonify(error="Sondaggio o opzione non trovati."), 404
    return "", 204

@app.get("/healthz")
def healthz():
    """Liveness: il processo risponde. Non tocca il database di proposito."""
    return jsonify(status="ok"), 200

@app.get("/readyz")
def readyz():
    """Readiness: pronto solo se MongoDB e' raggiungibile."""
    try:
        _client.admin.command("ping")
        return jsonify(status="ready"), 200
    except PyMongoError:
        return jsonify(status="not-ready"), 503