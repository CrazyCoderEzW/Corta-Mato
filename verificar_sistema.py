"""Verificação automática do processo completo do Corta-Mato (sem interface gráfica).

Executa, numa base de dados temporária, todo o fluxo do enunciado:
configurações -> importação CSV -> inscrições -> partida -> meta -> classificações
-> relatórios/exportações -> comunicação aos DT.

Uso:
    python verificar_sistema.py

Devolve código de saída 0 se todos os testes passarem e 1 caso contrário.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from cortamato.controllers.auth import ControladorAuth, Sessao
from cortamato.controllers.base import ErroValidacao
from cortamato.controllers.classificacoes import ControladorClassificacoes
from cortamato.controllers.configuracoes import ControladorConfiguracoes
from cortamato.controllers.importacao import ControladorImportacao
from cortamato.controllers.inscricoes import ControladorInscricoes
from cortamato.controllers.meta import ControladorMeta
from cortamato.controllers.partida import ControladorPartida
from cortamato.controllers.relatorios import ControladorRelatorios
from cortamato.models.db import BD

RESULTADOS: list[tuple[bool, str]] = []

# Base de dados MySQL usada apenas neste teste: é apagada e recriada no arranque.
NOME_BD_TESTE = "cortamato_teste"


def verificar(condicao: bool, descricao: str) -> None:
    RESULTADOS.append((bool(condicao), descricao))
    print(("  [OK]   " if condicao else "  [FALHA] ") + descricao)


def escrever_csv(caminho: Path, cabecalho: str, linhas: list[str]) -> Path:
    caminho.write_text(cabecalho + "\n" + "\n".join(linhas) + "\n", encoding="utf-8-sig")
    return caminho


def main() -> int:
    print("1. Base de dados e autenticação")
    bd = BD(NOME_BD_TESTE, recriar=True)
    sessao = Sessao()
    autenticacao = ControladorAuth(bd, sessao)
    autenticacao.autenticar("admin", "admin123")
    verificar(sessao.autenticado(), "autenticação do administrador inicial")
    verificar(len(sessao.permissoes) == 11, f"permissões do administrador ({len(sessao.permissoes)}/11)")

    falhou_login = False
    try:
        ControladorAuth(bd, Sessao()).autenticar("admin", "errada")
    except ErroValidacao:
        falhou_login = True
    verificar(falhou_login, "password inválida é recusada")

    config = ControladorConfiguracoes(bd, sessao)
    importacao = ControladorImportacao(bd, sessao)
    inscricoes = ControladorInscricoes(bd, sessao)
    partida = ControladorPartida(bd, sessao)
    meta = ControladorMeta(bd, sessao)
    classificacoes = ControladorClassificacoes(bd, sessao)
    relatorios = ControladorRelatorios(bd, sessao)

    print("2. Configuração e importação CSV")
    config.guardar_atividade({
        "designacao_atividade": "Corta-Mato Escolar AEPBS",
        "edicao": "2026/2027",
        "data_prova": "27/11/2026",
        "hora_partida": "09:30",
        "local": "Parque Municipal",
        "prazo_inscricoes": "20/11/2026",
        "ano_referencia_idades": "2026",
        "dorsais_inicio": "1",
        "apurados_por_escalao": "3",
        "pontos_coletiva": "3",
        "email_remetente": "direcao@aepbs.pt",
    })
    verificar(config.dados_atividade()["data_prova"] == "27/11/2026",
              "guarda e formata a data da prova")

    pasta = Path(tempfile.mkdtemp())
    csv_turmas = escrever_csv(
        pasta / "turmas.csv", "codigo;designacao;ano;dt_nome;dt_email",
        ["10A;10º A;10;Prof. Ana;ana@aepbs.pt", "9B;9º B;9;Prof. Rui;rui@aepbs.pt"],
    )
    resultado_turmas = importacao.importar_turmas(str(csv_turmas))
    verificar(resultado_turmas["criadas"] == 2 and not resultado_turmas["erros"],
              "importa 2 turmas sem erros")

    csv_alunos = escrever_csv(
        pasta / "alunos.csv",
        "numero;nome;sexo;data_nascimento;turma;codigo_cartao",
        [
            "101;Ana Silva;F;12/03/2012;10A;CARTAO-101",
            "102;Rita Costa;F;05/07/2012;10A;CARTAO-102",
            "103;João Pereira;M;22/01/2012;10A;CARTAO-103",
            "104;Miguel Santos;M;09/09/2012;10A;CARTAO-104",
            "105;Pedro Alves;M;17/11/2012;9B;CARTAO-105",
            "106;Tiago Lopes;M;01/02/2013;9B;CARTAO-106",
        ],
    )
    resultado_alunos = importacao.importar_alunos(str(csv_alunos))
    verificar(resultado_alunos["criados"] == 6 and not resultado_alunos["erros"],
              "importa 6 alunos sem erros")

    repetido = importacao.importar_alunos(str(csv_alunos))
    verificar(repetido["atualizados"] == 6 and repetido["criados"] == 0,
              "reimportação atualiza em vez de duplicar")

    csv_invalido = escrever_csv(
        pasta / "invalido.csv", "numero;nome;sexo;data_nascimento;turma",
        ["999;Aluno Fantasma;M;01/01/2012;ZZZ"],
    )
    resultado_invalido = importacao.importar_alunos(str(csv_invalido))
    verificar(len(resultado_invalido["erros"]) == 1, "turma inexistente é recusada")

    print("3. Secretariado de inscrições")
    alunos = config.listar_alunos()
    for aluno in alunos:
        inscricoes.criar(int(aluno["id"]), "inscrito")
    verificar(len(inscricoes.listar()) == 6, "regista 6 inscrições")
    verificar(all(linha["escalao"] for linha in inscricoes.listar()),
              "escalão atribuído automaticamente a todos")

    primeira = inscricoes.listar()[0]
    inscricoes.atualizar(int(primeira["id"]), "organizacao", "Apoio à organização")
    verificar(inscricoes.listar(estado="organizacao")[0]["aluno"] == primeira["aluno"],
              "altera inscrição para organização")
    inscricoes.atualizar(int(primeira["id"]), "inscrito", "")

    duplicado_recusado = False
    try:
        inscricoes.criar(int(alunos[0]["id"]), "inscrito")
    except ErroValidacao:
        duplicado_recusado = True
    verificar(duplicado_recusado, "inscrição duplicada é recusada")

    print("4. Secretariado de partida")
    verificar(partida.proximo_dorsal() == 1, "primeiro dorsal é 1")
    criados = []
    for linha in inscricoes.listar():
        criados.append(partida.entregar_dorsal(int(linha["id"]), ""))
    dorsais = [item["dorsal"] for item in criados]
    verificar(dorsais == [1, 2, 3, 4, 5, 6], f"dorsais sequenciais: {dorsais}")

    dorsal_repetido = False
    try:
        partida.entregar_dorsal(int(inscricoes.listar()[0]["id"]), "3")
    except ErroValidacao:
        dorsal_repetido = True
    verificar(dorsal_repetido, "dorsal duplicado é recusado")
    verificar(len(partida.listas_de_partida()) >= 1, "gera listas de partida por escalão/sexo")

    print("5. Secretariado de meta")
    ordem_registo = [4, 1, 6, 2]
    for dorsal in ordem_registo:
        meta.registar_por_dorsal(str(dorsal))
    verificar(meta.resumo()["chegadas"] == 4, "regista 4 chegadas")

    chegada_repetida = False
    try:
        meta.registar_por_dorsal("4")
    except ErroValidacao:
        chegada_repetida = True
    verificar(chegada_repetida, "chegada repetida é recusada")

    chegadas = meta.listar_chegadas()
    verificar(chegadas[0]["dorsal"] == 2, "última chegada é o dorsal 2 (ordem 4)")

    meta.mover_chegada(int(chegadas[0]["chegada_id"]), "1")
    nova_ordem = [linha["dorsal"] for linha in reversed(meta.listar_chegadas())]
    verificar(nova_ordem[0] == 2, f"correção de ordem aplicada: {nova_ordem}")

    meta.desfazer_ultima()
    verificar(meta.resumo()["chegadas"] == 3, "desfazer remove a última chegada")

    sem_chegada = [item for item in partida.listar_participantes() if item["chegada_ordem"] is None]
    verificar(len(sem_chegada) >= 1, "existem participantes sem chegada registada")
    meta.registar_desistencia(int(sem_chegada[0]["participacao_id"]), "Lesão")
    verificar(meta.resumo()["desistentes"] == 1, "regista desistência")
    verificar(meta.resumo()["chegadas"] == 3, "desistência não altera as chegadas válidas")

    print("6. Classificações")
    geral = classificacoes.geral()
    verificar(len(geral) == 3, f"classificação geral com 3 atletas (obtido {len(geral)})")
    verificar([linha.ordem for linha in geral] == [1, 2, 3], "ordem de chegada coerente")

    grupos = classificacoes.por_escalao()
    verificar(len(grupos) >= 1, "classificação por escalão/sexo")
    apurados = classificacoes.apurados()
    verificar(len(apurados) == 3, "apurados respeitam o limite por escalão")

    coletiva = classificacoes.coletiva()
    verificar(len(coletiva) >= 1, "classificação coletiva calculada")
    if coletiva:
        verificar(coletiva[0].posicao == 1 and coletiva[0].total_pontos > 0,
                  "primeira turma tem pontuação positiva")

    estatisticas = classificacoes.estatisticas()
    verificar(estatisticas["participantes"] == 6 and estatisticas["chegadas"] == 3,
              "estatísticas coerentes com os registos")

    print("7. Relatórios, exportações e comunicação")
    for chave, titulo in relatorios.definicoes():
        relatorio = relatorios.obter(chave)
        verificar(len(relatorio["cabecalho"]) == len(relatorio["larguras"]),
                  f"relatório '{titulo}' com colunas e larguras coerentes")
        verificar(abs(sum(relatorio["larguras"]) - 1.0) < 0.001,
                  f"larguras do relatório '{titulo}' somam 100%")

    destino_pdf = relatorios.exportar("individuais", "pdf")
    conteudo_pdf = Path(destino_pdf).read_bytes()
    verificar(conteudo_pdf.startswith(b"%PDF-1.4") and len(conteudo_pdf) > 800,
              f"PDF gerado ({len(conteudo_pdf)} bytes)")

    destino_csv = relatorios.exportar("inscritos", "csv")
    texto_csv = Path(destino_csv).read_text(encoding="utf-8-sig")
    verificar(texto_csv.startswith("Nº;Nome") and texto_csv.count("\n") >= 7,
              "CSV gerado com cabeçalho e registos")

    dados_email = relatorios.comunicacao_dt()
    verificar("Turma" in dados_email["corpo"] and "@aepbs.pt" in str(dados_email["destinatarios"]),
              "mensagem aos DT agrupada por turma")

    texto, eml = relatorios.exportar_comunicacao()
    verificar(Path(texto).exists() and Path(eml).exists(),
              "comunicação guardada em .txt e .eml")

    print("8. Controlo de acessos")
    sessao_meta = Sessao()
    from cortamato.models import repos_acesso

    perfil_meta = next(
        (perfil for perfil in repos_acesso.listar_perfis(bd) if perfil["nome"] == "Secretariado de Meta"),
        None,
    )
    if perfil_meta:
        sessao_meta.iniciar(
            {"id": 0, "nome": "Teste", "perfil": perfil_meta["nome"]},
            repos_acesso.permissoes_do_perfil(bd, int(perfil_meta["id"])),
        )
        verificar(not sessao_meta.tem("CONFIG_GERIR"),
                  "perfil de meta não tem permissão de configuração")
        verificar(sessao_meta.tem("META_GERIR"), "perfil de meta pode registar chegadas")

    print("\nResumo: %d testes, %d falhas" % (
        len(RESULTADOS), sum(1 for ok, _ in RESULTADOS if not ok)
    ))
    for ok, descricao in RESULTADOS:
        if not ok:
            print(f"  Falhou: {descricao}")
    return 0 if all(ok for ok, _ in RESULTADOS) else 1


if __name__ == "__main__":
    sys.exit(main())