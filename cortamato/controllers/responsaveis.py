"""Gestão de responsáveis, contas, perfis e permissões."""

from __future__ import annotations

import pymysql

from ..models import repos_acesso
from ..utils.seguranca import gerar_hash
from .base import P_PERFIS, P_RESPONSAVEIS, ControladorBase, ErroValidacao, requer


class ControladorResponsaveis(ControladorBase):
    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def listar(self) -> list[dict]:
        return repos_acesso.listar_responsaveis(self.bd)

    def listar_perfis(self) -> list[dict]:
        return repos_acesso.listar_perfis(self.bd)

    def matriz_permissoes(self) -> list[dict]:
        return repos_acesso.matriz_permissoes(self.bd)

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------
    @requer(P_RESPONSAVEIS)
    def criar(self, nome: str, email: str, username: str, password: str,
              perfil_id: int) -> int:
        nome = (nome or "").strip()
        email = (email or "").strip()
        username = (username or "").strip()
        if not nome or not email or not username:
            raise ErroValidacao("Nome, e-mail e utilizador são obrigatórios.")
        if "@" not in email:
            raise ErroValidacao("Indique um endereço de e-mail válido.")
        if len(password or "") < 6:
            raise ErroValidacao("A palavra-passe deve ter pelo menos 6 caracteres.")
        if not perfil_id:
            raise ErroValidacao("Selecione um perfil de acesso.")
        try:
            return repos_acesso.criar_responsavel(
                self.bd, nome, email, username, gerar_hash(password), int(perfil_id), 1
            )
        except pymysql.err.IntegrityError:
            raise ErroValidacao("Já existe um responsável com esse utilizador ou e-mail.")

    @requer(P_RESPONSAVEIS)
    def atualizar(self, responsavel_id: int, nome: str, email: str,
                  perfil_id: int, ativo: bool) -> None:
        nome = (nome or "").strip()
        email = (email or "").strip()
        if not nome or not email:
            raise ErroValidacao("Nome e e-mail são obrigatórios.")
        if self._id_utilizador() == int(responsavel_id) and not ativo:
            raise ErroValidacao("Não é possível desativar a conta em utilização.")
        try:
            repos_acesso.atualizar_responsavel(
                self.bd, int(responsavel_id), nome, email, int(perfil_id), 1 if ativo else 0
            )
        except pymysql.err.IntegrityError:
            raise ErroValidacao("O e-mail indicado já está associado a outro responsável.")

    @requer(P_RESPONSAVEIS)
    def definir_estado(self, responsavel_id: int, ativo: bool) -> None:
        if self._id_utilizador() == int(responsavel_id) and not ativo:
            raise ErroValidacao("Não é possível desativar a conta em utilização.")
        repos_acesso.definir_ativo(self.bd, int(responsavel_id), 1 if ativo else 0)

    @requer(P_RESPONSAVEIS)
    def redefinir_password(self, responsavel_id: int, nova: str) -> None:
        if len(nova or "") < 6:
            raise ErroValidacao("A palavra-passe deve ter pelo menos 6 caracteres.")
        repos_acesso.atualizar_password(self.bd, int(responsavel_id), gerar_hash(nova))

    @requer(P_PERFIS)
    def permissoes_do_perfil(self, perfil_id: int) -> list[str]:
        return repos_acesso.permissoes_do_perfil(self.bd, int(perfil_id))
