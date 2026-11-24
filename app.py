

from __future__ import annotations

from pathlib import Path

import flet as ft

from cortamato.models.db import BD, ErroLigacaoBD
from cortamato.views import common
from cortamato.views.shell import Aplicacao

PASTA = Path(__file__).resolve().parent


def mostrar_erro_bd(page: ft.Page, mensagem: str) -> None:
    """Apresenta um aviso legível quando o servidor MySQL não está acessível."""
    page.bgcolor = common.CINZA_FUNDO
    page.add(
        ft.Column(
            controls=[
                ft.Text(
                    "Não foi possível ligar à base de dados MySQL",
                    size=22,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Text(mensagem, selectable=True, size=13),
            ],
            spacing=16,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
    )
    page.update()


def main(page: ft.Page) -> None:
    page.title = "Corta-Mato Escolar | AEPBS"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(
        color_scheme_seed=common.VERDE,
        font_family="Segoe UI",
        use_material3=True,
    )
    page.bgcolor = common.CINZA_FUNDO
    page.padding = 0
    page.spacing = 0

    page.window.width = 1320
    page.window.height = 860
    # Permite testar/redimensionar para larguras de telemóvel.
    page.window.min_width = 360
    page.window.min_height = 500

    try:
        base_dados = BD()
    except ErroLigacaoBD as erro:
        mostrar_erro_bd(page, str(erro))
        return
    Aplicacao(page, base_dados).iniciar()


if __name__ == "__main__":
    ft.app(target=main, assets_dir=str(PASTA / "assets"))
