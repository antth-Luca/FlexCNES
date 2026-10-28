"""Preferências do usuário (tema) em JSON na pasta de dados."""
from __future__ import annotations

import json

from .paths import data_dir

THEMES = {"Sistema": "system", "Claro": "light", "Escuro": "dark"}


def _file():
    return data_dir() / "config.json"


def load() -> dict:
    try:
        return json.loads(_file().read_text(encoding="utf-8"))
    except Exception:
        return {}


def save(**kv) -> None:
    try:
        cfg = load()
        cfg.update(kv)
        _file().write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
