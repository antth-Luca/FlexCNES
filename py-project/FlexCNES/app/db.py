"""Banco de dados da aplicação (SQLite): usuários, estabelecimentos e registros."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from . import __version__
from .security import hash_password, password_problems, verify_password

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT NOT NULL UNIQUE COLLATE NOCASE,
    nome TEXT NOT NULL,
    senha_hash TEXT NOT NULL,
    criado_em TEXT NOT NULL,
    perfil TEXT NOT NULL DEFAULT 'COMUM',      -- ADMIN | COMUM
    ativo INTEGER NOT NULL DEFAULT 1,
    trocar_senha INTEGER NOT NULL DEFAULT 0    -- 1 após redefinição pelo administrador
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
    atualizado_em TEXT NOT NULL,
    regional TEXT DEFAULT ''
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


PERFIS = ('ADMIN', 'COMUM')


class AuthError(Exception):
    pass


# Versão do ESQUEMA do banco (não é a versão do programa). Só sobe quando a estrutura muda.
# 1 = FlexCNES 0.1.x (sem registro de versão); 2 = 0.2.x (perfis, regional, versão registrada).
SCHEMA_VERSION = 2


class DbVersionError(Exception):
    """O banco foi atualizado por um FlexCNES mais novo que este programa."""

    def __init__(self, db_schema: int, db_app: str, app_version: str):
        self.db_schema, self.db_app, self.app_version = db_schema, db_app, app_version
        super().__init__(
            f"Este banco foi atualizado pelo FlexCNES {db_app or '(versão desconhecida)'} "
            f"(esquema {db_schema}), mais novo que este programa (FlexCNES {app_version}, "
            f"esquema {SCHEMA_VERSION}).\nAtualize o FlexCNES neste computador para usar este banco.")


class DbMigrationNeeded(Exception):
    """Banco de versão anterior: precisa de confirmação antes de ser atualizado."""

    def __init__(self, db_schema: int, db_app: str, app_version: str):
        self.db_schema, self.db_app, self.app_version = db_schema, db_app, app_version
        super().__init__(
            f"Este banco foi criado por uma versão anterior do FlexCNES (esquema {db_schema}). "
            f"Para usá-lo, ele será atualizado para o esquema {SCHEMA_VERSION} (FlexCNES {app_version}).")


class Database:
    def __init__(self, path: str | Path, allow_migrate: bool = False):
        self.path = str(path)
        self.backup_path: str | None = None
        # timeout alto: com o banco em pasta de rede, outro computador pode estar gravando
        self.conn = sqlite3.connect(self.path, timeout=20)
        self.conn.row_factory = sqlite3.Row
        try:
            self._check_version(allow_migrate)
        except Exception:
            self.conn.close()
            raise
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        # migração: bancos criados antes da coluna "regional"
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(estabelecimentos)")}
        if "regional" not in cols:
            self.conn.execute("ALTER TABLE estabelecimentos ADD COLUMN regional TEXT DEFAULT ''")
        ucols = {r[1] for r in self.conn.execute("PRAGMA table_info(usuarios)")}
        for col, ddl in (("perfil", "TEXT NOT NULL DEFAULT 'COMUM'"),
                         ("ativo", "INTEGER NOT NULL DEFAULT 1"),
                         ("trocar_senha", "INTEGER NOT NULL DEFAULT 0")):
            if col not in ucols:
                self.conn.execute(f"ALTER TABLE usuarios ADD COLUMN {col} {ddl}")
        # bancos da v0.1: o primeiro usuário criado era o administrador
        if not self.conn.execute("SELECT 1 FROM usuarios WHERE perfil='ADMIN'").fetchone():
            self.conn.execute("UPDATE usuarios SET perfil='ADMIN' WHERE id=(SELECT MIN(id) FROM usuarios)")
        self._register_version()
        self.conn.commit()

    # ---------------------------------------------------------------- versão
    def _read_state(self) -> tuple[bool, int, str]:
        """(tem_dados, esquema, versão_do_programa_que_atualizou) sem alterar nada."""
        tem = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='usuarios'").fetchone() is not None
        if not tem:
            return False, SCHEMA_VERSION, ""
        schema, app = 1, ""
        has_cfg = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='config'").fetchone()
        if has_cfg:
            rows = dict(self.conn.execute(
                "SELECT chave, valor FROM config WHERE chave IN ('schema_version','ultimo_acesso_versao','criado_pela_versao')"
            ).fetchall())
            try:
                schema = int(rows.get("schema_version") or 1)
            except ValueError:
                schema = 1
            app = rows.get("ultimo_acesso_versao") or rows.get("criado_pela_versao") or ""
        return True, schema, app

    def _check_version(self, allow_migrate: bool) -> None:
        tem, schema, app = self._read_state()
        if not tem:
            return
        if schema > SCHEMA_VERSION:
            raise DbVersionError(schema, app, __version__)
        if schema < SCHEMA_VERSION:
            if not allow_migrate:
                raise DbMigrationNeeded(schema, app, __version__)
            self._backup(schema)

    def _backup(self, schema: int) -> None:
        """Cópia de segurança do arquivo antes de migrar (ao lado do banco)."""
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        dest = f"{self.path}.bak-esquema{schema}-{stamp}"
        dst = sqlite3.connect(dest)
        try:
            self.conn.backup(dst)
        finally:
            dst.close()
        self.backup_path = dest

    def _register_version(self) -> None:
        import socket
        cfg = {r["chave"] for r in self.conn.execute("SELECT chave FROM config")}
        now = _now()
        if "criado_pela_versao" not in cfg:
            self.set_config("criado_pela_versao", __version__, commit=False)
            self.set_config("criado_em", now, commit=False)
        self.set_config("schema_version", str(SCHEMA_VERSION), commit=False)
        self.set_config("ultimo_acesso_versao", __version__, commit=False)
        self.set_config("ultimo_acesso_em", now, commit=False)
        try:
            self.set_config("ultimo_acesso_maquina", socket.gethostname(), commit=False)
        except OSError:
            pass

    def version_info(self) -> dict[str, str]:
        return {
            "programa": __version__,
            "esquema_programa": str(SCHEMA_VERSION),
            "esquema_banco": self.get_config("schema_version", "?"),
            "criado_pela_versao": self.get_config("criado_pela_versao", "(anterior à 0.2.0)"),
            "ultimo_acesso_versao": self.get_config("ultimo_acesso_versao", ""),
            "ultimo_acesso_em": self.get_config("ultimo_acesso_em", ""),
            "ultimo_acesso_maquina": self.get_config("ultimo_acesso_maquina", ""),
        }

    def close(self) -> None:
        self.conn.close()

    # ---------------------------------------------------------------- usuários
    def user_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]

    def ping(self) -> None:
        self.conn.execute("SELECT 1").fetchone()

    def create_user(self, usuario: str, nome: str, senha: str, perfil: str = "COMUM",
                    trocar_senha: bool = False) -> int:
        usuario = usuario.strip()
        nome = nome.strip()
        if not usuario or not nome:
            raise AuthError("Informe o nome e o usuário.")
        if perfil not in PERFIS:
            raise AuthError("Perfil inválido.")
        try:
            cur = self.conn.execute(
                "INSERT INTO usuarios(usuario, nome, senha_hash, criado_em, perfil, trocar_senha)"
                " VALUES (?,?,?,?,?,?)",
                (usuario, nome, hash_password(senha), _now(), perfil, int(trocar_senha)),
            )
        except sqlite3.IntegrityError as e:
            raise AuthError("Já existe um usuário com esse login.") from e
        self.conn.commit()
        return cur.lastrowid

    def create_first_admin(self, usuario: str, nome: str, senha: str) -> int:
        """Cria o administrador no primeiro acesso (só se ainda não houver usuários)."""
        if self.user_count() > 0:
            raise AuthError("Já existe usuário cadastrado neste banco. Entre com o seu login.")
        return self.create_user(usuario, nome, senha, perfil="ADMIN")

    def authenticate(self, usuario: str, senha: str) -> sqlite3.Row:
        row = self.conn.execute(
            "SELECT * FROM usuarios WHERE usuario = ?", (usuario.strip(),)
        ).fetchone()
        # verifica mesmo sem usuário, para não revelar por tempo de resposta se o login existe
        stored = row["senha_hash"] if row else hash_password("x", iterations=1000)
        ok = verify_password(senha, stored)
        if not row or not ok:
            raise AuthError("Usuário ou senha incorretos.")
        if not row["ativo"]:
            raise AuthError("Usuário desativado. Procure o administrador.")
        return row

    def get_user(self, user_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM usuarios WHERE id=?", (user_id,)).fetchone()

    def list_users(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM usuarios ORDER BY perfil, nome COLLATE NOCASE").fetchall()

    def update_user(self, user_id: int, usuario: str, nome: str, ativo: bool) -> None:
        usuario, nome = usuario.strip(), nome.strip()
        if not usuario or not nome:
            raise AuthError("Informe o nome e o usuário.")
        try:
            self.conn.execute("UPDATE usuarios SET usuario=?, nome=?, ativo=? WHERE id=?",
                              (usuario, nome, int(ativo), user_id))
        except sqlite3.IntegrityError as e:
            raise AuthError("Já existe um usuário com esse login.") from e
        self.conn.commit()

    def change_password(self, user_id: int, nova: str, trocar_senha: bool = False) -> None:
        """Define a senha sem conferir a atual (uso interno/administrativo)."""
        self.conn.execute("UPDATE usuarios SET senha_hash=?, trocar_senha=? WHERE id=?",
                          (hash_password(nova), int(trocar_senha), user_id))
        self.conn.commit()

    def change_own_password(self, user_id: int, atual: str, nova: str) -> None:
        row = self.get_user(user_id)
        if not row or not verify_password(atual, row["senha_hash"]):
            raise AuthError("A senha atual está incorreta.")
        if atual == nova:
            raise AuthError("A nova senha deve ser diferente da atual.")
        probs = password_problems(nova)
        if probs:
            raise AuthError(" ".join(probs))
        self.change_password(user_id, nova, trocar_senha=False)

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
            data.get("regional", "").strip(),
            _now(),
        )
        try:
            if est_id is None:
                cur = self.conn.execute(
                    "INSERT INTO estabelecimentos(cnes,nome_fantasia,razao_social,cnpj,"
                    "municipio,uf,ibge,regional,atualizado_em) VALUES (?,?,?,?,?,?,?,?,?)",
                    vals,
                )
                est_id = cur.lastrowid
            else:
                self.conn.execute(
                    "UPDATE estabelecimentos SET cnes=?,nome_fantasia=?,razao_social=?,cnpj=?,"
                    "municipio=?,uf=?,ibge=?,regional=?,atualizado_em=? WHERE id=?",
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

    def set_config(self, chave: str, valor: str, commit: bool = True) -> None:
        self.conn.execute(
            "INSERT INTO config(chave,valor) VALUES(?,?) "
            "ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor",
            (chave, valor),
        )
        if commit:
            self.conn.commit()
