

from __future__ import annotations

import csv
import os
from pathlib import Path

from .datas import agora_texto
from .pdf import PDFSimples

PASTA_EXPORTACOES = Path(__file__).resolve().parents[2] / "exportacoes"


def _preparar_destino(nome: str, extensao: str) -> Path:
    PASTA_EXPORTACOES.mkdir(parents=True, exist_ok=True)
    base = "".join(caractere if caractere.isalnum() or caractere in "-_" else "-" for caractere in nome)
    return PASTA_EXPORTACOES / f"{base}.{extensao}"


def exportar_csv(nome: str, cabecalho: list[str], registos: list[list]) -> Path:
    destino = _preparar_destino(nome, "csv")
    with destino.open("w", encoding="utf-8-sig", newline="") as ficheiro:
        escritor = csv.writer(ficheiro, delimiter=";")
        escritor.writerow(cabecalho)
        for registo in registos:
            escritor.writerow(registo)
    return destino


def exportar_pdf(nome: str, titulo: str, subtitulo: str, cabecalho: list[str],
                 registos: list[list], larguras: list[float],
                 resumo: list[str] | None = None) -> Path:
    documento = PDFSimples(titulo=titulo)
    documento.titulo_principal(titulo)
    if subtitulo:
        documento.texto(subtitulo, 10, False, 18)
    documento.texto(f"Gerado em {agora_texto()}", 8, False, 16)
    for linha in resumo or []:
        documento.texto(linha, 9, False, 14)
    if resumo:
        documento.espaco(6)
    documento.tabela(cabecalho, registos, larguras)
    return documento.guardar(_preparar_destino(nome, "pdf"))


def abrir_ficheiro(caminho: str | Path) -> bool:
    """Abre o ficheiro exportado com a aplicação predefinida do sistema."""
    try:
        os.startfile(str(caminho))  # type: ignore[attr-defined]
        return True
    except Exception:
        return False
