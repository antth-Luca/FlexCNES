"""Coordenadas dos campos das Fichas 20 e 21 (PDF A4, origem no canto superior esquerdo, em pontos).

Tipos de campo:
  ("text",  (x0, top, x1, bottom), lab[, base])   texto livre; `lab` = altura do rótulo no topo da caixa;
                                          `base` (opcional) = baseline a partir do topo da caixa
  ("comb",  first_tick, last_tick, n, ytop, ybottom)   n dígitos entre os traços do campo
  ("cells", [x0, x1, ...], ytop, ybottom)  células com limites explícitos (um caractere por célula)
  ("check", (x0, top, x1, bottom))   caixa de marcação (desenha um X)
  ("center", (x0, top, x1, bottom))  texto centralizado em caixa pequena
"""
from __future__ import annotations

PAGE_W, PAGE_H = 595.22, 842.0

# ----------------------------------------------------------------------------
# Cabeçalho comum às duas fichas
# ----------------------------------------------------------------------------
HEADER_20 = {
    "cnes": ("comb", 30.5, 139.6, 7, 101.0, 114.1),
    "nome_fantasia": ("text", (221.8, 99.0, 559.0, 115.8), 6),
    "op_INCLUSAO": ("check", (283.3, 74.2, 299.5, 84.5)),
    "op_ALTERACAO": ("check", (418.6, 73.9, 434.6, 83.4)),
    "op_EXCLUSAO": ("check", (544.4, 74.0, 560.2, 83.8)),
}
HEADER_21 = {
    "cnes": ("comb", 31.4, 140.6, 7, 101.0, 114.1),
    "nome_fantasia": ("text", (221.5, 99.1, 556.3, 115.9), 6),
    "op_INCLUSAO": ("check", (282.5, 74.1, 298.6, 84.4)),
    "op_ALTERACAO": ("check", (416.8, 73.8, 432.7, 83.4)),
    "op_EXCLUSAO": ("check", (541.8, 73.9, 557.5, 83.8)),
    "nome": ("text", (21.3, 130.4, 572.6, 147.4), 6),
}

# ----------------------------------------------------------------------------
# Ficha 20 - Cadastro de Profissional
# ----------------------------------------------------------------------------
_DIG = (217.6, 240.2)  # linha de dígitos de PIS/CPF/CNS

FICHA20 = {
    "cad_SUS": ("check", (444.1, 136.4, 458.5, 146.2)),
    "cad_NAO_SUS": ("check", (501.4, 136.4, 516.1, 146.2)),
    "nome": ("text", (26.3, 164.4, 565.8, 197.8), 8),
    "pis": ("comb", 33.7, 158.4, 11, *_DIG),
    "cpf": ("comb", 178.1, 302.9, 11, *_DIG),
    "cns": ("comb", 325.0, 495.1, 15, *_DIG),
    "sexo_M": ("check", (516.9, 222.7, 527.3, 236.0)),
    "sexo_F": ("check", (540.2, 222.7, 550.8, 236.0)),
    "mae": ("text", (26.3, 254.0, 565.8, 282.5), 8),
    "pai": ("text", (27.1, 291.5, 566.5, 308.5), 6),
    "data_nasc": ("comb", 30.2, 114.1, 8, 332.2, 344.2),
    "mun_nasc": ("text", (138.0, 323.6, 352.8, 345.4), 8),
    "ibge_nasc": ("comb", 374.6, 453.9, 7, 332.2, 344.2),
    "uf_nasc": ("comb", 478.6, 499.6, 2, 330.7, 342.8),
    "raca_cor": ("center", (527.9, 329.8, 549.8, 342.8)),
    "cert_tipo": ("center", (52.1, 365.6, 76.0, 380.0)),
    "cartorio": ("text", (106.6, 361.0, 565.1, 383.5), 8),
    "livro": ("comb", 29.2, 119.9, 8, 406.5, 420.3),
    "fls": ("comb", 134.1, 172.6, 4, 406.5, 420.3),
    "termo": ("comb", 186.8, 277.5, 8, 406.2, 420.3),
    "cert_data": ("comb", 292.9, 383.5, 8, 406.5, 420.3),
    "rg_num": ("comb", 398.9, 557.6, 14, 406.5, 420.3),
    "rg_uf": ("comb", 38.0, 60.7, 2, 444.2, 456.5),
    "rg_orgao": ("text", (81.2, 435.6, 195.8, 461.1), 8),
    "rg_data": ("comb", 217.0, 303.2, 8, 445.8, 458.0),
    "nac_B": ("check", (342.6, 442.0, 352.3, 448.0)),
    "nac_E": ("check", (342.6, 450.2, 352.3, 456.0)),
    "pais_origem": ("comb", 467.0, 539.0, 4, 445.4, 459.5),
    "data_entrada": ("comb", 32.8, 123.5, 8, 482.5, 495.5),
    "data_naturalizacao": ("comb", 136.0, 226.6, 8, 482.4, 495.5),
    "portaria": ("text", (234.7, 473.0, 303.5, 499.1), 8),
    "titulo": ("comb", 310.0, 446.0, 12, 483.2, 497.0),
    "zona": ("comb", 462.5, 496.4, 3, 482.4, 495.5),
    "secao": ("comb", 514.1, 559.4, 4, 481.2, 495.8),
    "ctps_num": ("comb", 37.1, 116.5, 7, 527.0, 545.2),
    "ctps_serie": ("comb", 128.8, 185.5, 5, 527.0, 545.2),
    "ctps_uf": ("comb", 198.4, 221.1, 2, 527.8, 545.2),
    "ctps_data": ("comb", 234.8, 321.0, 8, 526.4, 543.8),
    "escolaridade": ("comb", 335.1, 371.1, 2, 524.2, 545.2),
    "sit_conjugal": ("center", (412.0, 526.6, 432.1, 544.3)),
    "freq_S": ("check", (497.0, 529.0, 505.6, 541.0)),
    "freq_N": ("check", (528.5, 529.0, 537.1, 541.0)),
    "tipo_logradouro": ("text", (38.9, 589.0, 126.6, 604.4), 0),
    "logradouro": ("text", (149.5, 584.8, 341.6, 607.7), 8),
    "numero": ("text", (346.8, 582.8, 389.8, 607.2), 8),
    "complemento": ("text", (397.9, 582.3, 474.6, 606.6), 8),
    "bairro": ("text", (479.8, 582.4, 565.1, 606.6), 8),
    "mun_res": ("text", (29.2, 617.6, 149.5, 641.3), 8),
    "ibge_res": ("comb", 155.1, 234.4, 7, 625.1, 639.2),
    "uf_res": ("comb", 271.5, 292.4, 2, 624.5, 640.1),
    "cep": ("comb", 311.6, 402.3, 8, 625.9, 639.6),
    "telefone": ("comb", 418.9, 555.0, 12, 625.9, 639.6),
    "banco_cod": ("cells", [30.6, 42.3, 53.8, 68.2], 688.6, 701.7),
    "banco_nome": ("text", (96.0, 685.2, 188.3, 702.7), 0),
    "ag_cod": ("cells", [196.3, 210.6, 225.4, 239.8, 254.2], 689.9, 702.1),
    "ag_nome": ("text", (271.0, 686.0, 403.4, 702.4), 0),
    "conta": ("cells", [409.4, 422.5, 433.3, 444.8, 455.5, 466.2, 476.9, 488.5, 499.1,
                        509.9, 520.6, 531.3, 542.8, 553.6, 563.5], 689.0, 702.0),
}

