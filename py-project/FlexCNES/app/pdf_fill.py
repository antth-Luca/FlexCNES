"""Preenchimento das Fichas 20 e 21: desenha os dados sobre o PDF original (sobreposição)."""
from __future__ import annotations

import io
import math
from pathlib import Path
from typing import Any, Iterable

from pypdf import PdfReader, PdfWriter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from . import ficha_layout as L
from .paths import resource_path
from .validators import date_digits, only_digits

FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
DEFAULT_SIZE = 9.5

# campos de `dados` (ficha 20) que são datas e vão em células DDMMAAAA
DATE_FIELDS = {"data_nasc", "cert_data", "rg_data", "data_entrada", "data_naturalizacao",
               "ctps_data", "data_deslig"}
# campos numéricos em células: somente dígitos
DIGIT_FIELDS = {"pis", "cpf", "cns", "ibge_nasc", "titulo", "zona", "secao", "ctps_num",
                "ibge_res", "cep", "telefone", "cnes"}
UPPER_FIELDS_EXCLUDE: set[str] = set()


class _Painter:
    def __init__(self, c: canvas.Canvas):
        self.c = c

    @staticmethod
    def y(top: float) -> float:
        """Converte y (origem no topo) para a origem do PDF (canto inferior)."""
        return L.PAGE_H - top

    def _fit_size(self, text: str, max_w: float, size: float, min_size: float = 5.5) -> float:
        while size > min_size and stringWidth(text, FONT, size) > max_w:
            size -= 0.25
        return size

    def text(self, value: str, box, lab: float, base: float | None = None,
             size: float = DEFAULT_SIZE):
        x0, top, x1, bottom = box
        if not value:
            return
        value = value.upper()
        pad = 3.0
        area_top = top + lab
        size = self._fit_size(value, (x1 - x0) - 2 * pad, size)
        if base is not None:
            baseline = top + base
        else:
            baseline = (area_top + bottom) / 2 + size * 0.35
        self.c.setFont(FONT, size)
        self.c.drawString(x0 + pad, self.y(baseline), value)

    def center(self, value: str, box, size: float = DEFAULT_SIZE):
        x0, top, x1, bottom = box
        if not value:
            return
        value = value.upper()
        size = self._fit_size(value, (x1 - x0) - 2, size)
        self.c.setFont(FONT, size)
        cx = (x0 + x1) / 2
        baseline = (top + bottom) / 2 + size * 0.35
        self.c.drawCentredString(cx, self.y(baseline), value)

    def check(self, box):
        x0, top, x1, bottom = box
        self.c.setLineWidth(1.3)
        m = 1.8
        self.c.line(x0 + m, self.y(top + m), x1 - m, self.y(bottom - m))
        self.c.line(x0 + m, self.y(bottom - m), x1 - m, self.y(top + m))

    def comb(self, value: str, first: float, last: float, n: int, ytop: float, ybot: float,
             size: float = 10.0):
        if not value:
            return
        value = value[:n]
        w = (last - first) / n
        self.c.setFont(FONT, size)
        baseline = (ytop + ybot) / 2 + size * 0.35
        for i, ch in enumerate(value):
            self.c.drawCentredString(first + w * (i + 0.5), self.y(baseline), ch.upper())

    def cells(self, value: str, xs: list[float], ytop: float, ybot: float, size: float = 10.0):
        if not value:
            return
        value = value[: len(xs) - 1]
        self.c.setFont(FONT, size)
        baseline = (ytop + ybot) / 2 + size * 0.35
        for i, ch in enumerate(value):
            self.c.drawCentredString((xs[i] + xs[i + 1]) / 2, self.y(baseline), ch.upper())

    def draw(self, spec: tuple, value: Any, key: str = ""):
        kind = spec[0]
        if kind == "check":
            if value:
                self.check(spec[1])
            return
        value = "" if value is None else str(value)
        if key in DATE_FIELDS:
            value = date_digits(value)
        elif key in DIGIT_FIELDS:
            value = only_digits(value)
        if kind == "text":
            self.text(value, spec[1], spec[2], spec[3] if len(spec) > 3 else None)
        elif kind == "center":
            self.center(value, spec[1])
        elif kind == "comb":
            self.comb(value, *spec[1:])
        elif kind == "cells":
            self.cells(value, *spec[1:])


def _merge(template: Path, overlay_pdf: bytes, writer: PdfWriter) -> None:
    base = PdfReader(str(template)).pages[0]
    over = PdfReader(io.BytesIO(overlay_pdf)).pages[0]
    base.merge_page(over)
    writer.add_page(base)


def _new_canvas() -> tuple[io.BytesIO, canvas.Canvas]:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(L.PAGE_W, L.PAGE_H))
    return buf, c


def _draw_header(p: _Painter, spec: dict, estab: dict, operacao: str) -> None:
    p.draw(spec["cnes"], estab.get("cnes", ""), "cnes")
    p.draw(spec["nome_fantasia"], estab.get("nome_fantasia", ""))
    for op in ("INCLUSAO", "ALTERACAO", "EXCLUSAO"):
        p.draw(spec[f"op_{op}"], operacao == op)


def render_ficha20(estab: dict, operacao: str, dados: dict) -> bytes:
    """Retorna os bytes de um PDF (1 página) com a Ficha 20 preenchida."""
    buf, c = _new_canvas()
    p = _Painter(c)
    _draw_header(p, L.HEADER_20, estab, operacao)

    cad = dados.get("cadastramento", "")
    p.draw(L.FICHA20["cad_SUS"], cad == "SUS")
    p.draw(L.FICHA20["cad_NAO_SUS"], cad == "NAO_SUS")
    p.draw(L.FICHA20["sexo_M"], dados.get("sexo") == "M")
    p.draw(L.FICHA20["sexo_F"], dados.get("sexo") == "F")
    p.draw(L.FICHA20["nac_B"], dados.get("nacionalidade") == "B")
    p.draw(L.FICHA20["nac_E"], dados.get("nacionalidade") == "E")
    p.draw(L.FICHA20["freq_S"], dados.get("freq_escola") == "S")
    p.draw(L.FICHA20["freq_N"], dados.get("freq_escola") == "N")

    skip = {"cad_SUS", "cad_NAO_SUS", "sexo_M", "sexo_F", "nac_B", "nac_E", "freq_S", "freq_N"}
    key_map = {"cert_tipo": "cert_tipo"}
    for key, spec in L.FICHA20.items():
        if key in skip:
            continue
        p.draw(spec, dados.get(key_map.get(key, key), ""), key)
    c.showPage()
    c.save()
    return buf.getvalue()


def render_ficha21(estab: dict, operacao: str, nome_prof: str,
                   vinculos: list[dict]) -> list[bytes]:
    """Retorna uma lista de PDFs (1 página cada), com até 3 vínculos por página."""
    paginas = max(1, math.ceil(len(vinculos) / L.VINCULOS_POR_PAGINA))
    out = []
    for pg in range(paginas):
        buf, c = _new_canvas()
        p = _Painter(c)
        _draw_header(p, L.HEADER_21, estab, operacao)
        p.draw(L.HEADER_21["nome"], nome_prof)
        chunk = vinculos[pg * 3: pg * 3 + 3]
        for idx, v in enumerate(chunk):
            fields = L.vinculo_fields(idx)
            for key, spec in fields.items():
                if key in ("sus_S", "sus_N"):
                    p.draw(spec, v.get("sus") == key[-1])
                else:
                    p.draw(spec, v.get(key, ""), key)
        c.showPage()
        c.save()
        out.append(buf.getvalue())
    return out


def write_ficha20(path: str | Path, estab: dict, operacao: str, dados: dict) -> Path:
    w = PdfWriter()
    _merge(resource_path("assets", "ficha20.pdf"), render_ficha20(estab, operacao, dados), w)
    return _save(w, path)


def write_ficha21(path: str | Path, estab: dict, operacao: str, nome_prof: str,
                  vinculos: Iterable[dict]) -> Path:
    w = PdfWriter()
    for page_bytes in render_ficha21(estab, operacao, nome_prof, list(vinculos)):
        _merge(resource_path("assets", "ficha21.pdf"), page_bytes, w)
    return _save(w, path)


def _save(writer: PdfWriter, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        writer.write(fh)
    return path
