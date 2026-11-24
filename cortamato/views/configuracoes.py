"""Vista de configurações da atividade, escalões etários e dados escolares."""

from __future__ import annotations

import flet as ft

from ..controllers.base import ErroValidacao, PermissaoNegada
from . import common

#: Campo, rótulo e largura na grelha de 12 colunas do formulário.
CHAVES_FORMULARIO = [
    ("designacao_atividade", "Designação da atividade",
     {"xs": 12, "sm": 6, "md": 6, "lg": 6}),
    ("edicao", "Edição (ex.: 2026/2027)", {"xs": 6, "sm": 3, "lg": 3}),
    ("data_prova", "Data da prova (dd/mm/aaaa)", {"xs": 6, "sm": 3, "lg": 3}),
    ("hora_partida", "Hora da primeira partida", {"xs": 6, "sm": 3, "lg": 3}),
    ("local", "Local da prova", {"xs": 12, "sm": 6, "lg": 6}),
    ("prazo_inscricoes", "Prazo de inscrições (dd/mm/aaaa)",
     {"xs": 6, "sm": 3, "lg": 3}),
    ("ano_referencia_idades", "Ano de referência das idades", {"xs": 6, "sm": 3, "lg": 3}),
    ("dorsais_inicio", "Primeiro dorsal", {"xs": 6, "sm": 3, "lg": 3}),
    ("apurados_por_escalao", "Apurados por escalão/sexo", {"xs": 6, "sm": 3, "lg": 3}),
    ("pontos_coletiva", "Elementos que pontuam por equipa", {"xs": 6, "sm": 3, "lg": 3}),
    ("email_remetente", "E-mail remetente das comunicações",
     {"xs": 12, "sm": 12, "md": 12, "lg": 12}),
]

#: Secções do formulário (título e campos, pela ordem de `CHAVES_FORMULARIO`).
GRUPOS_FORMULARIO = [
    ("Atividade e datas",
     ("designacao_atividade", "edicao", "data_prova", "hora_partida",
      "local", "prazo_inscricoes")),
    ("Regras de apuramento",
     ("ano_referencia_idades", "dorsais_inicio", "apurados_por_escalao",
      "pontos_coletiva", "email_remetente")),
]


def construir(app) -> ft.Control:
    page = app.page
    controlador = app.configuracoes
    valores = controlador.todas()

    # ------------------------------------------------------------------
    # Configuração da atividade
    # ------------------------------------------------------------------
    chaves_data = {"data_prova", "prazo_inscricoes"}
    campos: dict[str, object] = {}
    for chave, rotulo, colunas in CHAVES_FORMULARIO:
        # Sem largura fixa: cada campo estica para preencher a sua coluna.
        if chave in chaves_data:
            campos[chave] = common.campo_data(page, rotulo.replace(" (dd/mm/aaaa)", ""),
                                             valores.get(chave, ""), None, 1)
        else:
            campos[chave] = common.campo(rotulo, valores.get(chave, ""), None)

    # Campos brancos com contorno: destacam-se do cartão sem o tom acinzentado
    # do preenchimento por omissão.
    for item in campos.values():
        alvo = item.campo if isinstance(item, common.CampoData) else item
        alvo.fill_color = "#FFFFFF"
        alvo.border = ft.InputBorder.OUTLINE
        alvo.border_color = common.CINZA_BORDA

    def controlo(chave: str) -> ft.Control:
        item = campos[chave]
        return item.control if isinstance(item, common.CampoData) else item

    def guardar_atividade(_evento):
        try:
            controlador.guardar_atividade({chave: campo.value for chave, campo in campos.items()})
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        common.mensagem(page, "Configuração da atividade guardada.")
        app.navegar("configuracoes")

    colunas_por_chave = {chave: colunas for chave, _r, colunas in CHAVES_FORMULARIO}

    def seccao(titulo: str, chaves: tuple[str, ...]) -> ft.Control:
        """Título pequeno + grelha de campos dessa secção."""
        celulas = [
            ft.Container(content=controlo(chave), col=colunas_por_chave[chave])
            for chave in chaves
        ]
        return ft.Column(
            [
                ft.Text(titulo.upper(), size=10, weight=ft.FontWeight.BOLD,
                        color=common.VERDE_TEXTO),
                ft.ResponsiveRow(celulas, spacing=12, run_spacing=16),
            ],
            spacing=8,
            tight=True,
        )

    # Barra de ações: dica à esquerda, botão encostado à direita.
    barra_acoes = ft.Container(
        content=ft.Row(
            [
                ft.Text("As alterações ficam disponíveis de imediato em toda a prova.",
                        size=11, color=common.TEXTO_SUAVE, expand=True),
                common.botao("Guardar configuração", guardar_atividade,
                             icone=ft.Icons.SAVE),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=common.CINZA_SUAVE,
        border=ft.border.all(1, common.CINZA_BORDA),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
    )

    bloco_atividade = common.cartao(
        common.titulo_seccao("Dados da atividade", ft.Icons.EDIT_NOTE),
        common.subtitulo(
            "Informação usada no painel, nos dorsais, nas classificações e nas comunicações."
        ),
        *[seccao(titulo, chaves) for titulo, chaves in GRUPOS_FORMULARIO],
        barra_acoes,
        espacamento=14,
        preenchimento=16,
    )

    # ------------------------------------------------------------------
    # Escalões
    # ------------------------------------------------------------------
    escaloes = controlador.listar_escaloes()
    seletor = common.menu_suspenso(
        "Escalão existente (para editar)",
        [(escalao["id"], f"{escalao['designacao']} — {'Masculino' if escalao['sexo'] == 'M' else 'Feminino'}")
         for escalao in escaloes],
        largura=320,
    )
    campo_designacao = common.campo("Designação", "", 200)
    campo_sexo = common.menu_suspenso("Sexo", [("M", "Masculino"), ("F", "Feminino")], largura=160)
    campo_idade_min = common.campo("Idade mínima", "", 130)
    campo_idade_max = common.campo("Idade máxima", "", 130)
    campo_apurados = common.campo("Apurados", "6", 110)
    campo_ativo = ft.Checkbox(label="Ativo", value=True)

    # Mesmo tratamento visual dos campos da atividade: sem largura fixa, para
    # esticarem na grelha, e com fundo branco sobre o cartão.
    for campo_escalao in (seletor, campo_designacao, campo_sexo,
                          campo_idade_min, campo_idade_max, campo_apurados):
        campo_escalao.width = None
        campo_escalao.fill_color = "#FFFFFF"
        campo_escalao.border_color = common.CINZA_BORDA

    def carregar_escalao(_evento=None):
        if not seletor.value:
            return
        escolhido = next(
            (item for item in controlador.listar_escaloes()
             if str(item["id"]) == str(seletor.value)), None,
        )
        if not escolhido:
            return
        campo_designacao.value = escolhido["designacao"]
        campo_sexo.value = escolhido["sexo"]
        campo_idade_min.value = str(escolhido["idade_min"])
        campo_idade_max.value = str(escolhido["idade_max"])
        campo_apurados.value = str(escolhido["apurados"])
        campo_ativo.value = bool(escolhido["ativo"])
        page.update()

    seletor.on_change = carregar_escalao

    def limpar_escalao(_evento):
        seletor.value = None
        campo_designacao.value = ""
        campo_sexo.value = None
        campo_idade_min.value = ""
        campo_idade_max.value = ""
        campo_apurados.value = "6"
        campo_ativo.value = True
        page.update()

    def guardar_escalao(_evento):
        try:
            if seletor.value:
                controlador.atualizar_escalao(
                    int(seletor.value), campo_designacao.value or "", campo_sexo.value or "",
                    campo_idade_min.value or "", campo_idade_max.value or "",
                    campo_apurados.value or "0", bool(campo_ativo.value),
                )
            else:
                controlador.criar_escalao(
                    campo_designacao.value or "", campo_sexo.value or "",
                    campo_idade_min.value or "", campo_idade_max.value or "",
                    campo_apurados.value or "0",
                )
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        common.mensagem(page, "Escalão guardado.")
        app.navegar("configuracoes")

    tabela_escaloes = common.tabela(
        ["Escalão", "Sexo", "Idades", "Apurados", "Ativo"],
        [[item["designacao"], "M" if item["sexo"] == "M" else "F",
          f"{item['idade_min']}-{item['idade_max']}", item["apurados"],
          "Sim" if item["ativo"] else "Não"] for item in escaloes],
    )

    bloco_escaloes = common.cartao(
        common.titulo_seccao("Escalões etários por sexo", ft.Icons.CATEGORY),
        common.subtitulo(
            "A idade é calculada a partir do ano de referência definido acima. "
            "Os apurados indicam quantos atletas passam à fase seguinte "
            "(0 = usar o valor global das configurações)."
        ),
        ft.ResponsiveRow(
            [
                ft.Container(seletor, col={"xs": 12, "lg": 6}),
                ft.Container(campo_designacao, col={"xs": 12, "lg": 6}),
                ft.Container(campo_sexo, col={"xs": 6, "lg": 4}),
                ft.Container(campo_idade_min, col={"xs": 6, "lg": 3}),
                ft.Container(campo_idade_max, col={"xs": 6, "lg": 3}),
                ft.Container(campo_apurados, col={"xs": 6, "lg": 2}),
            ],
            spacing=12,
            run_spacing=12,
        ),
        ft.Row(
            [campo_ativo, common.botao("Guardar escalão", guardar_escalao),
             common.botao("Novo escalão", limpar_escalao, principal=False)],
            spacing=12,
            wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        common.separador(),
        tabela_escaloes,
        preenchimento=16,
    )

    # ------------------------------------------------------------------
    # Turmas e alunos
    # ------------------------------------------------------------------
    turmas = controlador.listar_turmas()
    alunos = controlador.listar_alunos()[:300]

    bloco_turmas = common.cartao(
        common.titulo_seccao("Turmas e diretores de turma", ft.Icons.SCHOOL),
        common.subtitulo("A importação é feita no módulo «Importações CSV»."),
        common.tabela(
            ["Código", "Designação", "Ano", "Diretor de Turma", "E-mail DT", "Alunos"],
            [[turma["codigo"], turma["designacao"] or "", turma["ano"] or "",
              turma["dt_nome"] or "", turma["dt_email"] or "", turma["total_alunos"]]
             for turma in turmas],
        ),
    )

    bloco_alunos = common.cartao(
        common.titulo_seccao(f"Alunos carregados (a mostrar {len(alunos)})",
                             ft.Icons.PEOPLE),
        common.tabela(
            ["Nº", "Nome", "Sexo", "Nascimento", "Turma", "Cartão"],
            [[aluno["numero"], aluno["nome"], aluno["sexo"],
              aluno["data_nascimento"] or "", aluno["turma"] or "",
              aluno["codigo_cartao"] or "—"] for aluno in alunos],
        ),
    )

    # Duas colunas: à esquerda os escalões (formulário + tabela), à direita as
    # tabelas de turmas e de alunos, que antes ficavam isoladas a toda a largura.
    return ft.Column(
        [
            common.titulo("Configurações"),
            bloco_atividade,
            ft.ResponsiveRow(
                [
                    ft.Column([bloco_escaloes], col={"xs": 12, "lg": 6},
                              spacing=14),
                    ft.Column([bloco_turmas, bloco_alunos], col={"xs": 12, "lg": 6},
                              spacing=14),
                ],
                spacing=14,
                run_spacing=14,
            ),
        ],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )
