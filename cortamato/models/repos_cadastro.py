"""Model: turmas, alunos, escalões e configurações."""

from __future__ import annotations

from .db import BD


# ----------------------------------------------------------------------
# Configurações
# ----------------------------------------------------------------------
def todas_configuracoes(bd: BD) -> dict[str, str]:
    linhas = bd.consultar("SELECT chave, valor FROM configuracao")
    return {linha["chave"]: linha["valor"] for linha in linhas}


def obter_configuracao(bd: BD, chave: str, omissao: str = "") -> str:
    linha = bd.consultar_um("SELECT valor FROM configuracao WHERE chave = %s", (chave,))
    return linha["valor"] if linha and linha["valor"] is not None else omissao


def definir_configuracao(bd: BD, chave: str, valor: str, descricao: str | None = None) -> None:
    existente = bd.consultar_um("SELECT chave FROM configuracao WHERE chave = %s", (chave,))
    if existente:
        bd.executar("UPDATE configuracao SET valor = %s WHERE chave = %s", (valor, chave))
    else:
        bd.executar(
            "INSERT INTO configuracao (chave, valor, descricao) VALUES (%s, %s, %s)",
            (chave, valor, descricao),
        )


# ----------------------------------------------------------------------
# Turmas
# ----------------------------------------------------------------------
def listar_turmas(bd: BD) -> list[dict]:
    return bd.consultar(
        "SELECT t.*, (SELECT COUNT(*) FROM aluno a WHERE a.turma_id = t.id) AS total_alunos "
        "FROM turma t ORDER BY t.codigo"
    )


def obter_turma_por_codigo(bd: BD, codigo: str) -> dict | None:
    return bd.consultar_um("SELECT * FROM turma WHERE codigo = %s", (codigo,))


def criar_turma(bd: BD, codigo: str, designacao: str, ano: int | None,
                dt_nome: str = "", dt_email: str = "") -> int:
    return bd.executar(
        "INSERT INTO turma (codigo, designacao, ano, dt_nome, dt_email) VALUES (%s, %s, %s, %s, %s)",
        (codigo, designacao, ano, dt_nome, dt_email),
    )


def atualizar_turma(bd: BD, turma_id: int, designacao: str, ano: int | None,
                    dt_nome: str, dt_email: str) -> None:
    bd.executar(
        "UPDATE turma SET designacao = %s, ano = %s, dt_nome = %s, dt_email = %s WHERE id = %s",
        (designacao, ano, dt_nome, dt_email, turma_id),
    )


# ----------------------------------------------------------------------
# Alunos
# ----------------------------------------------------------------------
def listar_alunos(bd: BD, pesquisa: str = "") -> list[dict]:
    sql = (
        "SELECT a.*, t.codigo AS turma "
        "FROM aluno a LEFT JOIN turma t ON t.id = a.turma_id "
    )
    parametros: tuple = ()
    if pesquisa:
        sql += "WHERE a.nome LIKE %s OR a.numero LIKE %s OR t.codigo LIKE %s "
        termo = f"%{pesquisa}%"
        parametros = (termo, termo, termo)
    sql += "ORDER BY a.nome"
    return bd.consultar(sql, parametros)


def obter_aluno(bd: BD, aluno_id: int) -> dict | None:
    return bd.consultar_um(
        "SELECT a.*, t.codigo AS turma FROM aluno a "
        "LEFT JOIN turma t ON t.id = a.turma_id WHERE a.id = %s",
        (aluno_id,),
    )


def obter_aluno_por_numero(bd: BD, numero: str, turma_id: int | None) -> dict | None:
    if turma_id is None:
        return bd.consultar_um("SELECT * FROM aluno WHERE numero = %s AND turma_id IS NULL", (numero,))
    return bd.consultar_um(
        "SELECT * FROM aluno WHERE numero = %s AND turma_id = %s", (numero, turma_id)
    )


def obter_aluno_por_cartao(bd: BD, codigo: str) -> dict | None:
    return bd.consultar_um(
        "SELECT a.*, t.codigo AS turma FROM aluno a "
        "LEFT JOIN turma t ON t.id = a.turma_id WHERE a.codigo_cartao = %s",
        (codigo,),
    )


def criar_aluno(bd: BD, numero: str, nome: str, sexo: str, data_nascimento: str,
                turma_id: int | None, codigo_cartao: str | None = None) -> int:
    return bd.executar(
        "INSERT INTO aluno (numero, nome, sexo, data_nascimento, turma_id, codigo_cartao) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (numero, nome, sexo, data_nascimento or None, turma_id, codigo_cartao or None),
    )


def atualizar_aluno(bd: BD, aluno_id: int, nome: str, sexo: str, data_nascimento: str,
                    turma_id: int | None, ativo: int) -> None:
    bd.executar(
        "UPDATE aluno SET nome = %s, sexo = %s, data_nascimento = %s, turma_id = %s, ativo = %s "
        "WHERE id = %s",
        (nome, sexo, data_nascimento or None, turma_id, ativo, aluno_id),
    )


def contar_alunos(bd: BD) -> int:
    linha = bd.consultar_um("SELECT COUNT(*) AS total FROM aluno")
    return int(linha["total"]) if linha else 0


# ----------------------------------------------------------------------
# Escalões
# ----------------------------------------------------------------------
def listar_escaloes(bd: BD, apenas_ativos: bool = False) -> list[dict]:
    sql = "SELECT * FROM escalao "
    if apenas_ativos:
        sql += "WHERE ativo = 1 "
    sql += "ORDER BY idade_min, sexo, designacao"
    return bd.consultar(sql)


def obter_escalao(bd: BD, escalao_id: int) -> dict | None:
    return bd.consultar_um("SELECT * FROM escalao WHERE id = %s", (escalao_id,))


def criar_escalao(bd: BD, designacao: str, sexo: str, idade_min: int, idade_max: int,
                  apurados: int) -> int:
    return bd.executar(
        "INSERT INTO escalao (designacao, sexo, idade_min, idade_max, apurados) "
        "VALUES (%s, %s, %s, %s, %s)",
        (designacao, sexo, idade_min, idade_max, apurados),
    )


def atualizar_escalao(bd: BD, escalao_id: int, designacao: str, sexo: str,
                      idade_min: int, idade_max: int, apurados: int, ativo: int) -> None:
    bd.executar(
        "UPDATE escalao SET designacao = %s, sexo = %s, idade_min = %s, idade_max = %s, "
        "apurados = %s, ativo = %s WHERE id = %s",
        (designacao, sexo, idade_min, idade_max, apurados, ativo, escalao_id),
    )


def escalao_para(bd: BD, sexo: str, idade: int | None) -> dict | None:
    """Determina o escalão aplicável a um atleta, a partir do sexo e da idade."""
    if idade is None:
        return None
    return bd.consultar_um(
        "SELECT * FROM escalao WHERE ativo = 1 AND sexo = %s AND %s BETWEEN idade_min AND idade_max "
        "ORDER BY idade_min LIMIT 1",
        (sexo, idade),
    )
