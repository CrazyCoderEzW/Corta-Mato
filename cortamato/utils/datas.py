

from __future__ import annotations

from datetime import date, datetime

FORMATOS_ENTRADA = ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y")


def hoje_texto() -> str:
    return date.today().strftime("%d/%m/%Y")


def agora_texto() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def converter_data(texto: str) -> date | None:
    """Converte texto em data, aceitando dd/mm/aaaa, dd-mm-aaaa e aaaa-mm-dd."""
    if not texto:
        return None
    limpo = str(texto).strip()
    if not limpo:
        return None
    for formato in FORMATOS_ENTRADA:
        try:
            return datetime.strptime(limpo, formato).date()
        except ValueError:
            continue
    return None


def normalizar_data(texto: str) -> str:
    """Devolve a data no formato ISO (aaaa-mm-dd) ou string vazia se inválida."""
    data = converter_data(texto)
    return data.isoformat() if data else ""


def formatar_data(texto: str | None) -> str:
    """Apresenta uma data ISO no formato português (dd/mm/aaaa)."""
    if not texto:
        return ""
    data = converter_data(str(texto))
    return data.strftime("%d/%m/%Y") if data else str(texto)


def idade_em_ano(data_nascimento: str | None, ano: int) -> int | None:
    """Calcula a idade que o atleta completa no ano de referência da atividade."""
    if not data_nascimento:
        return None
    data = converter_data(str(data_nascimento))
    if data is None:
        return None
    return int(ano) - data.year
