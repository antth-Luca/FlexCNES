"""Verificação de acesso à pasta/arquivo do banco (local ou em rede) e cópia segura do banco.

Tudo roda com limite de tempo: uma pasta de rede indisponível pode travar chamadas do sistema
operacional por muitos segundos, e a interface não deve congelar junto.
"""
from __future__ import annotations

import os
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")
TIMEOUT_S = 12.0


def with_timeout(fn: Callable[[], T], seconds: float, default: T) -> T:
    """Executa `fn` em outra thread; devolve `default` se passar de `seconds`."""
    box: list = []

    def run():
        try:
            box.append(fn())
        except Exception as e:  # noqa: BLE001 - qualquer falha vira resultado
            box.append(e)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(seconds)
    if not box:
        return default
    if isinstance(box[0], Exception):
        raise box[0]
    return box[0]


def normalize_dir(text: str) -> str:
    """Limpa o texto digitado/colado. Devolve '' se não for um caminho absoluto
    (aceita C:/pasta, Z:/pasta e //servidor/compartilhamento/pasta, com barras normais ou invertidas)."""
    t = (text or "").strip().strip('"').strip("'").strip()
    t = os.path.expandvars(os.path.expanduser(t))
    if not t or not os.path.isabs(t):
        return ""
    return t.rstrip("\\/") if len(t) > 3 else t


def _inspect(folder: str) -> dict:
    p = Path(folder)
    if not p.exists():
        return {"ok": False, "has_db": False,
                "msg": f"A pasta não existe ou não está acessível:\n{folder}"}
    if not p.is_dir():
        return {"ok": False, "has_db": False, "msg": f"O caminho não é uma pasta:\n{folder}"}
    probe = p / f".flexcnes_{uuid.uuid4().hex[:8]}.tmp"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as e:
        return {"ok": False, "has_db": False,
                "msg": f"Sem permissão para gravar na pasta:\n{folder}\n({e.strerror or e})"}
    from .paths import DB_FILENAME
    dbfile = p / DB_FILENAME
    if not dbfile.exists():
        return {"ok": True, "has_db": False, "msg": ""}
    try:
        con = sqlite3.connect(str(dbfile), timeout=5)
        try:
            names = {r[0] for r in con.execute("SELECT name FROM sqlite_master")}
        finally:
            con.close()
    except sqlite3.Error as e:
        return {"ok": False, "has_db": True, "msg": f"Não foi possível abrir o banco:\n{e}"}
    if "usuarios" not in names:
        return {"ok": False, "has_db": True,
                "msg": "Já existe um arquivo com o nome do banco, mas ele não é um banco do FlexCNES."}
    return {"ok": True, "has_db": True, "msg": ""}


def inspect_dir(folder: str | Path, seconds: float = TIMEOUT_S) -> dict:
    """{'ok', 'has_db', 'msg'}: a pasta existe, aceita gravação e (se houver) o banco abre."""
    folder = str(folder)
    try:
        return with_timeout(lambda: _inspect(folder), seconds, {
            "ok": False, "has_db": False,
            "msg": f"Tempo esgotado ao acessar a pasta (rede lenta ou indisponível):\n{folder}"})
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "has_db": False, "msg": f"Falha ao acessar a pasta:\n{folder}\n({e})"}


def db_status(db_file: str | Path, require_db: bool = False, seconds: float = TIMEOUT_S) -> tuple[bool, str]:
    """(ok, mensagem). Com `require_db`, a ausência do arquivo do banco também é falha."""
    r = inspect_dir(Path(db_file).parent, seconds)
    if r["ok"] and require_db and not r["has_db"]:
        return False, f"O arquivo do banco não foi encontrado em:\n{Path(db_file).parent}"
    return r["ok"], r["msg"]


def copy_db(src_file: str | Path, dst_dir: str | Path, seconds: float = 60.0) -> Path:
    """Copia o banco com a API de backup do SQLite (consistente mesmo com o arquivo em uso)."""
    from .paths import DB_FILENAME
    dst = Path(dst_dir) / DB_FILENAME
    if dst.exists():
        raise FileExistsError(f"Já existe um banco em {dst_dir}")

    def run():
        src = sqlite3.connect(str(src_file), timeout=10)
        out = sqlite3.connect(str(dst), timeout=10)
        try:
            src.backup(out)
        finally:
            out.close()
            src.close()
        return dst

    try:
        return with_timeout(run, seconds, None) or (_ for _ in ()).throw(
            TimeoutError("Tempo esgotado ao copiar o banco."))
    except Exception:
        if dst.exists():
            try:
                dst.unlink()
            except OSError:
                pass
        raise
