"""Autenticação e sessão do utilizador."""

from __future__ import annotations

from ..models import repos_acesso
from ..utils.seguranca import gerar_hash, verificar_password
from .base import ControladorBase, ErroValidacao


class Sessao:
    """Estado da sessão autenticada (utilizador e permissões efetivas)."""

    def __init__(self) -> None:
        self.utilizador: dict | None = None
        self.permissoes: set[str] = set()

    def autenticado(self) -> bool:
        return self.utilizador is not None

    def tem(self, codigo: str) -> bool:
        return codigo in self.permissoes

    def iniciar(self, utilizador: dict, permissoes: list[str]) -> None:
        self.utilizador = utilizador
        self.permissoes = set(permissoes)

    def terminar(self) -> None:
        self.utilizador = None
        self.permissoes = set()

    @property
    def nome(self) -> str:
        return self.utilizador["nome"] if self.utilizador else ""

    @property
    def perfil(self) -> str:
        return self.utilizador["perfil"] if self.utilizador else ""


class ControladorAuth(ControladorBase):
    def autenticar(self, username: str, password: str) -> dict:
        utilizador_nome = (username or "").strip()
        if not utilizador_nome or not password:
            raise ErroValidacao("Indique o utilizador e a palavra-passe.")

        utilizador = repos_acesso.obter_por_username(self.bd, utilizador_nome)
        if not utilizador or not verificar_password(password, utilizador["password_hash"]):
            raise ErroValidacao("Credenciais inválidas. Verifique o utilizador e a palavra-passe.")
        if not utilizador["ativo"]:
            raise ErroValidacao("Conta desativada. Contacte o administrador do sistema.")

        permissoes = repos_acesso.permissoes_do_perfil(self.bd, utilizador["perfil_id"])
        self.sessao.iniciar(utilizador, permissoes)
        return utilizador

    def terminar_sessao(self) -> None:
        self.sessao.terminar()

    def alterar_password(self, atual: str, nova: str) -> None:
        if not self.sessao.utilizador:
            raise ErroValidacao("Sessão inválida.")
        if len(nova or "") < 6:
            raise ErroValidacao("A nova palavra-passe deve ter pelo menos 6 caracteres.")
        registo = repos_acesso.obter_responsavel(self.bd, int(self.sessao.utilizador["id"]))
        if not registo or not verificar_password(atual or "", registo["password_hash"]):
            raise ErroValidacao("A palavra-passe atual não está correta.")
        repos_acesso.atualizar_password(self.bd, int(registo["id"]), gerar_hash(nova))
