"""Entidades de domínio usadas pelos controladores de classificação."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ClassificacaoIndividual:
    ordem: int
    dorsal: int
    aluno: str
    turma: str
    escalao: str
    sexo: str
    apurado: bool = False
    estado: str = "Classificado"


@dataclass
class ClassificacaoColetiva:
    posicao: int
    turma: str
    total_pontos: int
    classificados: int
    detalhe: str


@dataclass
class ParticipanteProva:
    inscricao_id: int
    aluno_id: int
    nome: str
    sexo: str
    turma: str
    escalao: str
    estado: str
    escalao_id: int | None = None
    dorsal: int | None = None
    chegada_ordem: int | None = None
