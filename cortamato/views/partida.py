"""Vista do secretariado de partida (entrega de dorsais e listas de partida)."""

from __future__ import annotations

import flet as ft

from ..controllers.base import ErroValidacao, PermissaoNegada
from . import common


def _tabela_participantes(participantes: list[dict], ao_cancelar) -> ft.Control:
    if not participantes:
        return common.aviso("Ainda não existem dorsais entregues.")

    linhas = []
    for item in participantes:
        linhas.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(str(item["dorsal"]), size=12,
                                        weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(item["aluno"], size=12)),
                    ft.DataCell(ft.Text(item["numero"] or "—", size=12)),
                    ft.DataCell(ft.Text(item["turma"] or "—", size=12)),
                    ft.DataCell(ft.Text(item["escalao"] or "—", size=12)),
                    ft.DataCell(ft.Text({"entregue": "Entregue", "desistente": "Desistente",
                                         "desclassificado": "Desclassificado",
                                         "pendente": "Pendente"}.get(item["estado"], item["estado"]),
                                        size=12)),
                    ft.DataCell(ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        tooltip="Cancelar participação",
                        icon_size=16,
                        on_click=lambda _e, pid=item["participacao_id"]: ao_cancelar(pid),
                    )),
                ]
            )
        )

    return ft.Row([
        ft.DataTable(
            columns=[ft.DataColumn(ft.Text(coluna, size=12, weight=ft.FontWeight.BOLD,
                                           color="#FFFFFF"))
                     for coluna in ["Dorsal", "Nome", "Nº", "Turma", "Escalão",
                                    "Estado", ""]],
            rows=linhas,
            heading_row_color=common.VERDE,
            column_spacing=18,
        )
    ], scroll=ft.ScrollMode.AUTO)


def construir(app) -> ft.Control:
    page = app.page
    controlador = app.partida

    participantes = controlador.listar_participantes()
    sem_dorsal = controlador.inscritos_sem_dorsal()

    proximo = controlador.proximo_dorsal()
    campo_dorsal = common.campo("Dorsal a entregar", str(proximo), 180)
    seletor_inscrito = common.menu_suspenso(
        "Inscrito sem dorsal",
        [(item["inscricao_id"],
          f"{item['aluno']} — {item['numero'] or 's/n'} ({item['turma'] or 'sem turma'} · "
          f"{item['escalao'] or 'sem escalão'})")
         for item in sem_dorsal],
        largura=520,
    )
    campo_leitura = common.campo("Leitura do QRCode do cartão de aluno (opcional)", "", 360)

    def entregar(_evento):
        try:
            resultado = controlador.entregar_dorsal(
                int(seletor_inscrito.value) if seletor_inscrito.value else 0,
                campo_dorsal.value or "",
            )
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        common.mensagem(
            page, f"Dorsal {resultado['dorsal']} entregue a {resultado['aluno']}."
        )
        app.navegar("partida")

    def ler_cartao(_evento):
        codigo = (campo_leitura.value or "").strip()
        if not codigo:
            common.mensagem(page, "Introduza ou leia o código do cartão.", erro=True)
            return
        aluno = app.configuracoes.aluno_por_cartao(codigo)
        if not aluno:
            common.mensagem(page, "Cartão não encontrado. Use a seleção manual.", erro=True)
            return
        campo_leitura.value = ""
        common.mensagem(
            page,
            f"Aluno identificado: {aluno['nome']} ({aluno.get('turma') or 'sem turma'}). "
            "Selecione-o na lista para confirmar a entrega do dorsal.",
        )
        page.update()

    def cancelar(participacao_id: int):
        try:
            controlador.cancelar_participacao(int(participacao_id))
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        common.mensagem(page, "Participação cancelada.")
        app.navegar("partida")

    # ------------------------------------------------------------------
    # Listas de partida
    # ------------------------------------------------------------------
    grupos = controlador.listas_de_partida()
    opcoes_grupos = [(grupo["grupo"], grupo["grupo"]) for grupo in grupos]
    seletor_grupo = common.menu_suspenso("Escalão/sexo", opcoes_grupos, largura=320)
    area_lista = ft.Column([], spacing=8)

    def mostrar_lista(_evento=None):
        if not grupos:
            area_lista.controls = [common.aviso("Sem participantes para listar.")]
            page.update()
            return
        grupo = next(
            (item for item in grupos if item["grupo"] == seletor_grupo.value), grupos[0]
        )
        area_lista.controls = [
            ft.Text(f"{grupo['grupo']} — {len(grupo['participantes'])} atletas", size=13,
                    weight=ft.FontWeight.BOLD),
            common.tabela(
                ["Dorsal", "Nome", "Nº", "Turma"],
                [[linha["dorsal"], linha["aluno"], linha["numero"] or "—",
                  linha["turma"] or "—"] for linha in grupo["participantes"]],
            ),
        ]
        page.update()

    if grupos and not seletor_grupo.value:
        seletor_grupo.value = grupos[0]["grupo"]
    seletor_grupo.on_change = mostrar_lista

    bloco_entrega = common.cartao(
        ft.Text("Entrega de dorsais", size=15, weight=ft.FontWeight.BOLD),
        common.subtitulo(
            f"Próximo dorsal disponível: {proximo}. O sistema associa o dorsal ao cartão de "
            "aluno, permitindo depois a leitura automática na meta."
        ),
        ft.Row([seletor_inscrito], wrap=True),
        ft.Row([campo_dorsal, common.botao("Entregar dorsal", entregar,
                                           icone=ft.Icons.CONFIRMATION_NUMBER)]),
        common.separador(),
        ft.Text("Procedimento manual alternativo", size=13, weight=ft.FontWeight.BOLD),
        common.subtitulo(
            "Se o QRCode não puder ser lido, identifique o aluno pelo número ou pelo nome "
            "e introduza o dorsal manualmente."
        ),
        ft.Row([campo_leitura,
                common.botao("Procurar cartão", ler_cartao, principal=False,
                             icone=ft.Icons.QR_CODE)]),
        common.aviso(
            "Participantes inscritos como «Organização» não recebem dorsal de prova."
        ),
    )

    bloco_lista_geral = common.cartao(
        ft.Text(f"Participantes com dorsal ({len(participantes)})", size=15,
                weight=ft.FontWeight.BOLD),
        _tabela_participantes(participantes, cancelar),
    )

    bloco_listas = common.cartao(
        ft.Text("Listas de partida", size=15, weight=ft.FontWeight.BOLD),
        ft.Row([seletor_grupo]), area_lista,
    )

    vista = ft.Column(
        [common.titulo("Secretariado de partida"),
         bloco_entrega,
         bloco_lista_geral,
         bloco_listas],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )
    mostrar_lista()
    return vista
