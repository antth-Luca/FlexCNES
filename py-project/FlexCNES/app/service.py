"""Regras de negócio da aplicação (independentes da interface gráfica)."""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from . import pdf_fill, planilha
from .cnes_import import CnesBase
from .db import Database
from .validators import (MESES, format_date, is_blank_or_valid_date, only_digits, parse_date,
                         valid_cns, valid_cpf, valid_pis)

OPERACOES = {"INCLUSAO": "Inclusão", "ALTERACAO": "Alteração", "EXCLUSAO": "Exclusão"}

# campos de data da Ficha 20 / vínculos (para validação)
DATE_LABELS_F20 = {
    "data_nasc": "Data de nascimento", "cert_data": "Data de emissão da certidão",
    "rg_data": "Data de emissão da identidade", "data_entrada": "Data de entrada",
    "data_naturalizacao": "Data de naturalização", "ctps_data": "Data de emissão da CTPS",
}
DATE_LABELS_VINC = {"data_entrada": "Data de entrada", "data_deslig": "Data de desligamento"}


@dataclass
class Session:
    user_id: int
    usuario: str
    nome: str


@dataclass
class Resultado:
    registro_id: int
    arquivos: list[Path] = field(default_factory=list)


def safe_filename(text: str, maxlen: int = 40) -> str:
    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9]+", "_", t).strip("_")
    return t[:maxlen] or "sem_nome"


def competencia_key(ano: int, mes: int) -> str:
    return f"{ano:04d}-{mes:02d}"


def split_competencia(key: str) -> tuple[int, int]:
    a, m = key.split("-")
    return int(a), int(m)


class Service:
    def __init__(self, db: Database, cnes_base: CnesBase, out_root: Path):
        self.db = db
        self.cnes = cnes_base
        self.out_root = Path(out_root)

    # ---------------------------------------------------------------- validação
    def validar(self, form: dict[str, Any]) -> tuple[list[str], list[str]]:
        """Retorna (erros bloqueantes, avisos). `form` no formato descrito em `salvar`."""
        erros: list[str] = []
        avisos: list[str] = []
        dados = form.get("dados", {})
        if form.get("categoria", "PROFISSIONAL") == "ESTABELECIMENTO":
            if not (form.get("descricao_planilha") or "").strip():
                erros.append("Descreva a alteração do estabelecimento.")
        else:
            if not (dados.get("nome") or "").strip():
                erros.append("Informe o nome do profissional.")
            if not (form.get("usa_ficha20") or form.get("usa_ficha21")):
                erros.append("Marque ao menos uma ficha (20 e/ou 21).")
            if form.get("operacao") == "ALTERACAO" and not (form.get("descricao_planilha") or "").strip():
                avisos.append("Sem descrição da alteração: na planilha constará só o nome do profissional.")
        if form.get("data_envio") and not is_blank_or_valid_date(form["data_envio"]):
            erros.append("Data de envio inválida (use dd/mm/aaaa).")

        if form.get("usa_ficha20"):
            for k, label in DATE_LABELS_F20.items():
                if not is_blank_or_valid_date(dados.get(k)):
                    erros.append(f"{label}: data inválida (use dd/mm/aaaa).")
            for key, label, fn, n in (("cpf", "CPF", valid_cpf, 11), ("pis", "PIS/PASEP", valid_pis, 11),
                                      ("cns", "CNS", valid_cns, 15)):
                v = only_digits(dados.get(key))
                if v and len(v) != n:
                    erros.append(f"{label} deve ter {n} dígitos.")
                elif v and not fn(v):
                    avisos.append(f"{label} com dígito verificador inválido.")
            v = only_digits(dados.get("cep"))
            if v and len(v) != 8:
                erros.append("CEP deve ter 8 dígitos.")
            # Código IBGE: 6 dígitos (padrão do CNES) ou 7 (com dígito verificador).
            for key, label in (("ibge_nasc", "IBGE (nascimento)"), ("ibge_res", "IBGE (residência)")):
                v = only_digits(dados.get(key))
                if v and len(v) not in (6, 7):
                    erros.append(f"{label} deve ter 6 ou 7 dígitos.")
            for key, label in (("uf_nasc", "UF de nascimento"), ("uf_res", "UF de residência"),
                               ("rg_uf", "UF da identidade"), ("ctps_uf", "UF da CTPS")):
                v = (dados.get(key) or "").strip()
                if v and not re.fullmatch(r"[A-Za-z]{2}", v):
                    erros.append(f"{label}: use a sigla com 2 letras.")
        if form.get("usa_ficha21"):
            for i, v in enumerate(form.get("vinculos", []), 1):
                for k, label in DATE_LABELS_VINC.items():
                    if not is_blank_or_valid_date(v.get(k)):
                        erros.append(f"Vínculo {i} – {label}: data inválida (use dd/mm/aaaa).")
                cbo = (v.get("cbo_cod") or "").strip()
                if cbo and not re.fullmatch(r"\d{6}", cbo):
                    avisos.append(f"Vínculo {i}: o CBO costuma ter 6 dígitos.")
        return erros, avisos

    # ------------------------------------------------------------------ salvar
    def salvar(self, sess: Session, est_id: int, form: dict[str, Any],
               registro_id: int | None = None) -> int:
        """`form`: categoria, operacao, ano, mes, data_envio (dd/mm/aaaa), usa_ficha20, usa_ficha21,
        descricao_planilha, dados{...}, vinculos[...]"""
        dados = dict(form.get("dados", {}))
        dados["vinculos"] = form.get("vinculos", [])
        envio = parse_date(form.get("data_envio"))
        return self.db.save_registro(
            sess.user_id, est_id,
            categoria=form.get("categoria", "PROFISSIONAL"),
            operacao=form["operacao"],
            competencia=competencia_key(form["ano"], form["mes"]),
            data_envio=envio.isoformat() if envio else None,
            nome_profissional=(dados.get("nome") or "").strip(),
            descricao_planilha=(form.get("descricao_planilha") or "").strip(),
            usa_ficha20=bool(form.get("usa_ficha20")),
            usa_ficha21=bool(form.get("usa_ficha21")),
            dados=dados,
            registro_id=registro_id,
        )

    def registro_para_form(self, sess: Session, registro_id: int) -> dict[str, Any] | None:
        r = self.db.get_registro(sess.user_id, registro_id)
        if not r:
            return None
        dados = json.loads(r["dados_json"] or "{}")
        vinc = dados.pop("vinculos", [])
        ano, mes = split_competencia(r["competencia"])
        envio = date.fromisoformat(r["data_envio"]) if r["data_envio"] else None
        return {
            "registro_id": r["id"], "categoria": r["categoria"], "operacao": r["operacao"],
            "ano": ano, "mes": mes, "data_envio": format_date(envio),
            "usa_ficha20": bool(r["usa_ficha20"]), "usa_ficha21": bool(r["usa_ficha21"]),
            "descricao_planilha": r["descricao_planilha"], "dados": dados, "vinculos": vinc,
            "estabelecimento_id": r["estabelecimento_id"],
        }

    # ------------------------------------------------------------------- PDFs
    def pasta_saida(self, estab: dict, competencia: str) -> Path:
        return self.out_root / estab["cnes"] / competencia

    def gerar_pdfs(self, sess: Session, registro_id: int) -> list[Path]:
        r = self.db.get_registro(sess.user_id, registro_id)
        if not r:
            raise ValueError("Registro não encontrado.")
        est = dict(self.db.get_estabelecimento(r["estabelecimento_id"]))
        dados = json.loads(r["dados_json"] or "{}")
        vinc = dados.pop("vinculos", [])
        pasta = self.pasta_saida(est, r["competencia"])
        base = f"{safe_filename(r['nome_profissional'])}_{OPERACOES[r['operacao']].lower()[:4]}"
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out: list[Path] = []
        if r["usa_ficha20"]:
            out.append(pdf_fill.write_ficha20(pasta / f"Ficha20_{base}_{stamp}.pdf",
                                              est, r["operacao"], dados))
        if r["usa_ficha21"]:
            out.append(pdf_fill.write_ficha21(pasta / f"Ficha21_{base}_{stamp}.pdf",
                                              est, r["operacao"], r["nome_profissional"], vinc))
        return out

    # --------------------------------------------------------------- planilha
    def linhas_planilha(self, sess: Session, est_id: int, ano: int, mes: int) -> list[dict]:
        est = dict(self.db.get_estabelecimento(est_id))
        regs = [dict(r) for r in self.db.list_registros(sess.user_id, est_id, competencia_key(ano, mes))]
        return planilha.montar_linhas(regs, est, MESES[mes - 1])

    def exportar_planilha(self, sess: Session, est_id: int, ano: int, mes: int, caminho: Path,
                          observacoes: str = "", anexar: bool = False) -> tuple[Path, bool]:
        est = dict(self.db.get_estabelecimento(est_id))
        linhas = self.linhas_planilha(sess, est_id, ano, mes)
        if not linhas:
            raise ValueError("Não há registros neste mês para o estabelecimento selecionado.")
        return planilha.write_workbook(
            caminho, ano=ano, mes=mes, municipio=est.get("municipio") or "",
            linhas=linhas, realizado_por=sess.nome, observacoes=observacoes,
            anexar_existente=anexar,
        )

    def nome_padrao_planilha(self, est: dict, ano: int, mes: int) -> str:
        return f"PLANILHA_FlexCNES_{MESES[mes - 1]}_{ano}_{est['cnes']}.xlsx"