# ----------------------------------------------------------------------------
# Ficha 21 - bloco de vínculo (coordenadas do 1º bloco) + deslocamentos dos demais
# ----------------------------------------------------------------------------
_V_ROW = (321.8, 333.8)
VINCULO_BLOCK = {
    # grupo "head"
    "registro": ("head", ("text", (35.2, 186.8, 164.6, 208.2), 7, 10.5)),
    "orgao": ("head", ("text", (227.1, 185.6, 326.9, 206.6), 7, 10.5)),
    "sus_S": ("head", ("check", (433.6, 192.0, 450.3, 201.1))),
    "sus_N": ("head", ("check", (491.3, 192.0, 508.1, 201.1))),
    "vinc_cod": ("head", ("center", (42.5, 225.1, 64.0, 242.9))),
    "vinc_desc": ("head", ("text", (70.4, 224.6, 235.3, 243.3), 0)),
    "tipo_cod": ("head", ("center", (246.7, 224.9, 268.1, 242.8))),
    "tipo_desc": ("head", ("text", (274.5, 224.9, 411.1, 243.7), 0)),
    "sub_cod": ("head", ("center", (422.4, 224.1, 444.9, 242.8))),
    "sub_desc": ("head", ("text", (454.6, 224.1, 558.4, 242.8), 0)),
    # grupo "cbo"
    "cbo_cod": ("cbo", ("center", (42.7, 270.3, 114.7, 293.2))),
    "cbo_desc": ("cbo", ("text", (136.6, 270.5, 384.9, 293.9), 4)),
    # grupo "carga"
    "ch_amb": ("carga", ("center", (408.5, 276.3, 427.3, 293.4))),
    "ch_hosp": ("carga", ("center", (471.2, 276.3, 489.9, 293.4))),
    "ch_outros": ("carga", ("center", (525.5, 276.3, 544.3, 293.4))),
    # grupo "datas"
    "data_entrada": ("datas", ("comb", 44.9, 128.8, 8, *_V_ROW)),
    "data_deslig": ("datas", ("comb", 162.8, 246.7, 8, *_V_ROW)),
    "motivo_cod": ("datas", ("comb", 280.6, 302.7, 2, 323.0, 335.5)),
    "motivo_desc": ("datas", ("text", (304.9, 321.8, 496.1, 336.7), 0)),
}

# (dx, dy) por bloco (0, 1, 2) e por grupo
VINCULO_OFFSETS = {
    0: {"head": (0, 0), "cbo": (0, 0), "carga": (0, 0), "datas": (0, 0)},
    1: {"head": (-1.8, 181.4), "cbo": (-1.8, 175.7), "carga": (-1.8, 170.7), "datas": (-1.8, 175.2)},
    2: {"head": (-0.4, 351.5), "cbo": (-0.5, 346.7), "carga": (-0.4, 341.9), "datas": (-0.4, 347.1)},
}
VINCULOS_POR_PAGINA = 3


def _shift(spec: tuple, dx: float, dy: float) -> tuple:
    kind = spec[0]
    if kind in ("text", "center", "check"):
        x0, t, x1, b = spec[1]
        new_box = (x0 + dx, t + dy, x1 + dx, b + dy)
        return (kind, new_box) + tuple(spec[2:])
    if kind == "comb":
        _, first, last, n, yt, yb = spec
        return ("comb", first + dx, last + dx, n, yt + dy, yb + dy)
    if kind == "cells":
        _, xs, yt, yb = spec
        return ("cells", [x + dx for x in xs], yt + dy, yb + dy)
    raise ValueError(kind)


def vinculo_fields(block: int) -> dict[str, tuple]:
    """Campos de um bloco de vínculo (0, 1 ou 2) na Ficha 21."""
    out = {}
    for key, (group, spec) in VINCULO_BLOCK.items():
        dx, dy = VINCULO_OFFSETS[block][group]
        out[key] = _shift(spec, dx, dy)
    return out
