"""Ecrã de autenticação (formulário diretamente sobre a fotografia da prova)."""

from __future__ import annotations

import flet as ft

from ..controllers.base import ErroValidacao
from . import common

#: Largura do formulário.
LARGURA_FORMULARIO = 420

#: Texto claro sobre a fotografia.
TEXTO_CLARO = "#FFFFFF"
TEXTO_SUAVE_CLARO = "#CDE3D6"
LINHA_CLARA = "#33FFFFFF"


def _campo(rotulo: str, icone, password: bool = False) -> ft.TextField:
    """Campo branco: sobre a fotografia, garante contraste para texto e ícones."""
    campo = ft.TextField(
        label=rotulo,
        password=password,
        can_reveal_password=password,
        prefix_icon=icone,
        text_size=13,
        filled=True,
        fill_color="#FFFFFF",
        border_color="#FFFFFF",
        focused_border_color=common.VERDE,
        border_radius=10,
    )
    # Sem altura fixa: o campo cresce o suficiente para o rótulo flutuante
    # ficar dentro da moldura (com `height` fixo o rótulo era desenhado fora).
    campo.content_padding = ft.padding.symmetric(horizontal=14, vertical=12)
    return campo


def _emblema(altura: int = 64) -> ft.Control:
    """Só o emblema do logótipo.

    A legenda "Desporto Escolar" é verde e desapareceria sobre a fotografia
    escura; a versão recortada é gerada em `cortamato/utils/logo.py`.
    """
    ficheiro = common.EMBLEMA
    if not (common.PASTA_ASSETS / ficheiro).is_file():
        ficheiro = common.LOGO
    return ft.Image(
        src=ficheiro,
        height=altura,
        fit=ft.ImageFit.CONTAIN,
        semantics_label="Desporto Escolar",
    )


def _cabecalho() -> ft.Control:
    return ft.Column(
        [
            _emblema(),
            ft.Text(
                "Corta-Mato Escolar",
                size=26,
                weight=ft.FontWeight.BOLD,
                color=TEXTO_CLARO,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Container(width=44, height=4, bgcolor=common.VERMELHO, border_radius=2),
        ],
        spacing=10,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )


def construir(app) -> ft.Control:
    campo_utilizador = _campo("Utilizador", ft.Icons.PERSON_OUTLINE)
    campo_utilizador.autofocus = True
    campo_password = _campo("Palavra-passe", ft.Icons.LOCK_OUTLINE, password=True)

    estado = ft.Text("", size=12, color=common.ERRO, expand=True)
    aviso_erro = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.ERROR_OUTLINE, size=15, color=common.ERRO),
                estado,
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor="#FDEDEB",
        border=ft.border.all(1, "#F5C9C4"),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        visible=False,
    )

    def entrar(_evento=None):
        aviso_erro.visible = False
        try:
            app.auth.autenticar(campo_utilizador.value or "", campo_password.value or "")
        except ErroValidacao as erro:
            estado.value = str(erro)
            aviso_erro.visible = True
            app.page.update()
            return
        app.mostrar_aplicacao("inicio")

    def limpar_erro(_evento=None):
        if aviso_erro.visible:
            aviso_erro.visible = False
            estado.value = ""
            app.page.update()

    campo_utilizador.on_change = limpar_erro
    campo_password.on_change = limpar_erro
    campo_password.on_submit = entrar

    # Em ecrãs estreitos o formulário encolhe para caber no telemóvel.
    largura_ecra = getattr(app.page, "width", None)
    largura = LARGURA_FORMULARIO
    if largura_ecra:
        largura = max(240, min(LARGURA_FORMULARIO, int(largura_ecra) - 48))

    # Sem cartão branco: o formulário assenta diretamente na fotografia.
    formulario = ft.Container(
        content=ft.Column(
            [
                _cabecalho(),
                ft.Container(height=4),
                ft.Container(height=1, bgcolor=LINHA_CLARA),
                ft.Container(height=2),
                ft.Text(
                    "Iniciar sessão",
                    size=13,
                    weight=ft.FontWeight.BOLD,
                    color=TEXTO_CLARO,
                ),
                campo_utilizador,
                campo_password,
                aviso_erro,
                ft.ElevatedButton(
                    "Entrar",
                    icon=ft.Icons.LOGIN,
                    on_click=entrar,
                    width=largura,
                    height=48,
                    bgcolor=common.VERDE,
                    color="#FFFFFF",
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        elevation=0,
                        text_style=ft.TextStyle(size=13, weight=ft.FontWeight.BOLD),
                    ),
                ),
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        width=largura,
    )

    conteudo = ft.Container(
        content=ft.Column(
            [
                formulario,
                ft.Container(height=18),
                ft.Text(
                    "Desporto Escolar · Agrupamento de Escolas de Padre Benjamim Salgado",
                    size=10,
                    color="#B9D8C6",
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        ),
        expand=True,
        padding=24,
    )

    # ------------------------------------------------------------------
    # Fundo fotográfico com camada de escurecimento
    # ------------------------------------------------------------------
    imagem = common.imagem_fundo()
    camadas: list[ft.Control] = [
        ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[common.VERDE_ESCURO, common.VERDE_PROFUNDO],
            ),
        )
    ]
    if imagem:
        camadas.append(
            ft.Container(
                expand=True,
                bgcolor=common.VERDE_PROFUNDO,
                image=common.fundo(imagem, 0.3),
            )
        )
    camadas.append(
        ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=["#66033A23", "#D9033A23"],
            ),
        )
    )
    camadas.append(ft.Container(content=conteudo, expand=True))

    return ft.Stack(camadas, expand=True, fit=ft.StackFit.EXPAND)
