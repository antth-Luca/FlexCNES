"""Validações e formatações de dados cadastrais (CPF, CNS, PIS, datas...)."""
from __future__ import annotations

import re
from datetime import date, datetime

MESES = [
    "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
    "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO",
]


def only_digits(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")


def valid_cpf(value: str) -> bool:
    d = only_digits(value)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for n in (9, 10):
        s = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        dv = (s * 10) % 11 % 10
        if dv != int(d[n]):
            return False
    return True


def valid_pis(value: str) -> bool:
    d = only_digits(value)
    if len(d) != 11:
        return False
    pesos = [3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    s = sum(int(d[i]) * pesos[i] for i in range(10))
    dv = 11 - s % 11
    if dv >= 10:
        dv = 0
    return dv == int(d[10])


def valid_cns(value: str) -> bool:
    """Cartão Nacional de Saúde (definitivo 1/2 e provisório 7/8/9)."""
    d = only_digits(value)
    if len(d) != 15:
        return False
    if d[0] in "12":
        pis = d[:11]
        s = sum(int(pis[i]) * (15 - i) for i in range(11))
        resto = s % 11
        dv = 11 - resto
        if dv == 11:
            dv = 0
        if dv == 10:
            s += 2
            resto = s % 11
            dv = 11 - resto
            res = pis + "001" + str(dv)
        else:
            res = pis + "000" + str(dv)
        return res == d
    if d[0] in "789":
        s = sum(int(d[i]) * (15 - i) for i in range(15))
        return s % 11 == 0
    return False


def parse_date(text: str | None) -> date | None:
    """Aceita dd/mm/aaaa, dd-mm-aaaa, ddmmaaaa ou aaaa-mm-dd. Retorna None se vazio/inválido."""
    t = (text or "").strip()
    if not t:
        return None
    t8 = only_digits(t)
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(t, fmt).date()
        except ValueError:
            pass
    if len(t8) == 8 and re.fullmatch(r"\d+", t):
        try:
            return datetime.strptime(t8, "%d%m%Y").date()
        except ValueError:
            return None
    return None


def format_date(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else ""


def date_digits(text: str | None) -> str:
    """Data como DDMMAAAA (para campos com quadradinhos). Vazio se inválida."""
    d = parse_date(text)
    return d.strftime("%d%m%Y") if d else ""


def is_blank_or_valid_date(text: str | None) -> bool:
    return not (text or "").strip() or parse_date(text) is not None


def competencia_label(ano: int, mes: int) -> str:
    return f"{MESES[mes - 1].capitalize()}{ano}"
