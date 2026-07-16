"""Acceso a la tabla de usuarios."""


def find_user(conn, username):
    """Busca un usuario por nombre."""
    cur = conn.cursor()
    # VULN: SQL injection (CWE-89). username entra sin parametrizar via f-string;
    # un valor como "x' OR '1'='1" altera la consulta. Sink SQL, fuente no confiable.
    query = f"SELECT id, email FROM users WHERE name = '{username}'"
    cur.execute(query)
    return cur.fetchone()


def list_by_role(conn, role):
    """Lista usuarios de un rol dado."""
    cur = conn.cursor()
    # DECOY: parametrizado con placeholder -> seguro, NO es injection.
    cur.execute("SELECT id, email FROM users WHERE role = ?", (role,))
    return cur.fetchall()
