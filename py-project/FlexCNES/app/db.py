"""Banco de dados da aplicação (SQLite): usuários, estabelecimentos e registros."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .security import hash_password, verify_password

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT NOT NULL UNIQUE COLLATE NOCASE,
    nome TEXT NOT NULL,
    senha_hash TEXT NOT NULL,
    criado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS estabelecimentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cnes TEXT NOT NULL UNIQUE,
    nome_fantasia TEXT NOT NULL,
    razao_social TEXT DEFAULT '',
    cnpj TEXT DEFAULT '',
    municipio TEXT DEFAULT '',
    uf TEXT DEFAULT '',
    ibge TEXT DEFAULT '',
    atualizado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS registros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    estabelecimento_id INTEGER NOT NULL REFERENCES estabelecimentos(id),
    categoria TEXT NOT NULL CHECK (categoria IN ('PROFISSIONAL','ESTABELECIMENTO')),
    operacao TEXT NOT NULL CHECK (operacao IN ('INCLUSAO','ALTERACAO','EXCLUSAO')),
    competencia TEXT NOT NULL,          -- AAAA-MM
    data_envio TEXT,                    -- AAAA-MM-DD
    nome_profissional TEXT DEFAULT '',
    descricao_planilha TEXT DEFAULT '', -- texto da coluna "Outras alterações"/"Estabelecimento"
    usa_ficha20 INTEGER NOT NULL DEFAULT 1,
    usa_ficha21 INTEGER NOT NULL DEFAULT 0,
    dados_json TEXT NOT NULL DEFAULT '{}',
    criado_em TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_registros_busca
    ON registros(usuario_id, estabelecimento_id, competencia);
CREATE TABLE IF NOT EXISTS config (
    chave TEXT PRIMARY KEY,
    valor TEXT
);
"""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class AuthError(Exception):
    pass


