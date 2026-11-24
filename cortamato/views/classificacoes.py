"""Vista das classificações gerais, por escalão, coletivas e apuramentos."""

from __future__ import annotations

import flet as ft

from . import common


def construir(app) -> ft.Control:
    page = app.page
    controlador = app.classificacoes
    estatisticas = controlador.estatisticas()

    indicadores = ft.Row([
        common.indicador("Participantes", estatisticas["participantes"], ft.Icons.DIRECTIONS_RUN),
        common.indicador("Chegadas", estatisticas["chegadas"], ft.Icons.FLAG),
        common.indicador("Desistências", estatisticas["desistentes"], ft.Icons.PERSON_OFF),
        common.indicador("Desclassificados", estatisticas["desclassificados"], ft.Icons.BLOCK),
        common.indicador("Concluíram", f"{estatisticas['cobertura']}%", ft.Icons.CHECK_CIRCLE),
    ], wrap=True, spacing=12)

    # ------------------------------------------------------------------
    # Classificação geral
    # ------------------------------------------------------------------
    geral = controlador.geral()
    if geral:
        tabela_geral = common.tabela(
            ["Pos.", "Dorsal", "Nome", "Turma", "Escalão", "Sexo"],
            [[linha.ordem, linha.dorsal, linha.aluno, linha.turma, linha.escalao, linha.sexo]
             for linha in geral],
        )
    else:
        tabela_geral = common.aviso("Ainda não existem atletas classificados.")

    # ------------------------------------------------------------------
    # Classificação por escalão/sexo
    # ------------------------------------------------------------------
    grupos = controlador.por_escalao()
    opcoes = [(indice, grupo["grupo"]) for indice, grupo in enumerate(grupos)]
    seletor_grupo = common.menu_suspenso("Escalão/sexo", opcoes, largura=320)
    area_grupo = ft.Column([], spacing=8)

    def mostrar_grupo(_evento=None):
        if not grupos:
            area_grupo.controls = [common.aviso("Sem classificações por escalão.")]
            page.update()
            return
        indice = int(seletor_grupo.value) if str(seletor_grupo.value or "").isdigit() else 0
        indice = max(0, min(indice, len(grupos) - 1))
        grupo = grupos[indice]
        area_grupo.controls = [
            ft.Text(f"{grupo['grupo']} — apuram os {grupo['limite']} primeiros", size=13,
                    weight=ft.FontWeight.BOLD),
            common.tabela(
                ["Pos.", "Dorsal", "Nome", "Turma", "Apurado"],
                [[linha.ordem, linha.dorsal, linha.aluno, linha.turma,
                  "Sim" if linha.apurado else "—"] for linha in grupo["linhas"]],
            ),
        ]
        page.update()

    if grupos and not seletor_grupo.value:
        seletor_grupo.value = "0"
    seletor_grupo.on_change = mostrar_grupo

    # ------------------------------------------------------------------
    # Classificação coletiva
    # ------------------------------------------------------------------
    coletiva = controlador.coletiva()
    if coletiva:
        tabela_coletiva = common.tabela(
            ["Pos.", "Turma", "Pontos", "Classificados", "Melhores classificados"],
            [[linha.posicao, linha.turma, linha.total_pontos, linha.classificados, linha.detalhe]
             for linha in coletiva],
        )
    else:
        tabela_coletiva = common.aviso("Sem classificação coletiva (turmas incompletas).")

    # ------------------------------------------------------------------
    # Apurados
    # ------------------------------------------------------------------
    apurados = controlador.apurados()
    tabela_apurados = (
        common.tabela(
            ["Escalão", "Pos.", "Dorsal", "Nome", "Turma"],
            [[item["grupo"], item["posicao"], item["dorsal"], item["aluno"], item["turma"]]
             for item in apurados],
        )
        if apurados else common.aviso("Ainda não existem apurados definidos.")
    )

    vista = ft.Column(
        [
            common.titulo("Classificações"),
            common.subtitulo(
                "As classificações são calculadas automaticamente a partir da ordem de chegada, "
                "excluindo desistências e desclassificações."
            ),
            indicadores,
            common.cartao(
                ft.Text(f"Classificação geral ({len(geral)})", size=15,
                        weight=ft.FontWeight.BOLD),
                tabela_geral,
            ),
            common.cartao(
                ft.Text("Classificação por escalão/sexo", size=15, weight=ft.FontWeight.BOLD),
                ft.Row([seletor_grupo]), area_grupo,
            ),
            common.cartao(
                ft.Text("Classificação coletiva por turma", size=15,
                        weight=ft.FontWeight.BOLD),
                common.subtitulo(
                    "Soma das posições obtidas nos respetivos escalões/sexo. "
                    "Menor pontuação = melhor classificação."
                ),
                tabela_coletiva,
            ),
            common.cartao(
                ft.Text("Apurados para a fase seguinte", size=15,
                        weight=ft.FontWeight.BOLD),
                tabela_apurados,
            ),
        ],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )
    mostrar_grupo()
    return vista
