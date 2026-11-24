"""Vista do secretariado de meta: chegadas, desistências e desclassificações."""

from __future__ import annotations

import flet as ft

from ..controllers.base import ErroValidacao, PermissaoNegada
from . import common


def construir(app) -> ft.Control:
    page = app.page
    controlador = app.meta
    resumo = controlador.resumo()
    ultima = controlador.ultima_chegada()

    # ------------------------------------------------------------------
    # Registo de chegadas
    # ------------------------------------------------------------------
    campo_dorsal = ft.TextField(
        label="Dorsal à chegada", width=220, autofocus=True, hint_text="Ex.: 42"
    )
    campo_cartao = common.campo("Leitura do QRCode do cartão (alternativo)", "", 300)

    def registar_por_dorsal(_evento=None):
        try:
            resultado = controlador.registar_por_dorsal(campo_dorsal.value or "", "qr")
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        common.mensagem(
            page,
            f"{resultado['ordem']}º — dorsal {resultado['dorsal']} · {resultado['aluno']} "
            f"({resultado['turma']})",
        )
        app.navegar("meta")

    campo_dorsal.on_submit = registar_por_dorsal

    def registar_por_cartao(_evento):
        try:
            resultado = controlador.registar_por_cartao(campo_cartao.value or "", "qr")
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        common.mensagem(
            page, f"{resultado['ordem']}º — {resultado['aluno']} ({resultado['turma']})"
        )
        app.navegar("meta")

    def desfazer(_evento):
        removido = controlador.desfazer_ultima()
        if removido is None:
            common.mensagem(page, "Não existem chegadas para remover.", erro=True)
            return
        common.mensagem(page, "Última chegada removida e ordem renumerada.")
        app.navegar("meta")

    estado_ultima = (
        f"{ultima['ordem']}º — dorsal {ultima['dorsal']} · {ultima['aluno']} "
        f"({ultima['turma'] or '—'}) às {ultima['hora']}"
        if ultima else "Ainda não foram registadas chegadas."
    )

    bloco_registo = common.cartao(
        ft.Row([
            common.indicador("Próxima ordem", resumo["ordem_seguinte"], ft.Icons.TIMER),
            common.indicador("Chegadas", resumo["chegadas"], ft.Icons.FLAG),
            common.indicador("Participantes", resumo["participantes"], ft.Icons.DIRECTIONS_RUN),
            common.indicador("Desistências", resumo["desistentes"], ft.Icons.PERSON_OFF),
            common.indicador("Desclassificados", resumo["desclassificados"], ft.Icons.BLOCK),
        ], wrap=True, spacing=12),
        common.separador(),
        ft.Text("Registo de chegadas", size=15, weight=ft.FontWeight.BOLD),
        common.subtitulo(
            "O registo é feito pela leitura do dorsal no funil de meta. "
            "A ordem de chegada é atribuída automaticamente."
        ),
        ft.Row([
            campo_dorsal,
            common.botao("Registar chegada", registar_por_dorsal, icone=ft.Icons.PLAY_ARROW),
            common.botao("Desfazer última", desfazer, principal=False, icone=ft.Icons.UNDO),
        ], wrap=True, spacing=12),
        ft.Row([campo_cartao,
                common.botao("Registar por cartão", registar_por_cartao, principal=False,
                             icone=ft.Icons.QR_CODE)], wrap=True, spacing=12),
        common.aviso(f"Última chegada: {estado_ultima}"),
    )

    # ------------------------------------------------------------------
    # Tabela de chegadas com correção
    # ------------------------------------------------------------------
    def abrir_correcao(chegada_id: int, ordem_atual: int):
        campo_posicao = ft.TextField(label="Nova posição", value=str(ordem_atual), width=160)
        dialogo = ft.AlertDialog(
            title=ft.Text("Corrigir ordem de chegada"),
            content=ft.Column([
                ft.Text("A lista é renumerada automaticamente após a correção.", size=12),
                campo_posicao,
            ], spacing=10, tight=True),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _e: page.close(dialogo)),
                ft.ElevatedButton("Guardar", on_click=lambda _e: confirmar_correcao()),
            ],
        )

        def confirmar_correcao():
            try:
                controlador.mover_chegada(chegada_id, campo_posicao.value or "")
            except (ErroValidacao, PermissaoNegada) as erro:
                page.close(dialogo)
                common.mensagem(page, str(erro), erro=True)
                return
            page.close(dialogo)
            common.mensagem(page, "Ordem de chegada corrigida.")
            app.navegar("meta")

        page.open(dialogo)

    chegadas = controlador.listar_chegadas(100)
    if chegadas:
        linhas = []
        for item in chegadas:
            linhas.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(item["ordem"]), size=12,
                                        weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(str(item["dorsal"]), size=12)),
                    ft.DataCell(ft.Text(item["aluno"], size=12)),
                    ft.DataCell(ft.Text(item["turma"] or "—", size=12)),
                    ft.DataCell(ft.Text(item["escalao"] or "—", size=12)),
                    ft.DataCell(ft.Text(item["hora"], size=11)),
                    ft.DataCell(ft.Text("QRCode" if item["metodo"] == "qr" else "Manual",
                                        size=11)),
                    ft.DataCell(ft.IconButton(
                        icon=ft.Icons.EDIT,
                        tooltip="Corrigir ordem",
                        icon_size=16,
                        on_click=lambda _e, cid=item["chegada_id"], pos=item["ordem"]:
                            abrir_correcao(cid, pos),
                    )),
                ])
            )
        tabela_chegadas: ft.Control = ft.Row([
            ft.DataTable(
                columns=[ft.DataColumn(ft.Text(coluna, size=12,
                                               weight=ft.FontWeight.BOLD, color="#FFFFFF"))
                         for coluna in ["Ord.", "Dorsal", "Nome", "Turma", "Escalão",
                                        "Hora", "Método", ""]],
                rows=linhas,
                heading_row_color=common.VERDE,
                column_spacing=18,
            )
        ], scroll=ft.ScrollMode.AUTO)
    else:
        tabela_chegadas = common.aviso("Sem chegadas registadas.")

    # ------------------------------------------------------------------
    # Ocorrências
    # ------------------------------------------------------------------
    lista_participantes = app.partida.listar_participantes()
    seletor_participante = common.menu_suspenso(
        "Participante",
        [(item["participacao_id"],
          f"{item['dorsal']} — {item['aluno']} ({item['turma'] or 'sem turma'})")
         for item in lista_participantes],
        largura=420,
    )
    campo_motivo = common.campo("Motivo", "", 320)

    def desistir(_evento):
        try:
            controlador.registar_desistencia(
                int(seletor_participante.value) if seletor_participante.value else 0,
                campo_motivo.value or "",
            )
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        common.mensagem(page, "Desistência registada.")
        app.navegar("meta")

    def desclassificar(_evento):
        try:
            controlador.registar_desclassificacao(
                int(seletor_participante.value) if seletor_participante.value else 0,
                campo_motivo.value or "",
            )
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        common.mensagem(page, "Desclassificação registada.")
        app.navegar("meta")

    def repor(_evento):
        try:
            controlador.repor_participante(
                int(seletor_participante.value) if seletor_participante.value else 0
            )
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        common.mensagem(page, "Participante reposto como classificado.")
        app.navegar("meta")

    ocorrencias = controlador.listar_ocorrencias()
    bloco_ocorrencias = common.cartao(
        ft.Text("Desistências, desclassificações e correções", size=15,
                weight=ft.FontWeight.BOLD),
        ft.Row([seletor_participante], wrap=True),
        ft.Row([campo_motivo,
                common.botao("Desistência", desistir, principal=False,
                             icone=ft.Icons.PERSON_OFF),
                common.botao("Desclassificação", desclassificar, principal=False,
                             icone=ft.Icons.BLOCK)], wrap=True, spacing=12),
        ft.Row([common.botao("Repor participante", repor, principal=False,
                             icone=ft.Icons.RESTORE)]),
        common.separador(),
        common.tabela(
            ["Tipo", "Dorsal", "Nome", "Turma", "Motivo", "Hora"],
            [[item["tipo"].capitalize(), item["dorsal"], item["aluno"],
              item["turma"] or "—", item["motivo"] or "—", item["hora"]]
             for item in ocorrencias],
        ) if ocorrencias else common.aviso("Sem ocorrências registadas."),
    )

    # ------------------------------------------------------------------
    # Gráfico de evolução das chegadas (linha acumulada)
    # ------------------------------------------------------------------
    def minutos(hora) -> float | None:
        """Converte a hora da chegada (datetime, time ou texto) em minutos."""
        horas = getattr(hora, "hour", None)
        mins = getattr(hora, "minute", None)
        segs = getattr(hora, "second", 0) or 0
        if horas is None:
            partes = str(hora or "").strip().split(":")
            if len(partes) < 2:
                return None
            try:
                horas, mins = int(partes[0]), int(partes[1])
                segs = int(float(partes[2])) if len(partes) > 2 else 0
            except ValueError:
                return None
        return int(horas) * 60 + int(mins) + int(segs) / 60

    def rotulo_hora(minutos_totais: float) -> str:
        total = int(round(minutos_totais)) % (24 * 60)
        return f"{total // 60:02d}:{total % 60:02d}"

    marcados: list[tuple[float, int]] = []
    for item in chegadas:
        momento = minutos(item.get("hora"))
        if momento is not None:
            marcados.append((momento, int(item["ordem"])))
    marcados.sort()

    if marcados:
        inicio = marcados[0][0]
        pontos = [
            ft.LineChartDataPoint(x=round(momento - inicio, 1), y=ordem)
            for momento, ordem in marcados
        ]
        duracao = max(ponto.x for ponto in pontos)
        topo = max(ordem for _momento, ordem in marcados)
        grafico: ft.Control = ft.LineChart(
            data_series=[
                ft.LineChartData(
                    data_points=pontos,
                    stroke_width=3,
                    color=common.VERDE,
                    curved=True,
                    stroke_cap_round=True,
                )
            ],
            min_x=0,
            max_x=max(duracao, 1),
            min_y=0,
            max_y=max(topo, 1),
            bottom_axis=ft.ChartAxis(
                labels=[
                    ft.ChartAxisLabel(
                        value=momento,
                        label=ft.Container(
                            content=ft.Text(rotulo_hora(inicio + momento), size=9,
                                            color=common.TEXTO_SUAVE),
                            padding=ft.padding.only(top=6),
                        ),
                    )
                    for momento in sorted({0.0, round(duracao / 2, 1), round(duracao, 1)})
                ],
                labels_size=26,
            ),
            left_axis=ft.ChartAxis(labels_size=26),
            horizontal_grid_lines=ft.ChartGridLines(
                color=common.CINZA_BORDA, width=1, dash_pattern=[3, 3]
            ),
            height=170,
        )
        nota_final = common.subtitulo(
            f"{topo} chegadas em {int(round(duracao))} min "
            f"(das {rotulo_hora(inicio)} às {rotulo_hora(inicio + duracao)})."
        )
    else:
        grafico = common.vazio(
            "A evolução das chegadas aparece aqui assim que forem registadas."
        )
        nota_final = common.subtitulo(
            "Cada ponto da linha corresponde a uma chegada registada no funil de meta."
        )

    cartao_grafico = common.cartao(
        common.titulo_seccao("Evolução das chegadas", ft.Icons.SHOW_CHART),
        common.subtitulo("Chegadas acumuladas ao longo do tempo, na ordem registada."),
        grafico,
        nota_final,
    )

    return ft.Column(
        [common.titulo("Secretariado de meta"),
         bloco_registo,
         cartao_grafico,
         common.cartao(ft.Text(f"Chegadas registadas ({len(chegadas)})", size=15,
                               weight=ft.FontWeight.BOLD), tabela_chegadas),
         bloco_ocorrencias],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )
