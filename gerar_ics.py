#!/usr/bin/env python3
"""Valida feiras.json e gera o calendário _site/feiras.ics (só biblioteca padrão).

Uso:
  python3 gerar_ics.py              valida e gera _site/feiras.ics
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
SAIDA = RAIZ / "_site" / "feiras.ics"

CATEGORIAS = {
    "medieval": "Medieval",
    "gastronomia": "Gastronomia",
    "vinho": "Vinho",
    "natal": "Natal",
    "artesanato": "Artesanato",
    "tradicional": "Tradicional",
}
OBRIGATORIOS = ["id", "nome", "categoria", "inicio", "fim", "confirmado",
                "cidade", "distrito", "descricao", "url", "fonte", "atualizado"]
OPCIONAIS = ["local", "nota", "estado"]
# Ordem das chaves em cada entrada quando o ficheiro é reescrito com --formatar.
ORDEM = ["id", "nome", "categoria", "inicio", "fim", "confirmado", "estado", "local",
         "cidade", "distrito", "descricao", "nota", "url", "fonte", "atualizado"]
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-(\d{4})$")
MAX_DIAS = 120  # nenhuma feira dura mais do que isto; apanha datas trocadas


def ler_data(valor, campo, ref, erros):
    try:
        return dt.date.fromisoformat(valor)
    except (TypeError, ValueError):
        erros.append(f"{ref}: '{campo}' tem de ser uma data AAAA-MM-DD (está {valor!r})")
        return None


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
        if "categoria" in f and f["categoria"] not in CATEGORIAS:
            erros.append(f"{ref}: categoria '{f['categoria']}' inválida; usa uma de {sorted(CATEGORIAS)}")
        if "estado" in f and f["estado"] != "cancelada":
            erros.append(f"{ref}: 'estado' só pode ser \"cancelada\" (ou não existir)")
        for campo in ("url", "fonte"):
            valor = f.get(campo)
            if isinstance(valor, str) and not valor.startswith(("https://", "http://")):
                erros.append(f"{ref}: '{campo}' tem de ser um URL http(s)")
        inicio = ler_data(f["inicio"], "inicio", ref, erros) if "inicio" in f else None
        fim = ler_data(f["fim"], "fim", ref, erros) if "fim" in f else None
        if "atualizado" in f:
            ler_data(f["atualizado"], "atualizado", ref, erros)
        if inicio and fim:
            if fim < inicio:
                erros.append(f"{ref}: 'fim' ({fim}) é antes de 'inicio' ({inicio})")
            elif (fim - inicio).days + 1 > MAX_DIAS:
                erros.append(f"{ref}: dura mais de {MAX_DIAS} dias; confirma as datas")
        fid = f.get("id")
        if isinstance(fid, str):
            m = ID_RE.match(fid)
            if not m:
                erros.append(f"{ref}: id inválido; usa minúsculas sem acentos, números e hífenes, "
                             "a acabar no ano (ex.: feira-do-fumeiro-vinhais-2027)")
            elif inicio and int(m.group(1)) != inicio.year:
                erros.append(f"{ref}: o id tem de acabar no ano de 'inicio' ({inicio.year})")
            if fid in vistos:
                erros.append(f"{ref}: id repetido")
            vistos.add(fid)
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


def titulo(f) -> str:
    texto = f["nome"]
    if f["cidade"].casefold() not in f["nome"].casefold():
        texto += f" · {f['cidade']}"
    if not f["confirmado"]:
        texto += " (a confirmar)"
    if f.get("estado") == "cancelada":
        texto = "CANCELADA: " + texto
    return texto


def descricao(f) -> str:
    blocos = [f["descricao"]]
    if not f["confirmado"]:
        blocos.append(f"Datas por confirmar. {f['nota']}")
    elif f.get("nota"):
        blocos.append(f["nota"])
    links = [f"Mais informação: {f['url']}"]
    if f["fonte"] != f["url"]:
        links.append(f"Fonte das datas: {f['fonte']}")
    links.append(f"Atualizado a {f['atualizado']}.")
    blocos.append("\n".join(links))
    return "\n\n".join(blocos)


def evento(f) -> list[str]:
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
        f"UID:{f['id']}@machado65.github.io",
        f"DTSTAMP:{carimbo}",
        f"LAST-MODIFIED:{carimbo}",
        f"DTSTART;VALUE=DATE:{inicio:%Y%m%d}",
        f"DTEND;VALUE=DATE:{fim_exclusivo:%Y%m%d}",
        f"SUMMARY:{escapar(titulo(f))}",
        f"LOCATION:{escapar(', '.join(s for s in sitio if s))}",
        f"DESCRIPTION:{escapar(descricao(f))}",
        f"URL:{f['url']}",
        f"CATEGORIES:{CATEGORIAS[f['categoria']]}",
        f"STATUS:{estado}",
        "TRANSP:TRANSPARENT",
        "END:VEVENT",
    ]


def gerar(feiras) -> str:
    linhas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Machado65//Feiras PT//PT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Feiras PT",
        f"X-WR-CALDESC:{escapar('Feiras tradicionais e gastronómicas em Portugal, revistas todas as semanas.')}",
        "X-WR-TIMEZONE:Europe/Lisbon",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
    ]
    for f in ordenar(feiras):
        linhas.extend(evento(f))
    linhas.append("END:VCALENDAR")
    return "".join(dobrar(linha) + "\r\n" for linha in linhas)


def listar(feiras) -> None:
    for f in ordenar(feiras):
        marca = "" if f["confirmado"] else "  (a confirmar)"
        if f.get("estado") == "cancelada":
            marca += "  CANCELADA"
        print(f"{f['inicio']} → {f['fim']}  {titulo(f).replace(' (a confirmar)', '')}  "
              f"[{f['categoria']}]{marca}")
    print(f"\n{len(feiras)} feiras, {sum(not f['confirmado'] for f in feiras)} por confirmar.")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--formatar", action="store_true", help="reescreve feiras.json ordenado e normalizado")
    p.add_argument("--listar", action="store_true", help="lista as feiras em vez de gerar o .ics")
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
    SAIDA.parent.mkdir(exist_ok=True)
    SAIDA.write_text(gerar(feiras), encoding="utf-8", newline="")
    print(f"{len(feiras)} feiras → {SAIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
