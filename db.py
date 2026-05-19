import os
import sqlite3
import hashlib
import json

DB_NAME = 'ezetec_clientes.db'
DATABASE_URL = os.environ.get('DATABASE_URL')
IN_VERCEL = os.environ.get('VERCEL') == '1'


class IntegrityError(Exception):
    pass


def _db_path():
    if IN_VERCEL:
        return os.path.join('/tmp', DB_NAME)
    return DB_NAME


def _use_pg():
    return bool(DATABASE_URL)


def _get_conn():
    if _use_pg():
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        return conn, RealDictCursor
    else:
        conn = sqlite3.connect(_db_path())
        conn.row_factory = sqlite3.Row
        return conn, None


def _fix(sql):
    return sql.replace('?', '%s') if _use_pg() else sql


def query(sql, params=None):
    conn, cf = _get_conn()
    try:
        cur = conn.cursor(cursor_factory=cf) if cf else conn.cursor()
        cur.execute(_fix(sql), params or [])
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def execute(sql, params=None):
    conn, cf = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(_fix(sql), params or [])
        conn.commit()
        auto_backup()
    except Exception as e:
        conn.rollback()
        if _use_pg():
            from psycopg2.errors import UniqueViolation
            if isinstance(e, UniqueViolation):
                raise IntegrityError(str(e))
        elif isinstance(e, sqlite3.IntegrityError):
            raise IntegrityError(str(e))
        raise
    finally:
        cur.close()
        conn.close()


def init_tables():
    # No Vercel sem PostgreSQL: NÃO copiar o banco committed para /tmp/
    # para evitar sobrescrever dados novos com dados antigos do repositório
    if _use_pg():
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS ordens_servico (
                id SERIAL PRIMARY KEY, nome TEXT, telefone TEXT,
                aparelho TEXT, marca TEXT, modelo TEXT,
                defeito_relatado TEXT, estado_entrada TEXT, observacao TEXT,
                defeito_encontrado TEXT, valor_conserto REAL DEFAULT 0.0,
                valor_pecas REAL DEFAULT 0.0, tecnico_responsavel TEXT,
                status_retirada TEXT, data_entrada DATE, data_saida DATE
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user'
            )
        ''')
        cur.execute("SELECT COUNT(*) FROM usuarios WHERE username='assistec'")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO usuarios (username, password, role) VALUES (%s, %s, %s)",
                ('assistec', hashlib.sha256('exetec554412'.encode()).hexdigest(), 'admin')
            )
        conn.commit()
        cur.close()
        conn.close()
    else:
        conn = sqlite3.connect(_db_path())
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS ordens_servico (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telefone TEXT,
            aparelho TEXT, marca TEXT, modelo TEXT, defeito_relatado TEXT,
            estado_entrada TEXT, observacao TEXT, defeito_encontrado TEXT,
            valor_conserto REAL DEFAULT 0.0, valor_pecas REAL DEFAULT 0.0,
            tecnico_responsavel TEXT, status_retirada TEXT,
            data_entrada DATE, data_saida DATE
        )''')
        for coluna, tipo in {
            'valor_pecas': 'REAL DEFAULT 0.0',
            'tecnico_responsavel': 'TEXT',
            'data_saida': 'DATE'
        }.items():
            try:
                c.execute(f'ALTER TABLE ordens_servico ADD COLUMN {coluna} {tipo}')
            except sqlite3.OperationalError:
                pass
        c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
            username TEXT PRIMARY KEY, password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )''')
        c.execute("SELECT COUNT(*) FROM usuarios")
        if c.fetchone()[0] == 0:
            if os.path.exists('users.json'):
                with open('users.json', 'r') as f:
                    users = json.load(f)
                for uname, data in users.items():
                    c.execute(
                        "INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
                        (uname, data['password'], data['role'])
                    )
            else:
                c.execute(
                    "INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
                    ('assistec', hashlib.sha256('exetec554412'.encode()).hexdigest(), 'admin')
                )
        conn.commit()
        conn.close()

    # Auto-restore from backup on cold start (Vercel /tmp perdido)
    if not _use_pg():
        try:
            rows = query("SELECT COUNT(*) AS cnt FROM ordens_servico")
            if rows and rows[0]['cnt'] == 0:
                if restore_backup():
                    pass
        except Exception:
            pass


def load_users():
    rows = query("SELECT username, password, role FROM usuarios")
    return {r['username']: {'password': r['password'], 'role': r['role']} for r in rows}


# --- AUTO BACKUP / RESTORE (persistência em Vercel) ---

def _backup_path():
    return os.path.join('/tmp', 'backup.json') if IN_VERCEL else 'backup.json'


def export_backup():
    rows = query("SELECT * FROM ordens_servico ORDER BY id")
    usuarios = load_users()
    data = {
        'ordens': [dict(r) for r in rows],
        'usuarios': usuarios,
        'version': 1
    }
    try:
        with open(_backup_path(), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def restore_backup():
    path = _backup_path()
    if not os.path.exists(path):
        return False
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for row in data.get('ordens', []):
            keys = ', '.join(row.keys())
            vals = ', '.join(['?'] * len(row))
            execute(f"INSERT OR IGNORE INTO ordens_servico ({keys}) VALUES ({vals})",
                    tuple(row.values()))
        for uname, info in data.get('usuarios', {}).items():
            execute("INSERT OR IGNORE INTO usuarios (username, password, role) VALUES (?, ?, ?)",
                    (uname, info['password'], info['role']))
        return True
    except Exception:
        return False


def auto_backup():
    try:
        return export_backup()
    except Exception:
        return False
