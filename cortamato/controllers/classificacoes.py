"""Classificações individuais, por escalão/sexo, coletivas e apuramentos."""

from __future__ import annotations

from ..models import repos_prova
from ..models.entidades import ClassificacaoColetiva, ClassificacaoIndividual
from ..models.repos_cadastro import obter_configuracao
from .base import P_CLASSIFICACOES, ControladorBase, requer


def _rotulo_sexo(sexo: str) -> str:
    return "Masculino" if sexo == "M" else "Feminino"


class ControladorClassificacoes(ControladorBase):
    # ------------------------------------------------------------------
    # Classificação geral
    # ------------------------------------------------------------------
    @requer(P_CLASSIFICACOES)
    def geral(self) -> list[ClassificacaoIndividual]:
        linhas = repos_prova.resultados_validos(self.bd)
        resultado = []
        for posicao, linha in enumerate(linhas, start=1):
            resultado.append(
                ClassificacaoIndividual(
                    ordem=posicao,
                    dorsal=int(linha["dorsal"]),
                    aluno=linha["aluno"],
                    turma=linha["turma"] or "—",
                    escalao=linha["escalao"],
                    sexo=_rotulo_sexo(linha["sexo"]),
                )
            )
        return resultado

    # ------------------------------------------------------------------
    # Classificação por escalão/sexo (com apuramento)
    # ------------------------------------------------------------------
    @requer(P_CLASSIFICACOES)
    def por_escalao(self) -> list[dict]:
        grupos: dict[tuple, list[dict]] = {}
        for linha in repos_prova.resultados_validos(self.bd):
            chave = (linha["idade_min"], linha["escalao"], linha["sexo"])
            grupos.setdefault(chave, []).append(linha)

        resultado = []
        for chave in sorted(grupos):
            itens = grupos[chave]
            limite = self._limite_apurados(itens[0])
            linhas = []
            for posicao, item in enumerate(itens, start=1):
                linhas.append(
                    ClassificacaoIndividual(
                        ordem=posicao,
                        dorsal=int(item["dorsal"]),
                        aluno=item["aluno"],
                        turma=item["turma"] or "—",
                        escalao=item["escalao"],
                        sexo=_rotulo_sexo(item["sexo"]),
                        apurado=posicao <= limite,
                    )
                )
            resultado.append({
                "grupo": f"{itens[0]['escalao']} — {_rotulo_sexo(itens[0]['sexo'])}",
                "limite": limite,
                "linhas": linhas,
            })
        return resultado

    def _limite_apurados(self, linha: dict) -> int:
        apurados = linha.get("apurados") or 0
        if int(apurados) > 0:
            return int(apurados)
        try:
            return int(obter_configuracao(self.bd, "apurados_por_escalao", "6"))
        except ValueError:
            return 6

    # ------------------------------------------------------------------
    # Classificação coletiva (por turma)
    # ------------------------------------------------------------------
    @requer(P_CLASSIFICACOES)
    def coletiva(self) -> list[ClassificacaoColetiva]:
        linhas = repos_prova.resultados_validos(self.bd)
        try:
            melhores = int(obter_configuracao(self.bd, "pontos_coletiva", "4"))
        except ValueError:
            melhores = 4
        melhores = max(1, melhores)

        # Posição de cada participante dentro do respetivo escalão/sexo
        grupos: dict[tuple, list[dict]] = {}
        for linha in linhas:
            grupos.setdefault((linha["escalao"], linha["sexo"]), []).append(linha)
        posicoes: dict[int, int] = {}
        for itens in grupos.values():
            for posicao, item in enumerate(itens, start=1):
                posicoes[int(item["participacao_id"])] = posicao

        por_turma: dict[str, list[tuple[int, str]]] = {}
        for linha in linhas:
            turma = linha["turma"] or "Sem turma"
            pontos = posicoes.get(int(linha["participacao_id"]), 0)
            por_turma.setdefault(turma, []).append((pontos, linha["aluno"]))

        classificacao: list[ClassificacaoColetiva] = []
        for turma, registos in por_turma.items():
            registos.sort()
            considerados = registos[:melhores]
            total = sum(pontos for pontos, _ in considerados)
            detalhe = ", ".join(f"{nome} ({pontos}º)" for pontos, nome in considerados)
            classificacao.append(
                ClassificacaoColetiva(
                    posicao=0,
                    turma=turma,
                    total_pontos=total,
                    classificados=len(registos),
                    detalhe=detalhe,
                )
            )

        classificacao.sort(key=lambda item: (item.total_pontos, -item.classificados))
        for posicao, item in enumerate(classificacao, start=1):
            item.posicao = posicao
        return classificacao

    # ------------------------------------------------------------------
    # Apurados e estatísticas
    # ------------------------------------------------------------------
    @requer(P_CLASSIFICACOES)
    def apurados(self) -> list[dict]:
        resultado: list[dict] = []
        for grupo in self.por_escalao():
            for linha in grupo["linhas"]:
                if linha.apurado:
                    resultado.append({
                        "grupo": grupo["grupo"],
                        "posicao": linha.ordem,
                        "dorsal": linha.dorsal,
                        "aluno": linha.aluno,
                        "turma": linha.turma,
                    })
        return resultado

    @requer(P_CLASSIFICACOES)
    def estatisticas(self) -> dict[str, int]:
        participantes = repos_prova.contar_participacoes(self.bd)
        chegadas = repos_prova.contar_chegadas(self.bd)
        desistentes = repos_prova.contar_estado_participacao(self.bd, "desistente")
        desclassificados = repos_prova.contar_estado_participacao(self.bd, "desclassificado")
        cobertura = int(round(chegadas * 100 / participantes)) if participantes else 0
        return {
            "participantes": participantes,
            "chegadas": chegadas,
            "desistentes": desistentes,
            "desclassificados": desclassificados,
            "cobertura": cobertura,
        }
