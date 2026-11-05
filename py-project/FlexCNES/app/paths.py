"""Localização de arquivos (dados do usuário e recursos embutidos)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "FlexCNES_Preenchimento"


def resource_path(*parts: str) -> Path:
    """Caminho de um recurso embutido (funciona também com PyInstaller)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base.joinpath(*parts)


def data_dir() -> Path:
    """Pasta de dados do usuário (banco SQLite, base CNES). Sobrescrevível por FCNES_DATA_DIR."""
    override = os.environ.get("FCNES_DATA_DIR")
    if override:
        p = Path(override)
    elif os.name == "nt":
        p = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
    else:
        p = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


DB_FILENAME = "flexcnes_app.db"


def _config_file() -> Path:
    return data_dir() / "config.json"


def configured_db_dir() -> str:
    """Pasta do banco definida pelo administrador (vazio = padrão). Guardada no config.json LOCAL
    de cada computador, pois a localização do banco não pode ficar dentro do próprio banco."""
    try:
        import json
        return str(json.loads(_config_file().read_text(encoding="utf-8")).get("db_dir", "") or "")
    except Exception:
        return ""


def default_db_dir() -> Path:
    return data_dir()


def db_dir() -> Path:
    custom = configured_db_dir()
    return Path(custom) if custom else default_db_dir()


def app_db_path() -> Path:
    return db_dir() / DB_FILENAME


def cnes_db_path() -> Path:
    return data_dir() / "cnes_base.db"


def default_output_dir() -> Path:
    """Pasta padrão onde PDFs e planilhas gerados são gravados."""
    docs = Path.home() / "Documents"
    base = docs if docs.exists() else Path.home()
    p = base / "FlexCNES_Fichas"
    p.mkdir(parents=True, exist_ok=True)
    return p
