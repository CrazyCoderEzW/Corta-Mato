"""Secretariado de partida: entrega de dorsais e listas de partida."""

from __future__ import annotations

from ..models import repos_inscricoes, repos_prova
from .base import P_PARTIDA, ControladorBase, ErroValidacao, requer


class ControladorPartida(ControladorBase):
    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def listar_participantes(self) -> list[dict]:
        return repos_prova.listar_participantes(self.bd)

    def listas_de_partida(self) -> list[dict]:
        return repos_prova.listas_de_partida(self.bd)

    def inscritos_sem_dorsal(self) -> list[dict]:
        return repos_inscricoes.inscritos_sem_dorsal(self.bd)

    def proximo_dorsal(self) -> int:
        return repos_prova.proximo_dorsal(self.bd, self._config_inteiro("dorsais_inicio", 1))

    def total_dorsais(self) -> int:
        return repos_prova.contar_participacoes(self.bd)

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------
    @requer(P_PARTIDA)
    def entregar_dorsal(self, inscricao_id: int, dorsal_texto: str) -> dict:
        if not inscricao_id:
            raise ErroValidacao("Selecione o participante.")
        inscricao = repos_inscricoes.obter_inscricao(self.bd, int(inscricao_id))
        if not inscricao:
            raise ErroValidacao("Inscrição inexistente.")
        if inscricao["estado"] == "organizacao":
            raise ErroValidacao(
                "Este elemento está inscrito como organização e não recebe dorsal de prova."
            )
        if repos_prova.participacao_da_inscricao(self.bd, int(inscricao_id)):
            raise ErroValidacao("Este inscrito já tem um dorsal atribuído.")

        texto = str(dorsal_texto or "").strip()
        if texto:
            if not texto.isdigit():
                raise ErroValidacao("O dorsal deve ser um número inteiro.")
            dorsal = int(texto)
            if dorsal <= 0:
                raise ErroValidacao("O dorsal deve ser um número positivo.")
        else:
            dorsal = self.proximo_dorsal()

        if repos_prova.dorsal_em_uso(self.bd, dorsal):
            raise ErroValidacao(f"O dorsal {dorsal} já está atribuído a outro participante.")

        participacao_id = repos_prova.criar_participacao(
            self.bd, int(inscricao_id), dorsal, self._id_utilizador()
        )
        repos_inscricoes.atualizar_inscricao(
            self.bd, int(inscricao_id), inscricao["escalao_id"], "participante",
            inscricao.get("observacoes") or "",
        )
        return {"participacao_id": participacao_id, "dorsal": dorsal,
                "aluno": inscricao["aluno"], "turma": inscricao.get("turma") or ""}

    @requer(P_PARTIDA)
    def cancelar_participacao(self, participacao_id: int) -> None:
        participacao = repos_prova.obter_participacao(self.bd, int(participacao_id))
        if not participacao:
            raise ErroValidacao("Participação inexistente.")
        if repos_prova.obter_chegada_por_participacao(self.bd, int(participacao_id)):
            raise ErroValidacao(
                "Já existem registos de meta para este dorsal. Corrija primeiro a meta."
            )
        repos_prova.apagar_participacao(self.bd, int(participacao_id))
        repos_inscricoes.atualizar_inscricao(
            self.bd, int(participacao["inscricao_id"]), participacao.get("escalao_id"),
            "inscrito", "",
        )
