"""Importação opcional da base de dados do CNES (ZIP do DATASUS) para consulta local.

Somente as tabelas necessárias são carregadas (estabelecimentos, municípios e CBO) em um
SQLite separado (`cnes_base.db`), em streaming - o ZIP nunca é extraído por inteiro.

ATENÇÃO: os nomes de arquivos/colunas abaixo seguem o dicionário de dados público do CNES
(tbEstabelecimento, tbMunicipio, tbAtividadeProfissional), mas NÃO foram validados contra um
ZIP real durante o desenvolvimento. O importador detecta colunas por aliases e informa no
relatório o que encontrou / não encontrou, para ajuste rápido se algo diferir.
"""
from __future__ import annotations

import csv
import io
import re
import sqlite3
import unicodedata
import zipfile
from pathlib import Path
from typing import Callable, Iterable

csv.field_size_limit(10_000_000)

SCHEMA = """
CREATE TABLE IF NOT EXISTS estabelecimento (
    cnes TEXT PRIMARY KEY, fantasia TEXT, razao TEXT, cnpj TEXT, mun_cod TEXT,
    logradouro TEXT, numero TEXT, bairro TEXT, cep TEXT, telefone TEXT
);
CREATE TABLE IF NOT EXISTS municipio (codigo TEXT PRIMARY KEY, nome TEXT, uf TEXT, busca TEXT);
CREATE TABLE IF NOT EXISTS cbo (codigo TEXT PRIMARY KEY, descricao TEXT, busca TEXT);
CREATE TABLE IF NOT EXISTS meta (chave TEXT PRIMARY KEY, valor TEXT);
CREATE INDEX IF NOT EXISTS ix_mun_busca ON municipio(busca);
"""

# tabela -> (regex do nome do arquivo, {coluna destino: [aliases de cabeçalho]}, obrigatórias)
SPECS = {
    "estabelecimento": (
        r"^tbestabelecimento\d*\.csv$",
        {
            "cnes": ["CO_CNES"],
            "fantasia": ["NO_FANTASIA"],
            "razao": ["NO_RAZAO_SOCIAL"],
            "cnpj": ["NU_CNPJ", "NU_CNPJ_MANTENEDORA"],
            "mun_cod": ["CO_MUNICIPIO_GESTOR", "CO_MUNICIPIO", "CO_IBGE"],
            "logradouro": ["NO_LOGRADOURO"],
            "numero": ["NU_ENDERECO"],
            "bairro": ["NO_BAIRRO"],
            "cep": ["CO_CEP"],
            "telefone": ["NU_TELEFONE"],
        },
        ("cnes", "fantasia"),
    ),
    "municipio": (
        r"^tbmunicipio\d*\.csv$",
        {
            "codigo": ["CO_MUNICIPIO", "CO_IBGE", "CO_MUNICIPIO_IBGE"],
            "nome": ["NO_MUNICIPIO", "DS_MUNICIPIO"],
            "uf": ["CO_SIGLA_ESTADO", "SG_UF", "CO_UF", "UF"],
        },
        ("codigo", "nome"),
    ),
    "cbo": (
        r"^tbatividadeprofissional\d*\.csv$",
        {
            "codigo": ["CO_CBO", "CO_ATIVIDADE_PROFISSIONAL"],
            "descricao": ["DS_ATIVIDADE_PROFISSIONAL", "NO_CBO", "DS_CBO"],
        },
        ("codigo", "descricao"),
    ),
}


DIGIT_COLS = {
    "estabelecimento": {"cnes", "cnpj", "mun_cod", "cep", "telefone"},
    "municipio": {"codigo"},
    "cbo": set(),
}


def _norm(name: str) -> str:
    return re.sub(r"[^A-Z0-9_]", "", name.strip().strip('"').upper())


def fold(text: str) -> str:
    """Maiúsculas sem acentos (para buscas que ignoram acentuação)."""
    t = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in t if not unicodedata.combining(ch)).upper().strip()


def _digits(v: str) -> str:
    return re.sub(r"\D", "", v or "")


class _Counter(io.RawIOBase):
    """Envolve o arquivo do ZIP e conta bytes lidos (para a barra de progresso)."""

    def __init__(self, f):
        self.f, self.n = f, 0

    def readable(self):
        return True

    def readinto(self, b):
        data = self.f.read(len(b))
        b[: len(data)] = data
        self.n += len(data)
        return len(data)


