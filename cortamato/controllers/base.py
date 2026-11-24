"""Base dos controladores, permissões e exceções de domínio."""

from __future__ import annotations

from functools import wraps

from ..models.db import BD

# Códigos de permissão (iguais aos registados na tabela permissao)
P_RESPONSAVEIS = "RESPONSAVEIS_GERIR"
P_PERFIS = "PERFIS_GERIR"
P_CONFIG = "CONFIG_GERIR"
P_IMPORTAR = "IMPORTAR_DADOS"
P_INSCRICOES = "INSCRICOES_GERIR"
P_INSCRICOES_CONSULTA = "INSCRICOES_CONSULTAR"
P_PARTIDA = "PARTIDA_GERIR"
P_META = "META_GERIR"
P_CLASSIFICACOES = "CLASSIFICACOES_VER"
P_RELATORIOS = "RELATORIOS_EXPORTAR"
P_EMAIL = "EMAIL_ENVIAR"

DESCRICAO_PERMISSOES = {
    P_RESPONSAVEIS: "Gerir responsáveis, contas e perfis",
    P_PERFIS: "Gerir perfis e matriz de permissões",
    P_CONFIG: "Configurar atividade, escalões e apuramentos",
    P_IMPORTAR: "Importar turmas, DT e alunos por CSV",
    P_INSCRICOES: "Criar, alterar e anular inscrições",
    P_INSCRICOES_CONSULTA: "Consultar inscrições e participantes",
    P_PARTIDA: "Secretariado de partida (dorsais)",
    P_META: "Secretariado de meta (chegadas)",
    P_CLASSIFICACOES: "Consultar classificações",
    P_RELATORIOS: "Gerar e exportar relatórios",
    P_EMAIL: "Preparar comunicações aos DT",
}


class ErroValidacao(Exception):
    """Erro de regra de negócio, apresentável ao utilizador."""


class PermissaoNegada(Exception):
    """Operação recusada por falta de permissão do perfil autenticado."""


def requer(permissao: str):
    """Garante que a sessão autenticada possui a permissão indicada."""

    def decorador(funcao):
        @wraps(funcao)
        def envolvida(self, *args, **kwargs):
            if not self.sessao.tem(permissao):
                raise PermissaoNegada(
                    "O perfil autenticado não tem permissão para esta operação."
                )
            return funcao(self, *args, **kwargs)

        return envolvida

    return decorador


class ControladorBase:
    def __init__(self, bd: BD, sessao) -> None:
        self.bd = bd
        self.sessao = sessao

    # Ajudas comuns -----------------------------------------------------
    def _valor_config(self, chave: str, omissao: str = "") -> str:
        from ..models import repos_cadastro

        return repos_cadastro.obter_configuracao(self.bd, chave, omissao)

    def _config_inteiro(self, chave: str, omissao: int) -> int:
        try:
            return int(float(self._valor_config(chave, str(omissao))))
        except (TypeError, ValueError):
            return omissao

    def _id_utilizador(self) -> int | None:
        if self.sessao.utilizador:
            return int(self.sessao.utilizador["id"])
        return None
