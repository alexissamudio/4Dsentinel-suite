"""Mini-app de ejemplo (codebase real contra el que se evalua el plan)."""

import sqlite3

DB_PATH = "app.db"


def connect_db():
    return sqlite3.connect(DB_PATH)


def run_query(sql, params=()):
    conn = connect_db()
    try:
        cur = conn.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.close()


def get_user(user_id):
    return run_query("SELECT * FROM users WHERE id = ?", (user_id,))
