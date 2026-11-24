"""Model: responsáveis, perfis e permissões."""

from __future__ import annotations

from .db import BD


def listar_responsaveis(bd: BD) -> list[dict]:
    return bd.consultar(
        "SELECT r.id, r.nome, r.email, r.username, r.ativo, r.criado_em, "
        "       r.perfil_id, p.nome AS perfil "
        "FROM responsavel r JOIN perfil p ON p.id = r.perfil_id "
        "ORDER BY r.nome"
    )


def obter_responsavel(bd: BD, responsavel_id: int) -> dict | None:
    return bd.consultar_um(
        "SELECT r.*, p.nome AS perfil FROM responsavel r "
        "JOIN perfil p ON p.id = r.perfil_id WHERE r.id = %s",
        (responsavel_id,),
    )


def obter_por_username(bd: BD, username: str) -> dict | None:
    return bd.consultar_um(
        "SELECT r.*, p.nome AS perfil FROM responsavel r "
        "JOIN perfil p ON p.id = r.perfil_id "
        "WHERE r.username = %s",
        (username,),
    )


def criar_responsavel(bd: BD, nome: str, email: str, username: str,
                      password_hash: str, perfil_id: int, ativo: int = 1) -> int:
    return bd.executar(
        "INSERT INTO responsavel (nome, email, username, password_hash, perfil_id, ativo) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (nome, email, username, password_hash, perfil_id, ativo),
    )


def atualizar_responsavel(bd: BD, responsavel_id: int, nome: str, email: str,
                          perfil_id: int, ativo: int) -> None:
    bd.executar(
        "UPDATE responsavel SET nome = %s, email = %s, perfil_id = %s, ativo = %s WHERE id = %s",
        (nome, email, perfil_id, ativo, responsavel_id),
    )


def atualizar_password(bd: BD, responsavel_id: int, password_hash: str) -> None:
    bd.executar(
        "UPDATE responsavel SET password_hash = %s WHERE id = %s",
        (password_hash, responsavel_id),
    )


def definir_ativo(bd: BD, responsavel_id: int, ativo: int) -> None:
    bd.executar("UPDATE responsavel SET ativo = %s WHERE id = %s", (ativo, responsavel_id))


def listar_perfis(bd: BD) -> list[dict]:
    return bd.consultar("SELECT id, nome, descricao FROM perfil ORDER BY nome")


def permissoes_do_perfil(bd: BD, perfil_id: int) -> list[str]:
    linhas = bd.consultar(
        "SELECT pe.codigo FROM permissao pe "
        "JOIN perfil_permissao pp ON pp.permissao_id = pe.id "
        "WHERE pp.perfil_id = %s ORDER BY pe.codigo",
        (perfil_id,),
    )
    return [linha["codigo"] for linha in linhas]


def listar_permissoes(bd: BD) -> list[dict]:
    return bd.consultar("SELECT id, codigo, descricao FROM permissao ORDER BY codigo")


def matriz_permissoes(bd: BD) -> list[dict]:
    """Devolve a matriz perfil -> lista de códigos de permissão."""
    perfis = listar_perfis(bd)
    for perfil in perfis:
        perfil["permissoes"] = permissoes_do_perfil(bd, perfil["id"])
    return perfis
