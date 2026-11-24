"""Model: secretariados de partida e de meta (participações, chegadas, ocorrências)."""

from __future__ import annotations

from .db import BD


# ----------------------------------------------------------------------
# Participações (secretariado de partida)
# ----------------------------------------------------------------------
def proximo_dorsal(bd: BD, inicio: int = 1) -> int:
    linha = bd.consultar_um("SELECT MAX(dorsal) AS maximo FROM participacao")
    maximo = linha["maximo"] if linha and linha["maximo"] is not None else None
    if maximo is None:
        return max(1, inicio)
    return max(maximo + 1, inicio)


def dorsal_em_uso(bd: BD, dorsal: int) -> bool:
    return bd.consultar_um("SELECT id FROM participacao WHERE dorsal = %s", (dorsal,)) is not None


def criar_participacao(bd: BD, inscricao_id: int, dorsal: int,
                       responsavel_id: int | None) -> int:
    return bd.executar(
        "INSERT INTO participacao (inscricao_id, dorsal, estado, registado_por) "
        "VALUES (%s, %s, 'entregue', %s)",
        (inscricao_id, dorsal, responsavel_id),
    )


def obter_participacao(bd: BD, participacao_id: int) -> dict | None:
    return bd.consultar_um(
        "SELECT p.*, i.aluno_id, i.escalao_id, a.nome AS aluno, a.numero, a.sexo, "
        "       t.codigo AS turma, e.designacao AS escalao "
        "FROM participacao p "
        "JOIN inscricao i ON i.id = p.inscricao_id "
        "JOIN aluno a ON a.id = i.aluno_id "
        "LEFT JOIN turma t ON t.id = a.turma_id "
        "LEFT JOIN escalao e ON e.id = i.escalao_id "
        "WHERE p.id = %s",
        (participacao_id,),
    )


def obter_por_dorsal(bd: BD, dorsal: int) -> dict | None:
    return bd.consultar_um(
        "SELECT p.*, i.aluno_id, i.escalao_id, a.nome AS aluno, a.numero, a.sexo, "
        "       t.codigo AS turma, e.designacao AS escalao, c.ordem AS chegada_ordem "
        "FROM participacao p "
        "JOIN inscricao i ON i.id = p.inscricao_id "
        "JOIN aluno a ON a.id = i.aluno_id "
        "LEFT JOIN turma t ON t.id = a.turma_id "
        "LEFT JOIN escalao e ON e.id = i.escalao_id "
        "LEFT JOIN chegada c ON c.participacao_id = p.id AND c.valida = 1 "
        "WHERE p.dorsal = %s",
        (dorsal,),
    )


def participacao_da_inscricao(bd: BD, inscricao_id: int) -> dict | None:
    return bd.consultar_um(
        "SELECT * FROM participacao WHERE inscricao_id = %s", (inscricao_id,)
    )


def apagar_participacao(bd: BD, participacao_id: int) -> None:
    bd.executar("DELETE FROM participacao WHERE id = %s", (participacao_id,))


def definir_estado_participacao(bd: BD, participacao_id: int, estado: str) -> None:
    bd.executar("UPDATE participacao SET estado = %s WHERE id = %s", (estado, participacao_id))


def listar_participantes(bd: BD) -> list[dict]:
    return bd.consultar(
        "SELECT p.id AS participacao_id, p.dorsal, p.estado, p.hora_dorsal, "
        "       a.nome AS aluno, a.numero, a.sexo, t.codigo AS turma, "
        "       e.designacao AS escalao, e.id AS escalao_id, e.idade_min, "
        "       c.ordem AS chegada_ordem "
        "FROM participacao p "
        "JOIN inscricao i ON i.id = p.inscricao_id "
        "JOIN aluno a ON a.id = i.aluno_id "
        "LEFT JOIN turma t ON t.id = a.turma_id "
        "LEFT JOIN escalao e ON e.id = i.escalao_id "
        "LEFT JOIN chegada c ON c.participacao_id = p.id AND c.valida = 1 "
        "ORDER BY COALESCE(e.idade_min, 99), a.sexo, p.dorsal"
    )


def listas_de_partida(bd: BD) -> list[dict]:
    """Participantes agrupados por escalão/sexo para consulta das listas de partida."""
    linhas = listar_participantes(bd)
    grupos: dict[str, list[dict]] = {}
    for linha in linhas:
        chave = f"{linha['escalao'] or 'Sem escalão'} — {'Masculino' if linha['sexo'] == 'M' else 'Feminino'}"
        grupos.setdefault(chave, []).append(linha)
    return [{"grupo": chave, "participantes": sorted(itens, key=lambda x: x["dorsal"])}
            for chave, itens in sorted(grupos.items())]


# ----------------------------------------------------------------------
# Chegadas (secretariado de meta)
# ----------------------------------------------------------------------
def proxima_ordem(bd: BD) -> int:
    linha = bd.consultar_um("SELECT MAX(ordem) AS maximo FROM chegada WHERE valida = 1")
    maximo = linha["maximo"] if linha and linha["maximo"] is not None else None
    return 1 if maximo is None else int(maximo) + 1


def criar_chegada(bd: BD, participacao_id: int, ordem: int, metodo: str,
                  responsavel_id: int | None) -> int:
    return bd.executar(
        "INSERT INTO chegada (participacao_id, ordem, metodo, registado_por) "
        "VALUES (%s, %s, %s, %s)",
        (participacao_id, ordem, metodo, responsavel_id),
    )


def obter_chegada_por_participacao(bd: BD, participacao_id: int) -> dict | None:
    return bd.consultar_um(
        "SELECT * FROM chegada WHERE participacao_id = %s AND valida = 1", (participacao_id,)
    )


