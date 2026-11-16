"""Tabela de forma de contratação (Vinculação / Tipo / Sub-tipo) do SCNES – Portaria GM/MS 1.130/2017.

Cada linha: (vinc_cod, vinc_desc, tipo_cod, tipo_desc, sub_cod, sub_desc, solicita_cnpj).
Conferida com a tabela publicada por secretarias municipais (Curitiba/Juiz de Fora) que reproduz o anexo
da Portaria. Confirme sempre na Portaria em caso de dúvida.
"""
from __future__ import annotations

from .validators import only_digits

_NA = "NÃO SE APLICA"

TABELA: list[tuple[str, str, str, str, str, str, bool]] = [
    ("01", "VÍNCULO EMPREGATÍCIO", "01", "ESTATUTÁRIO EFETIVO", "01", "SERVIDOR PRÓPRIO", False),
    ("01", "VÍNCULO EMPREGATÍCIO", "01", "ESTATUTÁRIO EFETIVO", "02", "SERVIDOR CEDIDO", True),
    ("01", "VÍNCULO EMPREGATÍCIO", "02", "EMPREGADO PÚBLICO CELETISTA", "01", "PRÓPRIO", False),
    ("01", "VÍNCULO EMPREGATÍCIO", "02", "EMPREGADO PÚBLICO CELETISTA", "03", "CEDIDO", True),
    ("01", "VÍNCULO EMPREGATÍCIO", "03", "CONTRATADO TEMPORÁRIO OU POR PRAZO/TEMPO DETERMINADO", "01", "PÚBLICO", False),
    ("01", "VÍNCULO EMPREGATÍCIO", "03", "CONTRATADO TEMPORÁRIO OU POR PRAZO/TEMPO DETERMINADO", "02", "PRIVADO", False),
    ("01", "VÍNCULO EMPREGATÍCIO", "04", "CARGO COMISSIONADO", "01", "CARGO COMISSIONADO NÃO CEDIDO", False),
    ("01", "VÍNCULO EMPREGATÍCIO", "04", "CARGO COMISSIONADO", "03", "SERVIDOR PÚBLICO PRÓPRIO", False),
    ("01", "VÍNCULO EMPREGATÍCIO", "04", "CARGO COMISSIONADO", "04", "SERVIDOR PÚBLICO CEDIDO", True),
    ("01", "VÍNCULO EMPREGATÍCIO", "04", "CARGO COMISSIONADO", "05", "SEM VÍNCULO COM O SETOR PÚBLICO", False),
    ("01", "VÍNCULO EMPREGATÍCIO", "05", "CELETISTA", "00", _NA, False),
    ("02", "AUTÔNOMO", "09", "PESSOA JURÍDICA", "00", _NA, True),
    ("02", "AUTÔNOMO", "10", "PESSOA FÍSICA", "00", _NA, False),
    ("02", "AUTÔNOMO", "11", "COOPERADO", "00", _NA, True),
    ("05", "RESIDÊNCIA", "01", "RESIDENTE", "01", "PRÓPRIO", False),
    ("05", "RESIDÊNCIA", "01", "RESIDENTE", "02", "SUBSIDIADO POR OUTRO ENTE/ENTIDADE", True),
    ("06", "ESTÁGIO", "01", "ESTAGIÁRIO", "01", "PRÓPRIO", False),
    ("06", "ESTÁGIO", "01", "ESTAGIÁRIO", "02", "SUBSIDIADO POR OUTRO ENTE/ENTIDADE", True),
    ("07", "BOLSA", "01", "BOLSISTA", "01", "PRÓPRIO", False),
    ("07", "BOLSA", "01", "BOLSISTA", "02", "SUBSIDIADO POR OUTRO ENTE/ENTIDADE", True),
    ("08", "INTERMEDIADO", "01", "EMPREGADO PÚBLICO CELETISTA", "00", _NA, True),
    ("08", "INTERMEDIADO", "02", "CONTRATADO TEMPORÁRIO OU POR PRAZO/TEMPO DETERMINADO", "00", _NA, True),
    ("08", "INTERMEDIADO", "03", "CARGO COMISSIONADO", "00", _NA, True),
    ("08", "INTERMEDIADO", "04", "CELETISTA", "00", _NA, True),
    ("08", "INTERMEDIADO", "05", "AUTÔNOMO", "01", "PESSOA JURÍDICA", True),
    ("08", "INTERMEDIADO", "05", "AUTÔNOMO", "02", "PESSOA FÍSICA", True),
    ("08", "INTERMEDIADO", "06", "COOPERADO", "00", _NA, True),
    ("08", "INTERMEDIADO", "07", "SERVIDOR PÚBLICO", "01", "CEDIDO", True),
    ("09", "INFORMAL", "01", "CONTRATADO VERBALMENTE", "00", _NA, False),
    ("09", "INFORMAL", "02", "VOLUNTARIADO", "00", _NA, False),
    ("10", "SERVIDOR PÚBLICO CEDIDO PARA A INICIATIVA PRIVADA", "01", "SERVIDOR CEDIDO", "00", _NA, True),
    ("10", "SERVIDOR PÚBLICO CEDIDO PARA A INICIATIVA PRIVADA", "02", "EMPREGADO PÚBLICO CELETISTA", "00", _NA, True),
    ("10", "SERVIDOR PÚBLICO CEDIDO PARA A INICIATIVA PRIVADA", "03", "CARGO COMISSIONADO", "00", _NA, True),
]


def vinculacoes() -> list[tuple[str, str]]:
    seen: dict[str, str] = {}
    for vc, vd, *_ in TABELA:
        seen.setdefault(vc, vd)
    return list(seen.items())


def tipos(vinc: str) -> list[tuple[str, str]]:
    seen: dict[str, str] = {}
    for vc, _, tc, td, *_ in TABELA:
        if vc == vinc:
            seen.setdefault(tc, td)
    return list(seen.items())


def subtipos(vinc: str, tipo: str) -> list[tuple[str, str]]:
    return [(sc, sd) for vc, _, tc, _, sc, sd, _ in TABELA if vc == vinc and tc == tipo]


def achar(vinc: str, tipo: str, sub: str):
    for linha in TABELA:
        if linha[0] == vinc and linha[2] == tipo and linha[4] == sub:
            return linha
    return None


def exige_cnpj(vinc: str, tipo: str, sub: str) -> bool:
    linha = achar(vinc, tipo, sub)
    return bool(linha and linha[6])


def valid_cnpj(value: str | None) -> bool:
    d = only_digits(value)
    if len(d) != 14 or d == d[0] * 14:
        return False
    for n in (12, 13):
        pesos = list(range(n - 7, 1, -1)) + list(range(9, 1, -1))
        soma = sum(int(c) * p for c, p in zip(d[:n], pesos))
        dv = 0 if soma % 11 < 2 else 11 - soma % 11
        if int(d[n]) != dv:
            return False
    return True


def format_cnpj(value: str | None) -> str:
    d = only_digits(value)
    if len(d) != 14:
        return value or ""
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
