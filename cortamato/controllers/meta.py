"""Secretariado de meta: registo de chegadas e ocorrências."""

from __future__ import annotations

from ..models import repos_cadastro, repos_inscricoes, repos_prova
from .base import P_META, ControladorBase, ErroValidacao, requer


class ControladorMeta(ControladorBase):
    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def listar_chegadas(self, limite: int = 200) -> list[dict]:
        return repos_prova.listar_chegadas(self.bd, limite)

    def listar_ocorrencias(self) -> list[dict]:
        return repos_prova.listar_ocorrencias(self.bd)

    def proxima_ordem(self) -> int:
        return repos_prova.proxima_ordem(self.bd)

    def ultima_chegada(self) -> dict | None:
        chegadas = repos_prova.listar_chegadas(self.bd, 1)
        return chegadas[0] if chegadas else None

    def resumo(self) -> dict[str, int]:
        return {
            "ordem_seguinte": repos_prova.proxima_ordem(self.bd),
            "chegadas": repos_prova.contar_chegadas(self.bd),
            "participantes": repos_prova.contar_participacoes(self.bd),
            "desistentes": repos_prova.contar_estado_participacao(self.bd, "desistente"),
            "desclassificados": repos_prova.contar_estado_participacao(self.bd, "desclassificado"),
        }

    # ------------------------------------------------------------------
    # Registo de chegadas
    # ------------------------------------------------------------------
    @requer(P_META)
    def registar_por_dorsal(self, dorsal_texto: str, metodo: str = "qr") -> dict:
        texto = str(dorsal_texto or "").strip()
        if not texto.isdigit():
            raise ErroValidacao("Indique um número de dorsal válido.")
        participacao = repos_prova.obter_por_dorsal(self.bd, int(texto))
        if not participacao:
            raise ErroValidacao(f"Não existe nenhum participante com o dorsal {texto}.")
        return self._registar(participacao, metodo)

    @requer(P_META)
    def registar_por_cartao(self, codigo: str, metodo: str = "qr") -> dict:
        """Registo alternativo pela leitura do QRCode do cartão de aluno."""
        codigo = (codigo or "").strip()
        if not codigo:
            raise ErroValidacao("Leia ou introduza o código do cartão de aluno.")
        aluno = repos_cadastro.obter_aluno_por_cartao(self.bd, codigo)
        if not aluno:
            raise ErroValidacao("Cartão de aluno não reconhecido pelo sistema.")
        inscricao = repos_inscricoes.obter_inscricao_do_aluno(self.bd, int(aluno["id"]))
        if not inscricao:
            raise ErroValidacao("O aluno não tem inscrição registada.")
        participacao = repos_prova.participacao_da_inscricao(self.bd, int(inscricao["id"]))
        if not participacao:
            raise ErroValidacao("O dorsal ainda não foi entregue a este aluno.")
        return self._registar(participacao, metodo)

    def _registar(self, participacao: dict, metodo: str) -> dict:
        if participacao["estado"] == "desistente":
            raise ErroValidacao("O participante está registado como desistente.")
        if participacao["estado"] == "desclassificado":
            raise ErroValidacao("O participante está desclassificado.")

        existente = repos_prova.obter_chegada_por_participacao(self.bd, int(participacao["id"]))
        if existente:
            raise ErroValidacao(
                f"O dorsal {participacao['dorsal']} já tem chegada registada "
                f"(ordem {existente['ordem']})."
            )

        ordem = repos_prova.proxima_ordem(self.bd)
        repos_prova.criar_chegada(
            self.bd, int(participacao["id"]), ordem, metodo, self._id_utilizador()
        )
        return {
            "ordem": ordem,
            "dorsal": participacao["dorsal"],
            "aluno": participacao["aluno"],
            "turma": participacao.get("turma") or "—",
            "escalao": participacao.get("escalao") or "—",
        }

    @requer(P_META)
    def desfazer_ultima(self) -> int | None:
        return repos_prova.apagar_ultima_chegada(self.bd)

    @requer(P_META)
    def mover_chegada(self, chegada_id: int, nova_ordem_texto: str) -> None:
        texto = str(nova_ordem_texto or "").strip()
        if not texto.isdigit() or int(texto) < 1:
            raise ErroValidacao("Indique a nova posição (número inteiro positivo).")
        repos_prova.mover_chegada(self.bd, int(chegada_id), int(texto))

    # ------------------------------------------------------------------
    # Ocorrências
    # ------------------------------------------------------------------
    @requer(P_META)
    def registar_desistencia(self, participacao_id: int, motivo: str = "") -> None:
        self._ocorrencia(participacao_id, "desistencia", "desistente", motivo)

    @requer(P_META)
    def registar_desclassificacao(self, participacao_id: int, motivo: str = "") -> None:
        if not (motivo or "").strip():
            raise ErroValidacao("Indique o motivo da desclassificação.")
        self._ocorrencia(participacao_id, "desclassificacao", "desclassificado", motivo)

    def _ocorrencia(self, participacao_id: int, tipo: str, estado: str, motivo: str) -> None:
        participacao = repos_prova.obter_participacao(self.bd, int(participacao_id))
        if not participacao:
            raise ErroValidacao("Participação inexistente.")
        if repos_prova.obter_chegada_por_participacao(self.bd, int(participacao_id)):
            repos_prova.apagar_ultima_chegada(self.bd, int(participacao_id))
        repos_prova.definir_estado_participacao(self.bd, int(participacao_id), estado)
        repos_prova.registar_ocorrencia(
            self.bd, int(participacao_id), tipo, (motivo or "").strip(), self._id_utilizador()
        )

    @requer(P_META)
    def repor_participante(self, participacao_id: int) -> None:
        participacao = repos_prova.obter_participacao(self.bd, int(participacao_id))
        if not participacao:
            raise ErroValidacao("Participação inexistente.")
        repos_prova.definir_estado_participacao(self.bd, int(participacao_id), "entregue")
        repos_prova.registar_ocorrencia(
            self.bd, int(participacao_id), "correcao",
            "Participante reposto como classificado", self._id_utilizador(),
        )
