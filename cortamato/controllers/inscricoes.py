"""Secretariado de inscrições: registo, alteração, anulação e consulta."""

from __future__ import annotations

import pymysql

from ..models import repos_cadastro, repos_inscricoes, repos_prova
from ..models.repos_inscricoes import ESTADOS_INSCRICAO, ETIQUETAS_ESTADO
from ..utils import datas
from .base import P_INSCRICOES, ControladorBase, ErroValidacao, requer


class ControladorInscricoes(ControladorBase):
    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def listar(self, pesquisa: str = "", estado: str = "",
               escalao_id: int | None = None) -> list[dict]:
        return repos_inscricoes.listar_inscricoes(self.bd, pesquisa, estado, escalao_id)

    def estados(self) -> list[tuple[str, str]]:
        return [(codigo, ETIQUETAS_ESTADO[codigo]) for codigo in ESTADOS_INSCRICAO]

    def resumo(self) -> dict[str, int]:
        return {
            "total": repos_inscricoes.contar_inscricoes(self.bd),
            "inscritos": repos_inscricoes.contar_inscricoes(self.bd, "inscrito"),
            "participantes": repos_inscricoes.contar_inscricoes(self.bd, "participante"),
            "organizacao": repos_inscricoes.contar_inscricoes(self.bd, "organizacao"),
            "com_dorsal": repos_prova.contar_participacoes(self.bd),
            "chegadas": repos_prova.contar_chegadas(self.bd),
        }

    def alunos_sem_inscricao(self, pesquisa: str = "") -> list[dict]:
        alunos = repos_cadastro.listar_alunos(self.bd, pesquisa)
        inscritos = {linha["aluno_id"] for linha in self.listar()}
        return [aluno for aluno in alunos if aluno["id"] not in inscritos]

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------
    @requer(P_INSCRICOES)
    def criar(self, aluno_id: int, estado: str = "inscrito", observacoes: str = "") -> int:
        if not aluno_id:
            raise ErroValidacao("Selecione um aluno.")
        if estado not in ESTADOS_INSCRICAO:
            raise ErroValidacao("Estado de inscrição inválido.")

        aluno = repos_cadastro.obter_aluno(self.bd, int(aluno_id))
        if not aluno:
            raise ErroValidacao("Aluno inexistente.")
        if not aluno["ativo"]:
            raise ErroValidacao("O aluno está inativo e não pode ser inscrito.")
        if repos_inscricoes.obter_inscricao_do_aluno(self.bd, int(aluno_id)):
            raise ErroValidacao("Este aluno já tem uma inscrição registada.")

        escalao_id = None
        if estado in ("inscrito", "participante"):
            escalao = repos_cadastro.escalao_para(self.bd, aluno["sexo"], self._idade(aluno))
            if escalao is None:
                raise ErroValidacao(
                    "Não foi possível determinar o escalão do aluno. Verifique a data de "
                    "nascimento e os escalões definidos nas configurações."
                )
            escalao_id = int(escalao["id"])

        return repos_inscricoes.criar_inscricao(
            self.bd, int(aluno_id), escalao_id, estado, self._id_utilizador(),
            (observacoes or "").strip(),
        )

    @requer(P_INSCRICOES)
    def inscrever_novo_aluno(self, numero: str, nome: str, sexo: str,
                             data_nascimento: str, turma: str = "",
                             codigo_cartao: str = "", estado: str = "inscrito",
                             observacoes: str = "") -> int:
        """Cria o aluno com os dados indicados e regista logo a inscrição.

        A turma é escrita pelo utilizador (ex.: ``10A``); se ainda não existir é
        criada automaticamente, senão é reutilizada a que já existe.
        """
        numero = (numero or "").strip()
        nome = (nome or "").strip()
        sexo = (sexo or "").strip().upper()
        cartao = (codigo_cartao or "").strip()

        if not numero:
            raise ErroValidacao("Indique o número do aluno.")
        if not nome:
            raise ErroValidacao("Indique o nome do aluno.")
        if sexo not in ("M", "F"):
            raise ErroValidacao("Selecione o sexo do aluno.")
        nascimento = datas.normalizar_data(data_nascimento)
        if not nascimento:
            raise ErroValidacao("Indique a data de nascimento no formato dd/mm/aaaa.")
        if estado not in ESTADOS_INSCRICAO:
            raise ErroValidacao("Estado de inscrição inválido.")

        turma_texto = str(turma or "").strip()
        turma_id: int | None = None
        if turma_texto:
            ja_existe = repos_cadastro.obter_turma_por_codigo(self.bd, turma_texto)
            if ja_existe:
                turma_id = int(ja_existe["id"])
            else:
                turma_id = repos_cadastro.criar_turma(
                    self.bd, turma_texto, turma_texto, None
                )

        existente = repos_cadastro.obter_aluno_por_numero(self.bd, numero, turma_id)
        if existente:
            raise ErroValidacao(
                f"Já existe o aluno nº {numero} ({existente['nome']}) nessa turma. "
                "Escolha-o na lista de alunos para o inscrever."
            )

        if estado in ("inscrito", "participante"):
            escalao = repos_cadastro.escalao_para(
                self.bd, sexo, datas.idade_em_ano(nascimento, self.ano_referencia())
            )
            if escalao is None:
                raise ErroValidacao(
                    "Não foi possível determinar o escalão do aluno. Verifique a data de "
                    "nascimento e os escalões definidos nas configurações."
                )

        try:
            aluno_id = repos_cadastro.criar_aluno(
                self.bd, numero, nome, sexo, nascimento, turma_id, cartao or None
            )
        except pymysql.err.IntegrityError as erro:
            raise ErroValidacao("Já existe um aluno com esse código de cartão.") from erro

        return self.criar(aluno_id, estado, observacoes)

    @requer(P_INSCRICOES)
    def atualizar(self, inscricao_id: int, estado: str, observacoes: str = "") -> None:
        inscricao = repos_inscricoes.obter_inscricao(self.bd, int(inscricao_id))
        if not inscricao:
            raise ErroValidacao("Inscrição inexistente.")
        if estado not in ESTADOS_INSCRICAO:
            raise ErroValidacao("Estado de inscrição inválido.")
        if repos_prova.participacao_da_inscricao(self.bd, int(inscricao_id)) and estado == "organizacao":
            raise ErroValidacao(
                "O participante já tem dorsal entregue; não pode ser alterado para organização."
            )

        escalao_id = inscricao["escalao_id"]
        if estado in ("inscrito", "participante") and not escalao_id:
            aluno = repos_cadastro.obter_aluno(self.bd, int(inscricao["aluno_id"]))
            escalao = repos_cadastro.escalao_para(
                self.bd, inscricao["sexo"], self._idade(aluno) if aluno else None
            )
            if escalao is None:
                raise ErroValidacao("Não foi possível determinar o escalão do aluno.")
            escalao_id = int(escalao["id"])

        repos_inscricoes.atualizar_inscricao(
            self.bd, int(inscricao_id), escalao_id, estado, (observacoes or "").strip()
        )

    @requer(P_INSCRICOES)
    def anular(self, inscricao_id: int) -> None:
        inscricao = repos_inscricoes.obter_inscricao(self.bd, int(inscricao_id))
        if not inscricao:
            raise ErroValidacao("Inscrição inexistente.")
        if repos_prova.participacao_da_inscricao(self.bd, int(inscricao_id)):
            raise ErroValidacao(
                "A inscrição já tem dorsal atribuído. Cancele primeiro a participação "
                "no secretariado de partida."
            )
        repos_inscricoes.apagar_inscricao(self.bd, int(inscricao_id))

    # ------------------------------------------------------------------
    # Ajudas
    # ------------------------------------------------------------------
    def ano_referencia(self) -> int:
        try:
            return int(self._valor_config("ano_referencia_idades", "2026"))
        except ValueError:
            return 2026

    def _idade(self, aluno: dict | None) -> int | None:
        if not aluno:
            return None
        return datas.idade_em_ano(aluno.get("data_nascimento"), self.ano_referencia())
