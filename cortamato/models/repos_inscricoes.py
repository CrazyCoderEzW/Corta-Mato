"""Model: inscrições dos alunos."""

from __future__ import annotations

from .db import BD

ESTADOS_INSCRICAO = ("nao_inscrito", "inscrito", "participante", "organizacao")

ETIQUETAS_ESTADO = {
    "nao_inscrito": "Não inscrito",
    "inscrito": "Inscrito",
    "participante": "Participante",
    "organizacao": "Organização",
}


def listar_inscricoes(bd: BD, pesquisa: str = "", estado: str = "",
                      escalao_id: int | None = None) -> list[dict]:
    sql = (
        "SELECT i.id, i.estado, i.data_inscricao, i.observacoes, i.escalao_id, "
        "       a.id AS aluno_id, a.nome AS aluno, a.numero, a.sexo, a.data_nascimento, "
        "       t.codigo AS turma, e.designacao AS escalao, "
        "       pa.dorsal, pa.id AS participacao_id, c.ordem AS chegada_ordem "
        "FROM inscricao i "
        "JOIN aluno a ON a.id = i.aluno_id "
        "LEFT JOIN turma t ON t.id = a.turma_id "
        "LEFT JOIN escalao e ON e.id = i.escalao_id "
        "LEFT JOIN participacao pa ON pa.inscricao_id = i.id "
        "LEFT JOIN chegada c ON c.participacao_id = pa.id AND c.valida = 1 "
        "WHERE 1 = 1 "
    )
    parametros: list = []
    if pesquisa:
        termo = f"%{pesquisa}%"
        sql += "AND (a.nome LIKE %s OR a.numero LIKE %s OR t.codigo LIKE %s) "
        parametros.extend([termo, termo, termo])
    if estado:
        sql += "AND i.estado = %s "
        parametros.append(estado)
    if escalao_id:
        sql += "AND i.escalao_id = %s "
        parametros.append(escalao_id)
    sql += "ORDER BY a.nome"
    return bd.consultar(sql, tuple(parametros))


def obter_inscricao(bd: BD, inscricao_id: int) -> dict | None:
    return bd.consultar_um(
        "SELECT i.*, a.nome AS aluno, a.sexo, a.data_nascimento, t.codigo AS turma, "
        "       e.designacao AS escalao "
        "FROM inscricao i "
        "JOIN aluno a ON a.id = i.aluno_id "
        "LEFT JOIN turma t ON t.id = a.turma_id "
        "LEFT JOIN escalao e ON e.id = i.escalao_id "
        "WHERE i.id = %s",
        (inscricao_id,),
    )


def obter_inscricao_do_aluno(bd: BD, aluno_id: int) -> dict | None:
    return bd.consultar_um("SELECT * FROM inscricao WHERE aluno_id = %s", (aluno_id,))


def criar_inscricao(bd: BD, aluno_id: int, escalao_id: int | None, estado: str,
                    responsavel_id: int | None, observacoes: str = "") -> int:
    return bd.executar(
        "INSERT INTO inscricao (aluno_id, escalao_id, estado, responsavel_id, observacoes) "
        "VALUES (%s, %s, %s, %s, %s)",
        (aluno_id, escalao_id, estado, responsavel_id, observacoes),
    )


def atualizar_inscricao(bd: BD, inscricao_id: int, escalao_id: int | None, estado: str,
                        observacoes: str) -> None:
    bd.executar(
        "UPDATE inscricao SET escalao_id = %s, estado = %s, observacoes = %s WHERE id = %s",
        (escalao_id, estado, observacoes, inscricao_id),
    )


def apagar_inscricao(bd: BD, inscricao_id: int) -> None:
    bd.executar("DELETE FROM inscricao WHERE id = %s", (inscricao_id,))


def contar_inscricoes(bd: BD, estado: str | None = None) -> int:
    if estado:
        linha = bd.consultar_um("SELECT COUNT(*) AS total FROM inscricao WHERE estado = %s", (estado,))
    else:
        linha = bd.consultar_um("SELECT COUNT(*) AS total FROM inscricao")
    return int(linha["total"]) if linha else 0


def inscritos_sem_dorsal(bd: BD, excluir_organizacao: bool = True) -> list[dict]:
    sql = (
        "SELECT i.id AS inscricao_id, a.nome AS aluno, a.numero, a.sexo, "
        "       t.codigo AS turma, e.designacao AS escalao, i.estado "
        "FROM inscricao i "
        "JOIN aluno a ON a.id = i.aluno_id "
        "LEFT JOIN turma t ON t.id = a.turma_id "
        "LEFT JOIN escalao e ON e.id = i.escalao_id "
        "LEFT JOIN participacao p ON p.inscricao_id = i.id "
        "WHERE p.id IS NULL AND i.estado = 'inscrito' "
    )
    if excluir_organizacao:
        sql += "AND i.estado <> 'organizacao' "
    sql += "ORDER BY COALESCE(e.idade_min, 99), a.sexo, a.nome"
    return bd.consultar(sql)