def import_zip(
    zip_path: str | Path,
    db_path: str | Path,
    progress: Callable[[str, float], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> dict:
    """Importa o ZIP do CNES. Retorna relatório: tabelas, linhas, colunas ausentes, não encontradas."""
    report: dict = {"tabelas": {}, "nao_encontradas": [], "colunas_ausentes": {}}
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)
    with zipfile.ZipFile(zip_path) as z:
        members = {Path(i.filename).name.lower(): i for i in z.infolist() if not i.is_dir()}
        for table, (pattern, cols, required) in SPECS.items():
            match = next((m for n, m in members.items() if re.match(pattern, n)), None)
            if match is None:
                report["nao_encontradas"].append(table)
                continue
            rows = _import_member(z, match, conn, table, cols, required, report, progress, cancelled)
            report["tabelas"][table] = rows
            if cancelled and cancelled():
                break
    conn.execute(
        "INSERT OR REPLACE INTO meta(chave,valor) VALUES('importado_de', ?)",
        (Path(zip_path).name,),
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta(chave,valor) VALUES('importado_em', datetime('now','localtime'))"
    )
    conn.commit()
    conn.close()
    return report


def _import_member(z, info, conn, table, cols, required, report, progress, cancelled) -> int:
    with z.open(info) as zf:
        counter = _Counter(zf)
        buf = io.BufferedReader(counter, buffer_size=1 << 20)
        enc = "cp1252"
        # detecta a codificação lendo o início sem consumir o fluxo principal
        with z.open(info) as probe:
            head = probe.read(65536)
        try:
            head.decode("utf-8")
            enc = "utf-8-sig"
        except UnicodeDecodeError as e:
            # um caractere multibyte cortado no fim do bloco não indica latin-1
            enc = "utf-8-sig" if e.start >= len(head) - 3 else "cp1252"
        text = io.TextIOWrapper(buf, encoding=enc, newline="")
        first = text.readline()
        delim = ";" if first.count(";") >= first.count(",") else ","
        header = [_norm(h) for h in next(csv.reader([first], delimiter=delim))]
        idx: dict[str, int] = {}
        for dest, aliases in cols.items():
            for a in aliases:
                if a in header:
                    idx[dest] = header.index(a)
                    break
        missing = [c for c in required if c not in idx]
        if missing:
            report["colunas_ausentes"][table] = {"faltando": missing, "cabecalho": header[:40]}
            return 0
        opt_missing = [c for c in cols if c not in idx]
        if opt_missing:
            report["colunas_ausentes"].setdefault(table, {"opcionais": opt_missing})
        dest_cols = list(idx)
        search_src = {"municipio": "nome", "cbo": "descricao"}.get(table)
        if search_src:
            dest_cols.append("busca")
        sql = f"INSERT OR REPLACE INTO {table}({','.join(dest_cols)}) VALUES({','.join('?' * len(dest_cols))})"
        total = max(info.file_size, 1)
        batch, n = [], 0
        reader = csv.reader(text, delimiter=delim)
        digit_cols = DIGIT_COLS[table]
        for row in reader:
            if len(row) <= max(idx.values()):
                continue
            vals = []
            for c in dest_cols:
                if c == "busca":
                    vals.append(fold(row[idx[search_src]]))
                    continue
                v = row[idx[c]].strip()
                vals.append(_digits(v) if c in digit_cols else v)
            if table == "estabelecimento" and vals[dest_cols.index("cnes")]:
                vals[dest_cols.index("cnes")] = vals[dest_cols.index("cnes")].zfill(7)
            batch.append(vals)
            n += 1
            if len(batch) >= 5000:
                conn.executemany(sql, batch)
                batch.clear()
                if progress:
                    progress(table, min(counter.n / total, 1.0))
                if cancelled and cancelled():
                    break
        if batch:
            conn.executemany(sql, batch)
        conn.commit()
        if progress:
            progress(table, 1.0)
        return n


class CnesBase:
    """Consulta à base CNES importada (opcional)."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def available(self) -> bool:
        if not self.path.exists():
            return False
        try:
            with self._conn() as c:
                return c.execute("SELECT COUNT(*) FROM estabelecimento").fetchone()[0] > 0
        except sqlite3.Error:
            return False

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(str(self.path))
        c.row_factory = sqlite3.Row
        return c

    def info(self) -> dict:
        if not self.path.exists():
            return {}
        with self._conn() as c:
            meta = {r["chave"]: r["valor"] for r in c.execute("SELECT * FROM meta")}
            for t in ("estabelecimento", "municipio", "cbo"):
                try:
                    meta[f"n_{t}"] = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                except sqlite3.Error:
                    meta[f"n_{t}"] = 0
        return meta

    def estabelecimento(self, cnes: str) -> dict | None:
        cnes = _digits(cnes).zfill(7)
        with self._conn() as c:
            r = c.execute("SELECT * FROM estabelecimento WHERE cnes=?", (cnes,)).fetchone()
            if not r:
                return None
            d = dict(r)
            d["municipio"], d["uf"], d["ibge"] = "", "", ""
            if d.get("mun_cod"):
                m = c.execute(
                    "SELECT * FROM municipio WHERE substr(codigo,1,6)=?", (d["mun_cod"][:6],)
                ).fetchone()
                if m:
                    d["municipio"], d["uf"], d["ibge"] = m["nome"], m["uf"] or "", m["codigo"]
            return d

    def cbo(self, codigo: str) -> str:
        with self._conn() as c:
            r = c.execute("SELECT descricao FROM cbo WHERE codigo=?", (codigo.strip(),)).fetchone()
            return r["descricao"] if r else ""

    def search_cbo(self, termo: str, limit: int = 30) -> list[tuple[str, str]]:
        with self._conn() as c:
            return [(r["codigo"], r["descricao"]) for r in c.execute(
                "SELECT codigo, descricao FROM cbo WHERE busca LIKE ? OR codigo LIKE ? "
                "ORDER BY descricao LIMIT ?", (f"%{fold(termo)}%", f"{termo.strip()}%", limit))]

    def municipio_por_nome(self, nome: str, uf: str = "") -> dict | None:
        with self._conn() as c:
            sql = "SELECT * FROM municipio WHERE busca = ?"
            args: list = [fold(nome)]
            if uf:
                sql += " AND uf = ?"
                args.append(uf.upper())
            r = c.execute(sql + " LIMIT 1", args).fetchone()
            return dict(r) if r else None