def listar_chegadas(bd: BD, limite: int = 200) -> list[dict]:
    return bd.consultar(
        "SELECT c.id AS chegada_id, c.ordem, c.hora, c.metodo, p.dorsal, p.estado, "
        "       p.id AS participacao_id, a.nome AS aluno, t.codigo AS turma, "
        "       e.designacao AS escalao, a.sexo "
        "FROM chegada c "
        "JOIN participacao p ON p.id = c.participacao_id "
        "JOIN inscricao i ON i.id = p.inscricao_id "
        "JOIN aluno a ON a.id = i.aluno_id "
        "LEFT JOIN turma t ON t.id = a.turma_id "
        "LEFT JOIN escalao e ON e.id = i.escalao_id "
        "WHERE c.valida = 1 "
        "ORDER BY c.ordem DESC LIMIT %s",
        (limite,),
    )


def apagar_ultima_chegada(bd: BD, participacao_id: int | None = None) -> int | None:
    if participacao_id is None:
        linha = bd.consultar_um("SELECT id FROM chegada WHERE valida = 1 ORDER BY ordem DESC LIMIT 1")
    else:
        linha = bd.consultar_um(
            "SELECT id FROM chegada WHERE participacao_id = %s AND valida = 1", (participacao_id,)
        )
    if not linha:
        return None
    bd.executar("DELETE FROM chegada WHERE id = %s", (linha["id"],))
    normalizar_ordens(bd)
    return linha["id"]


def normalizar_ordens(bd: BD) -> None:
    con = bd.ligar()
    try:
        with con.cursor() as cursor:
            cursor.execute("SELECT id FROM chegada WHERE valida = 1 ORDER BY ordem, id")
            for posicao, (identificador,) in enumerate(cursor.fetchall(), start=1):
                cursor.execute(
                    "UPDATE chegada SET ordem = %s WHERE id = %s", (posicao, identificador)
                )
        con.commit()
    finally:
        con.close()


def mover_chegada(bd: BD, chegada_id: int, nova_ordem: int) -> None:
    """Reordena a lista de chegadas colocando o registo na posição indicada."""
    con = bd.ligar()
    try:
        with con.cursor() as cursor:
            cursor.execute("SELECT id FROM chegada WHERE valida = 1 ORDER BY ordem, id")
            registos = cursor.fetchall()
            ids = [identificador for (identificador,) in registos]
            if chegada_id not in ids:
                return
            ids.remove(chegada_id)
            indice = max(0, min(int(nova_ordem) - 1, len(ids)))
            ids.insert(indice, chegada_id)
            for posicao, identificador in enumerate(ids, start=1):
                cursor.execute(
                    "UPDATE chegada SET ordem = %s WHERE id = %s", (posicao, identificador)
                )
        con.commit()
    finally:
        con.close()


# ----------------------------------------------------------------------
# Ocorrências (desistências, desclassificações, correções)
# ----------------------------------------------------------------------
def registar_ocorrencia(bd: BD, participacao_id: int, tipo: str, motivo: str,
                        responsavel_id: int | None) -> int:
    return bd.executar(
        "INSERT INTO ocorrencia (participacao_id, tipo, motivo, registado_por) "
        "VALUES (%s, %s, %s, %s)",
        (participacao_id, tipo, motivo, responsavel_id),
    )


def listar_ocorrencias(bd: BD) -> list[dict]:
    return bd.consultar(
        "SELECT o.id, o.tipo, o.motivo, o.hora, p.dorsal, a.nome AS aluno, "
        "       t.codigo AS turma, o.participacao_id "
        "FROM ocorrencia o "
        "JOIN participacao p ON p.id = o.participacao_id "
        "JOIN inscricao i ON i.id = p.inscricao_id "
        "JOIN aluno a ON a.id = i.aluno_id "
        "LEFT JOIN turma t ON t.id = a.turma_id "
        "ORDER BY o.hora DESC"
    )


# ----------------------------------------------------------------------
# Resultados (usados nas classificações)
# ----------------------------------------------------------------------
def resultados_validos(bd: BD) -> list[dict]:
    """Chegadas válidas de participantes classificados, ordenadas pela ordem de chegada."""
    return bd.consultar(
        "SELECT c.ordem, p.dorsal, p.estado, p.id AS participacao_id, "
        "       i.aluno_id, i.escalao_id, a.nome AS aluno, a.sexo, "
        "       t.codigo AS turma, COALESCE(e.designacao, 'Sem escalão') AS escalao, "
        "       COALESCE(e.apurados, 0) AS apurados, COALESCE(e.idade_min, 99) AS idade_min "
        "FROM chegada c "
        "JOIN participacao p ON p.id = c.participacao_id "
        "JOIN inscricao i ON i.id = p.inscricao_id "
        "JOIN aluno a ON a.id = i.aluno_id "
        "LEFT JOIN turma t ON t.id = a.turma_id "
        "LEFT JOIN escalao e ON e.id = i.escalao_id "
        "WHERE c.valida = 1 AND p.estado = 'entregue' "
        "ORDER BY c.ordem"
    )


def contar_participacoes(bd: BD) -> int:
    linha = bd.consultar_um("SELECT COUNT(*) AS total FROM participacao")
    return int(linha["total"]) if linha else 0


def contar_chegadas(bd: BD) -> int:
    linha = bd.consultar_um("SELECT COUNT(*) AS total FROM chegada WHERE valida = 1")
    return int(linha["total"]) if linha else 0


def contar_estado_participacao(bd: BD, estado: str) -> int:
    linha = bd.consultar_um(
        "SELECT COUNT(*) AS total FROM participacao WHERE estado = %s", (estado,)
    )
    return int(linha["total"]) if linha else 0
