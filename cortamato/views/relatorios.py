"""Vista de relatórios, exportações e comunicação aos diretores de turma."""

from __future__ import annotations

import flet as ft

from ..controllers.base import ErroValidacao, PermissaoNegada
from . import common


def construir(app) -> ft.Control:
    page = app.page
    controlador = app.relatorios

    area_preview = ft.Column(
        [common.aviso("Escolha um relatório para pré-visualizar os dados.")],
        spacing=8,
    )

    def previsualizar(chave: str):
        try:
            relatorio = controlador.obter(chave)
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        except Exception as erro:  # noqa: BLE001
            common.mensagem(page, f"Erro ao gerar o relatório: {erro}", erro=True)
            return

        controlos: list[ft.Control] = [
            ft.Text(relatorio["titulo"], size=15, weight=ft.FontWeight.BOLD),
            common.subtitulo(relatorio["subtitulo"]),
        ]
        for linha in relatorio["resumo"]:
            controlos.append(ft.Text(linha, size=11, color=common.TEXTO_SUAVE))
        controlos.append(
            common.tabela(relatorio["cabecalho"], relatorio["registos"])
            if relatorio["registos"]
            else common.aviso("Este relatório não tem registos para apresentar.")
        )
        area_preview.controls = controlos
        page.update()

    def exportar(chave: str, formato: str):
        try:
            destino = controlador.exportar(chave, formato)
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        common.mensagem(page, f"Ficheiro gerado: {destino}")

    blocos = []
    for chave, titulo in controlador.definicoes():
        blocos.append(
            common.cartao(
                ft.Text(titulo, size=14, weight=ft.FontWeight.BOLD),
                ft.Row([
                    common.botao("Pré-visualizar",
                                 lambda _e, c=chave: previsualizar(c), principal=False),
                    common.botao("Exportar PDF", lambda _e, c=chave: exportar(c, "pdf")),
                    common.botao("Exportar CSV",
                                 lambda _e, c=chave: exportar(c, "csv"), principal=False),
                ], wrap=True, spacing=8),
            )
        )

    # ------------------------------------------------------------------
    # Comunicação aos diretores de turma
    # ------------------------------------------------------------------
    area_mensagem = common.campo(
        "Mensagem a enviar aos diretores de turma", "", 900,
        multiline=True, min_lines=12, max_lines=20,
    )

    def ver_mensagem(_evento):
        try:
            dados = controlador.comunicacao_dt()
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        area_mensagem.value = dados["corpo"]
        common.mensagem(
            page,
            f"Mensagem preparada para {len(dados['por_turma'])} turma(s) e "
            f"{len(dados['destinatarios'])} destinatário(s).",
        )
        page.update()

    def guardar_mensagem(_evento):
        try:
            texto, eml = controlador.exportar_comunicacao()
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        common.mensagem(page, f"Mensagem guardada em {texto} e {eml}")

    bloco_comunicacao = common.cartao(
        ft.Text("Comunicação aos diretores de turma", size=15, weight=ft.FontWeight.BOLD),
        common.subtitulo(
            "A mensagem agrupa os alunos por turma, distinguindo participantes e elementos de "
            "apoio à organização, e destina-se à justificação de faltas."
        ),
        ft.Row([
            common.botao("Gerar mensagem", ver_mensagem, icone=ft.Icons.EMAIL),
            common.botao("Guardar (.txt /.eml)", guardar_mensagem, principal=False,
                         icone=ft.Icons.SAVE),
        ], wrap=True, spacing=10),
        area_mensagem,
    )

    bloco_exportacoes = common.cartao(
        ft.Text("Pasta de exportações", size=15, weight=ft.FontWeight.BOLD),
        common.subtitulo(
            "Os ficheiros são guardados em «exportacoes» (PDF/CSV) e em «comunicacoes» "
            "(mensagens .txt/.eml), dentro da pasta do projeto."
        ),
    )

    return ft.Column(
        [
            common.titulo("Relatórios e exportações"),
            bloco_exportacoes,
            *blocos,
            common.cartao(
                ft.Text("Pré-visualização", size=15, weight=ft.FontWeight.BOLD),
                area_preview,
            ),
            bloco_comunicacao,
        ],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )
