"""Endpoint de login (codebase real contra el que se evalua la tarea)."""

from flask import Flask, request, jsonify
from werkzeug.security import check_password_hash

from db import find_user_by_name

app = Flask(__name__)


@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    client_ip = request.remote_addr

    user = find_user_by_name(username)
    if user is None or not check_password_hash(user["pw_hash"], password):
        return jsonify({"error": "invalid credentials"}), 401

    return jsonify({"ok": True, "user": username}), 200
