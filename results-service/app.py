import logging
import os

from flask import Flask, jsonify
from pymongo import MongoClient
from pymongo.errors import PyMongoError

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.environ.get("MONGODB_DB", "easypolls")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("results-service")

app = Flask(__name__)

_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
polls = _client[MONGODB_DB]["polls"]


@app.get("/api/results/<poll_id>")
def results(poll_id):
    doc = polls.find_one({"_id": poll_id})
    if not doc:
        return jsonify(error="Sondaggio non trovato."), 404

    options = [
        {"id": o["id"], "text": o["text"], "votes": o["votes"]}
        for o in doc["options"]
    ]
    total = sum(o["votes"] for o in options)

    resp = jsonify(
        id=doc["_id"],
        question=doc["question"],
        options=options,
        totalVotes=total,
    )
    # I risultati cambiano in continuazione: mai servirli da cache.
    resp.headers["Cache-Control"] = "no-store"
    return resp, 200


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