"""Vista do secretariado de inscrições."""

from __future__ import annotations

import flet as ft

from ..controllers.base import P_INSCRICOES, ErroValidacao, PermissaoNegada
from ..models.repos_inscricoes import ETIQUETAS_ESTADO
from ..utils import datas
from . import common


def construir(app) -> ft.Control:
    page = app.page
    controlador = app.inscricoes
    pode_gerir = app.sessao.tem(P_INSCRICOES)

    # ------------------------------------------------------------------
    # Filtros e tabela
    # ------------------------------------------------------------------
    pesquisa = common.campo("Pesquisar (nome, nº, turma)", "", 260)
    filtro_estado = common.menu_suspenso(
        "Estado", [("", "Todos")] + [(codigo, rotulo) for codigo, rotulo in controlador.estados()],
        largura=200,
    )
    filtro_escalao = common.menu_suspenso(
        "Escalão",
        [("", "Todos")] + [(item["id"], f"{item['designacao']} ({item['sexo']})")
                           for item in app.configuracoes.listar_escaloes()],
        largura=220,
    )
    area_tabela = ft.Column([], spacing=8)
    area_resumo = ft.Row([], spacing=12)

    def carregar_tabela(_evento=None):
        escalao_id = int(filtro_escalao.value) if filtro_escalao.value else None
        linhas = controlador.listar(
            pesquisa.value or "", filtro_estado.value or "", escalao_id
        )
        if linhas:
            area_tabela.controls = [
                common.tabela(
                    ["Nº", "Nome", "Sexo", "Nasc.", "Turma", "Escalão", "Estado",
                     "Inscrição", "Dorsal", "Chegada"],
                    [[linha["numero"] or "—", linha["aluno"], linha["sexo"],
                      datas.formatar_data(linha["data_nascimento"]),
                      linha["turma"] or "—", linha["escalao"] or "—",
                      ETIQUETAS_ESTADO.get(linha["estado"], linha["estado"]),
                      datas.formatar_data(linha["data_inscricao"]),
                      linha["dorsal"] or "—", linha["chegada_ordem"] or "—"]
                     for linha in linhas],
                )
            ]
        else:
            area_tabela.controls = [common.aviso("Não existem inscrições para os filtros indicados.")]
        page.update()

    resumo = controlador.resumo()
    area_resumo.controls = [
        common.indicador("Total", resumo["total"], ft.Icons.EDIT_NOTE),
        common.indicador("Inscritos", resumo["inscritos"], ft.Icons.PERSON_ADD),
        common.indicador("Participantes", resumo["participantes"], ft.Icons.DIRECTIONS_RUN),
        common.indicador("Organização", resumo["organizacao"], ft.Icons.GROUPS),
    ]

    # ------------------------------------------------------------------
    # Nova inscrição
    # ------------------------------------------------------------------
    alunos_disponiveis = controlador.alunos_sem_inscricao()
    opcoes_alunos = [
        (aluno["id"], f"{aluno['nome']} — {aluno['numero'] or 's/n'} ({aluno['turma'] or 'sem turma'})")
        for aluno in alunos_disponiveis
    ]
    aluno_sel = common.menu_suspenso("Aluno", opcoes_alunos, largura=420)
    estado_novo = common.menu_suspenso(
        "Estado da inscrição",
        [("inscrito", "Inscrito"), ("organizacao", "Organização (apoio)")],
        valor="inscrito", largura=240,
    )

    def registar(_evento):
        try:
            controlador.criar(
                int(aluno_sel.value) if aluno_sel.value else 0,
                estado_novo.value or "inscrito",
            )
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        common.mensagem(page, "Inscrição registada com sucesso.")
        app.navegar("inscricoes")

    bloco_novo = common.cartao(
        ft.Text("Nova inscrição", size=15, weight=ft.FontWeight.BOLD),
        common.subtitulo(
            "O escalão é determinado automaticamente a partir do sexo, da data de nascimento "
            "e do ano de referência definido nas configurações."
        ),
        ft.Row([aluno_sel], wrap=True),
        ft.Row([estado_novo], wrap=True, spacing=12),
        ft.Row([common.botao("Registar inscrição", registar, icone=ft.Icons.ADD)]),
        common.aviso(
            "A descentralização permite que cada professor registe as inscrições das suas turmas. "
            "Se o aluno ainda não existe na base de dados, use o bloco seguinte para o registar "
            "e inscrever de uma só vez."
        ),
        visivel=pode_gerir,
    )

    # ------------------------------------------------------------------
    # Inscrever aluno novo (registo manual)
    # ------------------------------------------------------------------
    manual_numero = common.campo("Nº do aluno", "", None, expand=1)
    manual_nome = common.campo("Nome completo", "", None, expand=2)
    manual_sexo = common.menu_suspenso(
        "Sexo", [("M", "Masculino"), ("F", "Feminino")], largura=None, expand=1
    )
    manual_nascimento = common.campo_data(
        page, "Data de nascimento", largura=None, expandir=3
    )
    manual_turma = common.campo("Turma (ex.: 10A)", "", None, expand=1)

    def inscrever_manual(_evento):
        try:
            controlador.inscrever_novo_aluno(
                manual_numero.value or "",
                manual_nome.value or "",
                manual_sexo.value or "",
                manual_nascimento.value or "",
                manual_turma.value or "",
            )
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        common.mensagem(page, "Aluno registado e inscrição criada.")
        app.navegar("inscricoes")

    bloco_manual = common.cartao(
        ft.Text("Inscrever aluno novo", size=15, weight=ft.FontWeight.BOLD),
        common.subtitulo(
            "Escreva os dados do aluno: fica inscrito como «Inscrito», com o escalão "
            "calculado automaticamente. Se a turma ainda não existir, é criada."
        ),
        ft.Row([manual_numero, manual_nome, manual_sexo], spacing=12),
        ft.Row([manual_nascimento.control, manual_turma], spacing=12,
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Row([
            common.botao("Registar aluno e inscrever", inscrever_manual,
                         icone=ft.Icons.PERSON_ADD),
        ]),
        visivel=pode_gerir,
    )

    # ------------------------------------------------------------------
    # Alterar / anular
    # ------------------------------------------------------------------
    todas = controlador.listar()
    seletor_inscricao = common.menu_suspenso(
        "Inscrição a alterar",
        [(linha["id"], f"#{linha['id']} — {linha['aluno']} ({linha['turma'] or 'sem turma'})")
         for linha in todas],
        largura=420,
    )
    estado_alterar = common.menu_suspenso(
        "Novo estado",
        [(codigo, rotulo) for codigo, rotulo in controlador.estados()],
        largura=240,
    )

    def preencher(_evento=None):
        escolhida = next((linha for linha in todas if str(linha["id"]) == str(seletor_inscricao.value)), None)
        if escolhida:
            estado_alterar.value = escolhida["estado"]
            page.update()

    seletor_inscricao.on_change = preencher

    def guardar_alteracao(_evento):
        try:
            controlador.atualizar(
                int(seletor_inscricao.value) if seletor_inscricao.value else 0,
                estado_alterar.value or "",
            )
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        common.mensagem(page, "Inscrição atualizada.")
        app.navegar("inscricoes")

    def anular(_evento):
        if not seletor_inscricao.value:
            common.mensagem(page, "Selecione a inscrição a anular.", erro=True)
            return
        try:
            controlador.anular(int(seletor_inscricao.value))
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        common.mensagem(page, "Inscrição anulada.")
        app.navegar("inscricoes")

    bloco_alterar = common.cartao(
        ft.Text("Alterar ou anular inscrição", size=15, weight=ft.FontWeight.BOLD),
        ft.Row([seletor_inscricao], wrap=True),
        ft.Row([estado_alterar], wrap=True, spacing=12),
        ft.Row([
            common.botao("Guardar alteração", guardar_alteracao, icone=ft.Icons.SAVE),
            common.botao("Anular inscrição", anular, principal=False, icone=ft.Icons.DELETE),
        ], spacing=10),
        visivel=pode_gerir,
    )

    vista = ft.Column(
        [
            common.titulo("Secretariado de inscrições"),
            area_resumo,
            ft.Row([pesquisa, filtro_estado, filtro_escalao,
                    common.botao("Pesquisar", carregar_tabela, principal=False,
                                 icone=ft.Icons.SEARCH)],
                   wrap=True, spacing=12),
            area_tabela,
            bloco_novo,
            bloco_manual,
            bloco_alterar,
        ],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    carregar_tabela()
    return vista
