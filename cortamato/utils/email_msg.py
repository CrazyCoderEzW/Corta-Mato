

from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

from .datas import agora_texto

PASTA_COMUNICACOES = Path(__file__).resolve().parents[2] / "comunicacoes"


def construir_mensagem(atividade: str, data_prova: str, por_turma: dict[str, dict],
                       participacao_texto: str = "Participante na prova",
                       organizacao_texto: str = "Elemento de apoio à organização") -> str:
    """Compõe o corpo do e-mail agrupado por turma.

    por_turma = {
        "10A": {"dt": "Prof. X", "email": "x@aepbs.pt",
                "participantes": ["Nome 1"], "organizacao": ["Nome 2"]},
    }
    """
    linhas: list[str] = [
        f"Assunto: Justificação de faltas — {atividade} ({data_prova})",
        "",
        "Exmos. Senhores Diretores de Turma,",
        "",
        f"No âmbito da atividade {atividade}, realizada a {data_prova}, solicita-se a "
        "justificação das faltas dos alunos abaixo identificados.",
        "",
    ]

    if not por_turma:
        linhas.append("(Sem registos de alunos a comunicar.)")
        return "\n".join(linhas)

    for turma in sorted(por_turma):
        dados = por_turma[turma]
        linhas.append(f"Turma {turma}" + (f" — DT: {dados.get('dt')}" if dados.get("dt") else ""))
        for nome in sorted(dados.get("participantes", [])):
            linhas.append(f"   - {nome} ({participacao_texto})")
        for nome in sorted(dados.get("organizacao", [])):
            linhas.append(f"   - {nome} ({organizacao_texto})")
        linhas.append("")

    linhas.extend([
        "Com os melhores cumprimentos,",
        "A organização do Corta-Mato",
        "",
        f"Mensagem preparada pelo sistema em {agora_texto()}.",
    ])
    return "\n".join(linhas)


def guardar_eml(assunto: str, corpo: str, destinatarios: list[str],
                remetente: str, nome_ficheiro: str = "comunicacao_dt") -> Path:
    PASTA_COMUNICACOES.mkdir(parents=True, exist_ok=True)
    mensagem = EmailMessage()
    mensagem["Subject"] = assunto
    mensagem["From"] = remetente or "direcao@aepbs.pt"
    mensagem["To"] = ", ".join(destinatarios) if destinatarios else "direcao@aepbs.pt"
    mensagem.set_content(corpo)
    destino = PASTA_COMUNICACOES / f"{nome_ficheiro}.eml"
    destino.write_bytes(mensagem.as_bytes())
    return destino


def guardar_texto(corpo: str, nome_ficheiro: str = "comunicacao_dt") -> Path:
    PASTA_COMUNICACOES.mkdir(parents=True, exist_ok=True)
    destino = PASTA_COMUNICACOES / f"{nome_ficheiro}.txt"
    destino.write_text(corpo, encoding="utf-8")
    return destino