class Database:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # ---------------------------------------------------------------- usuários
    def user_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]

    def create_user(self, usuario: str, nome: str, senha: str) -> int:
        usuario = usuario.strip()
        nome = nome.strip()
        if not usuario or not nome:
            raise AuthError("Informe o nome e o usuário.")
        try:
            cur = self.conn.execute(
                "INSERT INTO usuarios(usuario, nome, senha_hash, criado_em) VALUES (?,?,?,?)",
                (usuario, nome, hash_password(senha), _now()),
            )
        except sqlite3.IntegrityError as e:
            raise AuthError("Já existe um usuário com esse login.") from e
        self.conn.commit()
        return cur.lastrowid

    def authenticate(self, usuario: str, senha: str) -> sqlite3.Row:
        row = self.conn.execute(
            "SELECT * FROM usuarios WHERE usuario = ?", (usuario.strip(),)
        ).fetchone()
        # verifica mesmo sem usuário, para não revelar por tempo de resposta se o login existe
        stored = row["senha_hash"] if row else hash_password("x", iterations=1000)
        ok = verify_password(senha, stored)
        if not row or not ok:
            raise AuthError("Usuário ou senha incorretos.")
        return row

    def change_password(self, user_id: int, nova: str) -> None:
        self.conn.execute(
            "UPDATE usuarios SET senha_hash=? WHERE id=?", (hash_password(nova), user_id)
        )
        self.conn.commit()

    # -------------------------------------------------------- estabelecimentos
    def list_estabelecimentos(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM estabelecimentos ORDER BY nome_fantasia COLLATE NOCASE"
        ).fetchall()

    def get_estabelecimento(self, est_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM estabelecimentos WHERE id=?", (est_id,)
        ).fetchone()

    def save_estabelecimento(self, data: dict[str, Any], est_id: int | None = None) -> int:
        cnes = "".join(ch for ch in str(data.get("cnes", "")) if ch.isdigit())
        if len(cnes) != 7:
            raise ValueError("O CNES deve ter 7 dígitos.")
        if not str(data.get("nome_fantasia", "")).strip():
            raise ValueError("Informe o nome fantasia do estabelecimento.")
        vals = (
            cnes,
            data["nome_fantasia"].strip(),
            data.get("razao_social", "").strip(),
            "".join(ch for ch in data.get("cnpj", "") if ch.isdigit()),
            data.get("municipio", "").strip(),
            data.get("uf", "").strip().upper(),
            "".join(ch for ch in data.get("ibge", "") if ch.isdigit()),
            _now(),
        )
        try:
            if est_id is None:
                cur = self.conn.execute(
                    "INSERT INTO estabelecimentos(cnes,nome_fantasia,razao_social,cnpj,"
                    "municipio,uf,ibge,atualizado_em) VALUES (?,?,?,?,?,?,?,?)",
                    vals,
                )
                est_id = cur.lastrowid
            else:
                self.conn.execute(
                    "UPDATE estabelecimentos SET cnes=?,nome_fantasia=?,razao_social=?,cnpj=?,"
                    "municipio=?,uf=?,ibge=?,atualizado_em=? WHERE id=?",
                    vals + (est_id,),
                )
        except sqlite3.IntegrityError as e:
            raise ValueError("Já existe um estabelecimento com esse CNES.") from e
        self.conn.commit()
        return est_id

    # ---------------------------------------------------------------- registros
    def save_registro(
        self,
        usuario_id: int,
        estabelecimento_id: int,
        *,
        categoria: str = "PROFISSIONAL",
        operacao: str,
        competencia: str,
        data_envio: str | None,
        nome_profissional: str = "",
        descricao_planilha: str = "",
        usa_ficha20: bool = True,
        usa_ficha21: bool = False,
        dados: dict | None = None,
        registro_id: int | None = None,
    ) -> int:
        payload = json.dumps(dados or {}, ensure_ascii=False)
        now = _now()
        if registro_id is None:
            cur = self.conn.execute(
                "INSERT INTO registros(usuario_id,estabelecimento_id,categoria,operacao,"
                "competencia,data_envio,nome_profissional,descricao_planilha,usa_ficha20,"
                "usa_ficha21,dados_json,criado_em,atualizado_em) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (usuario_id, estabelecimento_id, categoria, operacao, competencia, data_envio,
                 nome_profissional, descricao_planilha, int(usa_ficha20), int(usa_ficha21),
                 payload, now, now),
            )
            registro_id = cur.lastrowid
        else:
            # só o dono do registro pode alterá-lo
            cur = self.conn.execute(
                "UPDATE registros SET estabelecimento_id=?,categoria=?,operacao=?,competencia=?,"
                "data_envio=?,nome_profissional=?,descricao_planilha=?,usa_ficha20=?,"
                "usa_ficha21=?,dados_json=?,atualizado_em=? WHERE id=? AND usuario_id=?",
                (estabelecimento_id, categoria, operacao, competencia, data_envio,
                 nome_profissional, descricao_planilha, int(usa_ficha20), int(usa_ficha21),
                 payload, now, registro_id, usuario_id),
            )
            if cur.rowcount == 0:
                raise AuthError("Registro não encontrado para este usuário.")
        self.conn.commit()
        return registro_id

    def list_registros(
        self, usuario_id: int, estabelecimento_id: int | None = None,
        competencia: str | None = None,
    ) -> list[sqlite3.Row]:
        sql = "SELECT * FROM registros WHERE usuario_id=?"
        args: list[Any] = [usuario_id]
        if estabelecimento_id is not None:
            sql += " AND estabelecimento_id=?"
            args.append(estabelecimento_id)
        if competencia:
            sql += " AND competencia=?"
            args.append(competencia)
        sql += " ORDER BY competencia DESC, id DESC"
        return self.conn.execute(sql, args).fetchall()

    def get_registro(self, usuario_id: int, registro_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM registros WHERE id=? AND usuario_id=?", (registro_id, usuario_id)
        ).fetchone()

    def delete_registro(self, usuario_id: int, registro_id: int) -> None:
        self.conn.execute(
            "DELETE FROM registros WHERE id=? AND usuario_id=?", (registro_id, usuario_id)
        )
        self.conn.commit()

    # ------------------------------------------------------------------- config
    def get_config(self, chave: str, default: str = "") -> str:
        row = self.conn.execute("SELECT valor FROM config WHERE chave=?", (chave,)).fetchone()
        return row["valor"] if row and row["valor"] is not None else default

    def set_config(self, chave: str, valor: str) -> None:
        self.conn.execute(
            "INSERT INTO config(chave,valor) VALUES(?,?) "
            "ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor",
            (chave, valor),
        )
        self.conn.commit()
