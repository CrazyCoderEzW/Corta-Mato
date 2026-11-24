"""Vista de configurações da atividade, escalões etários e dados escolares."""

from __future__ import annotations

import flet as ft

from ..controllers.base import ErroValidacao, PermissaoNegada
from . import common

CHAVES_FORMULARIO = [
    ("designacao_atividade", "Designação da atividade", 300),
    ("edicao", "Edição (ex.: 2026/2027)", 180),
    ("data_prova", "Data da prova (dd/mm/aaaa)", 180),
    ("hora_partida", "Hora da primeira partida", 180),
    ("local", "Local da prova", 300),
    ("prazo_inscricoes", "Prazo de inscrições (dd/mm/aaaa)", 200),
    ("ano_referencia_idades", "Ano de referência das idades", 200),
    ("dorsais_inicio", "Primeiro dorsal", 150),
    ("apurados_por_escalao", "Apurados por escalão/sexo", 190),
    ("pontos_coletiva", "Elementos que pontuam por equipa", 210),
    ("email_remetente", "E-mail remetente das comunicações", 280),
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
    for chave, rotulo, largura in CHAVES_FORMULARIO:
        if chave in chaves_data:
            campos[chave] = common.campo_data(page, rotulo.replace(" (dd/mm/aaaa)", ""),
                                             valores.get(chave, ""), largura)
        else:
            campos[chave] = common.campo(rotulo, valores.get(chave, ""), largura)

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

    bloco_atividade = common.cartao(
        ft.Text("Dados da atividade", size=15, weight=ft.FontWeight.BOLD),
        ft.Row([controlo(chave) for chave, _r, _l in CHAVES_FORMULARIO], wrap=True, spacing=12),
        ft.Row([common.botao("Guardar configuração", guardar_atividade, icone=ft.Icons.SAVE)]),
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
        ft.Text("Escalões etários por sexo", size=15, weight=ft.FontWeight.BOLD),
        common.subtitulo(
            "A idade é calculada a partir do ano de referência definido acima. "
            "Os apurados indicam quantos atletas passam à fase seguinte "
            "(0 = usar o valor global das configurações)."
        ),
        ft.Row([seletor], wrap=True, spacing=12),
        ft.Row([campo_designacao, campo_sexo, campo_idade_min, campo_idade_max,
                campo_apurados], wrap=True, spacing=12),
        ft.Row([campo_ativo, common.botao("Guardar escalão", guardar_escalao),
                common.botao("Novo escalão", limpar_escalao, principal=False)]),
        common.separador(),
        tabela_escaloes,
    )

    # ------------------------------------------------------------------
    # Turmas e alunos
    # ------------------------------------------------------------------
    turmas = controlador.listar_turmas()
    alunos = controlador.listar_alunos()[:300]

    bloco_turmas = common.cartao(
        ft.Text("Turmas e diretores de turma", size=15, weight=ft.FontWeight.BOLD),
        common.subtitulo("A importação é feita no módulo «Importações CSV»."),
        common.tabela(
            ["Código", "Designação", "Ano", "Diretor de Turma", "E-mail DT", "Alunos"],
            [[turma["codigo"], turma["designacao"] or "", turma["ano"] or "",
              turma["dt_nome"] or "", turma["dt_email"] or "", turma["total_alunos"]]
             for turma in turmas],
        ),
    )

    bloco_alunos = common.cartao(
        ft.Text(f"Alunos carregados (a mostrar {len(alunos)})", size=15,
                weight=ft.FontWeight.BOLD),
        common.tabela(
            ["Nº", "Nome", "Sexo", "Nascimento", "Turma", "Cartão"],
            [[aluno["numero"], aluno["nome"], aluno["sexo"],
              aluno["data_nascimento"] or "", aluno["turma"] or "",
              aluno["codigo_cartao"] or "—"] for aluno in alunos],
        ),
    )

    return ft.Column(
        [common.titulo("Configurações"),
         bloco_atividade,
         bloco_escaloes,
         bloco_turmas,
         bloco_alunos],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )
