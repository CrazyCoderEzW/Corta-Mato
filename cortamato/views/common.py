
"""Componentes visuais reutilizáveis (identidade gráfica Desporto Escolar).

Toda a aplicação usa este módulo como sistema de design: cores da marca,
cartões, botões, campos, tabelas, indicadores e mensagens.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import flet as ft

from ..utils import datas
from ..utils import logo as logo_util

# ---------------------------------------------------------------------------
# Identidade visual Desporto Escolar
# ---------------------------------------------------------------------------
VERMELHO = "#E1251B"
VERMELHO_ESCURO = "#B71C13"
VERDE = "#007A3D"
VERDE_ESCURO = "#045532"
VERDE_PROFUNDO = "#033A23"
VERDE_CLARO = "#E6F3EC"
VERDE_TEXTO = "#0B5C36"
AZUL = "#123B7A"
AMARELO = "#FFC72C"

CINZA_FUNDO = "#F1F5F2"
CINZA_BORDA = "#DCE5DE"
CINZA_SUAVE = "#F7FAF8"
TEXTO = "#15211B"
TEXTO_SUAVE = "#5C6B62"
ERRO = "#B3261E"
AVISO = "#8A6100"

#: Ficheiro do logotipo (pasta `assets` do projeto).
LOGO = "desporto_escolar.png"

#: Emblema recortado, sem a legenda verde (para fundos escuros).
EMBLEMA = "desporto_escolar_emblema.png"

#: Pasta de recursos gráficos da aplicação.
PASTA_ASSETS = Path(__file__).resolve().parents[2] / "assets"

# Garante o logótipo sem fundo em `assets` (ver `cortamato/utils/logo.py`).
try:
    logo_util.instalar(PASTA_ASSETS, LOGO)
except Exception:  # noqa: BLE001 - o logótipo nunca deve impedir o arranque
    pass

#: Nomes aceites para a fotografia de fundo (basta colocar o ficheiro em `assets`).
NOMES_FUNDO = (
    "fundo_cortamato.jpg",
    "fundo_cortamato.jpeg",
    "fundo_cortamato.png",
    "fundo.jpg",
    "fundo.jpeg",
    "fundo.png",
)


def imagem_fundo() -> str | None:
    """Devolve o ficheiro de fundo disponível em `assets`, se existir."""
    for nome in NOMES_FUNDO:
        if (PASTA_ASSETS / nome).is_file():
            return nome
    return None


def fundo(src: str, opacidade: float = 0.35) -> ft.DecorationImage:
    """Fotografia de fundo esbatida sobre a cor do contentor (efeito de tonalidade)."""
    return ft.DecorationImage(
        src=src,
        fit=ft.ImageFit.COVER,
        opacity=opacidade,
        alignment=ft.Alignment(0, 0),
    )

SOMBRA = ft.BoxShadow(
    blur_radius=16,
    spread_radius=0,
    color="#12033A23",
    offset=ft.Offset(0, 3),
)


def _tom(cor: str, alfa: str = "1A") -> str:
    """Devolve a cor com transparência (formato #AARRGGBB) para fundos suaves."""
    if cor.startswith("#") and len(cor) == 7:
        return f"#{alfa}{cor[1:]}"
    return cor


# ---------------------------------------------------------------------------
# Marca
# ---------------------------------------------------------------------------
def marca(altura: int = 54, fundo: str | None = "#FFFFFF", espaco: int = 10,
          raio: int = 12, largura: int | None = None) -> ft.Container:
    """Logotipo oficial do Desporto Escolar sobre fundo claro.

    Com `fundo=None` o logotipo é mostrado sem placa de fundo, para ficheiros
    PNG transparentes colocados diretamente sobre cartões claros.
    """
    return ft.Container(
        content=ft.Image(
            src=LOGO,
            height=altura,
            fit=ft.ImageFit.CONTAIN,
            semantics_label="Desporto Escolar",
        ),
        bgcolor=fundo,
        padding=espaco,
        width=largura,
        border_radius=raio,
        alignment=ft.Alignment(0, 0),
    )


# ---------------------------------------------------------------------------
# Tipografia
# ---------------------------------------------------------------------------
def titulo(texto: str) -> ft.Text:
    return ft.Text(texto, size=24, weight=ft.FontWeight.BOLD, color=TEXTO)


def subtitulo(texto: str) -> ft.Text:
    return ft.Text(texto, size=13, color=TEXTO_SUAVE)


def titulo_seccao(texto: str, icone=None, cor: str = VERDE) -> ft.Control:
    """Cabeçalho de cartão: ícone em destaque + título."""
    elementos: list[ft.Control] = []
    if icone is not None:
        elementos.append(
            ft.Container(
                content=ft.Icon(icone, size=16, color=cor),
                bgcolor=_tom(cor),
                width=28,
                height=28,
                border_radius=8,
                alignment=ft.Alignment(0, 0),
            )
        )
    elementos.append(
        ft.Text(texto, size=14, weight=ft.FontWeight.BOLD, color=TEXTO, expand=True)
    )
    return ft.Row(elementos, spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)


# ---------------------------------------------------------------------------
# Estrutura
# ---------------------------------------------------------------------------
def cartao(*controlos, expandir: bool = False, largura: int | None = None,
           visivel: bool = True, espacamento: int = 12, preenchimento: int = 18,
           col=None) -> ft.Container:
    grelha = {} if col is None else {"col": col}
    return ft.Container(
        content=ft.Column(list(controlos), spacing=espacamento, tight=True),
        bgcolor="#FFFFFF",
        padding=preenchimento,
        border=ft.border.all(1, CINZA_BORDA),
        border_radius=14,
        shadow=SOMBRA,
        expand=expandir,
        width=largura,
        visible=visivel,
        **grelha,
    )


def separador() -> ft.Divider:
    return ft.Divider(height=1, color=CINZA_BORDA)


def vazio(texto: str, icone=None) -> ft.Container:
    """Estado vazio para listas e tabelas sem registos."""
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(icone or ft.Icons.INBOX_OUTLINED, size=18, color="#93A69A"),
                ft.Text(texto, size=12, color=TEXTO_SUAVE, expand=True),
            ],
            spacing=10,
        ),
        bgcolor=CINZA_SUAVE,
        border=ft.border.all(1, CINZA_BORDA),
        border_radius=10,
        padding=14,
    )


def etiqueta(texto: str, cor: str = VERDE) -> ft.Container:
    return ft.Container(
        content=ft.Text(texto, size=10, color="#FFFFFF", weight=ft.FontWeight.BOLD),
        bgcolor=cor,
        padding=ft.padding.symmetric(horizontal=9, vertical=3),
        border_radius=20,
    )


def aviso(texto: str, cor: str = AVISO) -> ft.Container:
    fundo = "#FFF8E1" if cor == AVISO else _tom(cor, "14")
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=cor),
                ft.Text(texto, size=12, color=cor, expand=True),
            ],
            spacing=8,
        ),
        bgcolor=fundo,
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border_radius=10,
    )


# ---------------------------------------------------------------------------
# Indicadores
# ---------------------------------------------------------------------------
def indicador(rotulo: str, valor, icone=None, cor: str = VERDE,
              largura: int | None = 190, col=None) -> ft.Container:
    grelha = {} if col is None else {"col": col}
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(icone or ft.Icons.INSIGHTS, size=17, color=cor),
                            bgcolor=_tom(cor),
                            width=30,
                            height=30,
                            border_radius=9,
                            alignment=ft.Alignment(0, 0),
                        ),
                        ft.Text(
                            rotulo.upper(),
                            size=9,
                            color=TEXTO_SUAVE,
                            weight=ft.FontWeight.BOLD,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            expand=True,
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(str(valor), size=26, weight=ft.FontWeight.BOLD, color=TEXTO),
            ],
            spacing=8,
            tight=True,
        ),
        bgcolor="#FFFFFF",
        padding=14,
        border=ft.border.all(1, CINZA_BORDA),
        border_radius=12,
        shadow=SOMBRA,
        width=None if col is not None else largura,
        **grelha,
    )


# ---------------------------------------------------------------------------
# Tabelas
# ---------------------------------------------------------------------------
def tabela(cabecalho: list[str], linhas: list[list]) -> ft.Control:
    """Tabela com deslocamento apenas horizontal (a página trata do vertical)."""
    return ft.Row(
        [
            ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text(coluna, size=11.5))
                    for coluna in cabecalho
                ],
                rows=[
                    ft.DataRow(
                        cells=[
                            ft.DataCell(
                                valor
                                if isinstance(valor, ft.Control)
                                else ft.Text(str(valor), size=12, color=TEXTO)
                            )
                            for valor in linha
                        ]
                    )
                    for linha in linhas
                ],
                heading_row_color=VERDE_ESCURO,
                heading_text_style=ft.TextStyle(
                    size=11.5, weight=ft.FontWeight.BOLD, color="#FFFFFF"
                ),
                data_text_style=ft.TextStyle(size=12, color=TEXTO),
                heading_row_height=42,
                data_row_min_height=40,
                data_row_max_height=52,
                divider_thickness=0.6,
                horizontal_lines=ft.BorderSide(1, CINZA_BORDA),
                column_spacing=22,
                border_radius=10,
            )
        ],
        scroll=ft.ScrollMode.AUTO,
    )


# ---------------------------------------------------------------------------
# Formulários
# ---------------------------------------------------------------------------
def campo(rotulo: str, valor: str = "", largura: int = 240, **extra) -> ft.TextField:
    extra.setdefault("filled", True)
    extra.setdefault("fill_color", CINZA_SUAVE)
    extra.setdefault("border_radius", 10)
    extra.setdefault("border_color", CINZA_BORDA)
    extra.setdefault("focused_border_color", VERDE)
    extra.setdefault("content_padding", ft.padding.symmetric(horizontal=12, vertical=14))
    return ft.TextField(label=rotulo, value=str(valor or ""), width=largura, **extra)


def menu_suspenso(rotulo: str, opcoes: list[tuple[str, str]], valor: str | None = None,
                  largura: int | None = 240, ao_mudar=None, **extra) -> ft.Dropdown:
    return ft.Dropdown(
        label=rotulo,
        width=largura,
        value=valor if valor not in (None, "") else None,
        options=[ft.dropdown.Option(key=str(chave), text=str(texto)) for chave, texto in opcoes],
        on_change=ao_mudar,
        filled=True,
        fill_color=CINZA_SUAVE,
        border_radius=10,
        border_color=CINZA_BORDA,
        focused_border_color=VERDE,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
        **extra,
    )


class CampoData:
    """Campo de data (dd/mm/aaaa) com o calendário do Flet à direita.

    O texto pode ser escrito à mão; o botão abre o `ft.DatePicker` e devolve a
    data escolhida já no formato português.
    """

    def __init__(self, page: ft.Page, rotulo: str, valor: str = "",
                 largura: int | None = 240, expandir: int = 0) -> None:
        self.page = page
        inicial = datas.converter_data(str(valor or ""))
        self.campo = campo(
            rotulo,
            inicial.strftime("%d/%m/%Y") if inicial else str(valor or ""),
            largura,
            hint_text="dd/mm/aaaa",
            **({"expand": expandir} if expandir else {}),
        )
        self.botao = ft.IconButton(
            icon=ft.Icons.CALENDAR_MONTH,
            tooltip="Escolher no calendário",
            icon_color=VERDE_TEXTO,
            on_click=self.abrir,
        )
        self.control = ft.Row(
            [self.campo, self.botao],
            spacing=2,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            **({"expand": expandir} if expandir else {}),
        )

    @property
    def value(self) -> str:
        return self.campo.value or ""

    @value.setter
    def value(self, novo: str | None) -> None:
        self.campo.value = str(novo or "")

    def abrir(self, _evento=None) -> None:
        atual = datas.converter_data(self.campo.value)
        seletor = ft.DatePicker(
            first_date=datetime(1970, 1, 1),
            last_date=datetime(2100, 12, 31),
            value=datetime(atual.year, atual.month, atual.day) if atual else None,
            help_text=self.campo.label,
            on_change=self._escolher,
        )
        self.page.open(seletor)

    def _escolher(self, evento) -> None:
        escolhida = evento.control.value
        if not escolhida:
            return
        if isinstance(escolhida, date):
            self.campo.value = escolhida.strftime("%d/%m/%Y")
        else:
            self.campo.value = datas.formatar_data(str(escolhida))
        self.page.update()


def campo_data(page: ft.Page, rotulo: str, valor: str = "",
               largura: int | None = 240, expandir: int = 0) -> CampoData:
    return CampoData(page, rotulo, valor, largura, expandir)


def _estilo_botao(cor: str, preenchido: bool) -> ft.ButtonStyle:
    return ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=10),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        elevation=0 if preenchido else 0,
        color="#FFFFFF" if preenchido else VERDE_TEXTO,
        bgcolor=cor if preenchido else None,
        overlay_color=_tom(cor, "1F"),
        side=None if preenchido else ft.BorderSide(1, CINZA_BORDA),
    )


def botao(texto: str, ao_clicar, principal: bool = True, icone=None) -> ft.Control:
    if principal:
        return ft.ElevatedButton(
            texto,
            on_click=ao_clicar,
            icon=icone,
            height=42,
            bgcolor=VERDE,
            color="#FFFFFF",
            style=_estilo_botao(VERDE, True),
        )
    return ft.OutlinedButton(
        texto,
        on_click=ao_clicar,
        icon=icone,
        height=42,
        style=_estilo_botao(VERDE, False),
    )


def linha_info(rotulo: str, valor: str) -> ft.Row:
    return ft.Row(
        [
            ft.Text(rotulo, size=12, color=TEXTO_SUAVE, width=200),
            ft.Text(str(valor), size=12, color=TEXTO, weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.RIGHT, expand=True),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


# ---------------------------------------------------------------------------
# Mensagens
# ---------------------------------------------------------------------------
def mensagem(page: ft.Page, texto: str, erro: bool = False) -> None:
    try:
        page.open(
            ft.SnackBar(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.ERROR_OUTLINE if erro else ft.Icons.CHECK_CIRCLE_OUTLINE,
                            size=16,
                            color="#FFFFFF",
                        ),
                        ft.Text(texto, color="#FFFFFF", size=12, expand=True),
                    ],
                    spacing=8,
                ),
                bgcolor=ERRO if erro else VERDE_ESCURO,
                behavior=ft.SnackBarBehavior.FLOATING,
                margin=ft.margin.all(24),
                shape=ft.RoundedRectangleBorder(radius=10),
            )
        )
    except Exception:
        page.update()
