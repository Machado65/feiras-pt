#!/usr/bin/env python3
"""Valida feiras.json e gera os calendários em português e em inglês (só biblioteca padrão).

Uso:
  python3 gerar_ics.py              valida e gera _site/feiras.ics (PT) e _site/fairs.ics (EN)
  python3 gerar_ics.py --formatar   idem, e reescreve feiras.json ordenado e normalizado
  python3 gerar_ics.py --listar     valida e lista as feiras por ordem de data
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DADOS = RAIZ / "feiras.json"
SITE = RAIZ / "_site"

CATEGORIAS = ["medieval", "gastronomia", "vinho", "natal", "artesanato", "tradicional"]
OBRIGATORIOS = ["id", "nome", "nome_en", "categoria", "inicio", "fim", "confirmado",
                "cidade", "distrito", "descricao", "descricao_en", "url", "fonte", "atualizado"]
OPCIONAIS = ["local", "nota", "nota_en", "estado"]
# Ordem das chaves em cada entrada quando o ficheiro é reescrito com --formatar.
ORDEM = ["id", "nome", "nome_en", "categoria", "inicio", "fim", "confirmado", "estado",
         "local", "cidade", "distrito", "descricao", "descricao_en", "nota", "nota_en",
         "url", "fonte", "atualizado"]
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-(\d{4})$")
MAX_DIAS = 120  # nenhuma feira dura mais do que isto; apanha datas trocadas

# Tudo o que muda entre o calendário português e o inglês.
IDIOMAS = {
    "pt": {
        "ficheiro": "feiras.ics",
        "uid": "{}@machado65.github.io",
        "nome_cal": "Feiras PT",
        "desc_cal": "Feiras tradicionais e gastronómicas em Portugal, revistas todos os meses.",
        "campos": ("nome", "descricao", "nota"),
        "categorias": {"medieval": "Medieval", "gastronomia": "Gastronomia", "vinho": "Vinho",
                       "natal": "Natal", "artesanato": "Artesanato", "tradicional": "Tradicional"},
        "a_confirmar": " (a confirmar)",
        "cancelada": "CANCELADA: ",
        "datas_por_confirmar": "Datas por confirmar.",
        "nome_original": None,
        "mais_info": "Mais informação: {}",
        "fonte": "Fonte das datas: {}",
        "atualizado": "Atualizado a {}.",
    },
    "en": {
        "ficheiro": "fairs.ics",
        "uid": "{}-en@machado65.github.io",
        "nome_cal": "Portugal Fairs",
        "desc_cal": "Traditional fairs, food and wine festivals, medieval fairs and Christmas "
                    "markets across Portugal, reviewed every month.",
        "campos": ("nome_en", "descricao_en", "nota_en"),
        "categorias": {"medieval": "Medieval", "gastronomia": "Food", "vinho": "Wine",
                       "natal": "Christmas", "artesanato": "Crafts", "tradicional": "Traditional"},
        "a_confirmar": " (TBC)",
        "cancelada": "CANCELLED: ",
        "datas_por_confirmar": "Dates to be confirmed.",
        "nome_original": "Portuguese name: {}",
        "mais_info": "More information: {}",
        "fonte": "Source for the dates: {}",
        "atualizado": "Updated {}.",
    },
}


def ler_data(valor, campo, ref, erros):
    try:
        return dt.date.fromisoformat(valor)
    except (TypeError, ValueError):
        erros.append(f"{ref}: '{campo}' tem de ser uma data AAAA-MM-DD (está {valor!r})")
        return None


def validar_campos(f, ref, erros):
    for campo in OBRIGATORIOS:
        if campo not in f:
            erros.append(f"{ref}: falta o campo '{campo}'")
    desconhecidos = sorted(set(f) - set(OBRIGATORIOS) - set(OPCIONAIS))
    if desconhecidos:
        erros.append(f"{ref}: campos desconhecidos {desconhecidos}")
    for campo in ORDEM:
        if campo in f and campo != "confirmado":
            if not isinstance(f[campo], str) or not f[campo].strip():
                erros.append(f"{ref}: '{campo}' tem de ser texto não vazio")
    if "confirmado" in f and not isinstance(f["confirmado"], bool):
        erros.append(f"{ref}: 'confirmado' tem de ser true ou false")
    if f.get("confirmado") is False and not f.get("nota"):
        erros.append(f"{ref}: uma entrada por confirmar precisa de 'nota' a dizer de onde vêm as datas")
    if ("nota" in f) != ("nota_en" in f):
        erros.append(f"{ref}: 'nota' e 'nota_en' existem as duas ou nenhuma")
    if "categoria" in f and f["categoria"] not in CATEGORIAS:
        erros.append(f"{ref}: categoria '{f['categoria']}' inválida; usa uma de {CATEGORIAS}")
    if "estado" in f and f["estado"] != "cancelada":
        erros.append(f"{ref}: 'estado' só pode ser \"cancelada\" (ou não existir)")
    for campo in ("url", "fonte"):
        valor = f.get(campo)
        if isinstance(valor, str) and not valor.startswith(("https://", "http://")):
            erros.append(f"{ref}: '{campo}' tem de ser um URL http(s)")


def validar_datas(f, ref, erros):
    inicio = ler_data(f["inicio"], "inicio", ref, erros) if "inicio" in f else None
    fim = ler_data(f["fim"], "fim", ref, erros) if "fim" in f else None
    if "atualizado" in f:
        ler_data(f["atualizado"], "atualizado", ref, erros)
    if inicio and fim:
        if fim < inicio:
            erros.append(f"{ref}: 'fim' ({fim}) é antes de 'inicio' ({inicio})")
        elif (fim - inicio).days + 1 > MAX_DIAS:
            erros.append(f"{ref}: dura mais de {MAX_DIAS} dias; confirma as datas")
    return inicio


def validar_id(f, ref, inicio, vistos, erros):
    fid = f.get("id")
    if not isinstance(fid, str):
        return
    m = ID_RE.match(fid)
    if not m:
        erros.append(f"{ref}: id inválido; usa minúsculas sem acentos, números e hífenes, "
                     "a acabar no ano (ex.: feira-do-fumeiro-vinhais-2027)")
    elif inicio and int(m.group(1)) != inicio.year:
        erros.append(f"{ref}: o id tem de acabar no ano de 'inicio' ({inicio.year})")
    if fid in vistos:
        erros.append(f"{ref}: id repetido")
    vistos.add(fid)


def validar(dados) -> list[str]:
    if not isinstance(dados, dict) or not isinstance(dados.get("feiras"), list):
        return ['o ficheiro tem de ser um objeto {"feiras": [...]}']
    erros = []
    if set(dados) != {"feiras"}:
        erros.append(f"chaves a mais no topo do ficheiro: {sorted(set(dados) - {'feiras'})}")
    vistos = set()
    for i, f in enumerate(dados["feiras"]):
        if not isinstance(f, dict):
            erros.append(f"feiras[{i}]: tem de ser um objeto")
            continue
        ref = f"feiras[{i}] ({f.get('id', 'sem id')})"
        validar_campos(f, ref, erros)
        inicio = validar_datas(f, ref, erros)
        validar_id(f, ref, inicio, vistos, erros)
    return erros


def ordenar(feiras):
    return sorted(feiras, key=lambda f: (f["inicio"], f["fim"], f["id"]))


def escapar(texto: str) -> str:
    """Escapa um valor TEXT do iCalendar (RFC 5545, 3.3.11)."""
    return (texto.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
            .replace("\r\n", "\n").replace("\n", "\\n"))


def dobrar(linha: str) -> str:
    """Parte linhas com mais de 75 octetos sem cortar caracteres UTF-8 nem escapes (\\,) a meio."""
    partes, atual, tamanho = [], "", 0
    for pedaco in re.findall(r"\\.|.", linha, flags=re.DOTALL):
        n = len(pedaco.encode("utf-8"))
        if tamanho + n > 75:
            partes.append(atual)
            atual, tamanho = " " + pedaco, 1 + n
        else:
            atual += pedaco
            tamanho += n
    partes.append(atual)
    return "\r\n".join(partes)


def titulo(f, t) -> str:
    nome = f[t["campos"][0]]
    texto = nome
    if f["cidade"].casefold() not in nome.casefold():
        texto += f" · {f['cidade']}"
    if not f["confirmado"]:
        texto += t["a_confirmar"]
    if f.get("estado") == "cancelada":
        texto = t["cancelada"] + texto
    return texto


def descricao(f, t) -> str:
    _, campo_desc, campo_nota = t["campos"]
    blocos = [f[campo_desc]]
    if not f["confirmado"]:
        blocos.append(f"{t['datas_por_confirmar']} {f[campo_nota]}")
    elif f.get(campo_nota):
        blocos.append(f[campo_nota])
    linhas = []
    if t["nome_original"]:
        linhas.append(t["nome_original"].format(f["nome"]))
    linhas.append(t["mais_info"].format(f["url"]))
    if f["fonte"] != f["url"]:
        linhas.append(t["fonte"].format(f["fonte"]))
    linhas.append(t["atualizado"].format(f["atualizado"]))
    blocos.append("\n".join(linhas))
    return "\n\n".join(blocos)


def evento(f, t) -> list[str]:
    inicio = dt.date.fromisoformat(f["inicio"])
    fim_exclusivo = dt.date.fromisoformat(f["fim"]) + dt.timedelta(days=1)
    carimbo = dt.date.fromisoformat(f["atualizado"]).strftime("%Y%m%dT000000Z")
    sitio = [f.get("local"), f["cidade"]]
    if f["distrito"].casefold() not in f["cidade"].casefold():
        sitio.append(f["distrito"])
    sitio.append("Portugal")
    if f.get("estado") == "cancelada":
        estado = "CANCELLED"
    else:
        estado = "CONFIRMED" if f["confirmado"] else "TENTATIVE"
    return [
        "BEGIN:VEVENT",
        f"UID:{t['uid'].format(f['id'])}",
        f"DTSTAMP:{carimbo}",
        f"LAST-MODIFIED:{carimbo}",
        f"DTSTART;VALUE=DATE:{inicio:%Y%m%d}",
        f"DTEND;VALUE=DATE:{fim_exclusivo:%Y%m%d}",
        f"SUMMARY:{escapar(titulo(f, t))}",
        f"LOCATION:{escapar(', '.join(s for s in sitio if s))}",
        f"DESCRIPTION:{escapar(descricao(f, t))}",
        f"URL:{f['url']}",
        f"CATEGORIES:{t['categorias'][f['categoria']]}",
        f"STATUS:{estado}",
        "TRANSP:TRANSPARENT",
        "END:VEVENT",
    ]


def gerar(feiras, t) -> str:
    linhas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Machado65//Feiras PT//PT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escapar(t['nome_cal'])}",
        f"X-WR-CALDESC:{escapar(t['desc_cal'])}",
        "X-WR-TIMEZONE:Europe/Lisbon",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
    ]
    for f in ordenar(feiras):
        linhas.extend(evento(f, t))
    linhas.append("END:VCALENDAR")
    return "".join(dobrar(linha) + "\r\n" for linha in linhas)


def listar(feiras) -> None:
    pt = IDIOMAS["pt"]
    for f in ordenar(feiras):
        marca = "" if f["confirmado"] else "  (a confirmar)"
        if f.get("estado") == "cancelada":
            marca += "  CANCELADA"
        nome = titulo({**f, "confirmado": True, "estado": None}, pt)
        print(f"{f['inicio']} → {f['fim']}  {nome}  [{f['categoria']}]{marca}")
    print(f"\n{len(feiras)} feiras, {sum(not f['confirmado'] for f in feiras)} por confirmar.")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--formatar", action="store_true", help="reescreve feiras.json ordenado e normalizado")
    p.add_argument("--listar", action="store_true", help="lista as feiras em vez de gerar os calendários")
    args = p.parse_args()

    try:
        dados = json.loads(DADOS.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"feiras.json não é JSON válido: {e}", file=sys.stderr)
        return 1
    erros = validar(dados)
    if erros:
        print(f"feiras.json tem {len(erros)} erro(s):", file=sys.stderr)
        for erro in erros:
            print(f"  - {erro}", file=sys.stderr)
        return 1
    feiras = dados["feiras"]

    if args.listar:
        listar(feiras)
        return 0
    if args.formatar:
        normalizadas = [{k: f[k] for k in ORDEM if k in f} for f in ordenar(feiras)]
        DADOS.write_text(json.dumps({"feiras": normalizadas}, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    SITE.mkdir(exist_ok=True)
    for t in IDIOMAS.values():
        (SITE / t["ficheiro"]).write_text(gerar(feiras, t), encoding="utf-8", newline="")
    print(f"{len(feiras)} feiras → _site/{IDIOMAS['pt']['ficheiro']} e _site/{IDIOMAS['en']['ficheiro']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
