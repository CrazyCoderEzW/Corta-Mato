"""Estrutura principal da aplicação: barra lateral, navegação e dashboard."""

from __future__ import annotations

import traceback
from datetime import date
from pathlib import Path

import flet as ft

from ..controllers.auth import ControladorAuth, Sessao
from ..controllers.base import (P_CLASSIFICACOES, P_CONFIG, P_IMPORTAR, P_INSCRICOES,
                                P_INSCRICOES_CONSULTA, P_META, P_PARTIDA, P_RELATORIOS,
                                P_RESPONSAVEIS, ErroValidacao, PermissaoNegada)
from ..controllers.classificacoes import ControladorClassificacoes
from ..controllers.configuracoes import ControladorConfiguracoes
from ..controllers.importacao import ControladorImportacao
from ..controllers.inscricoes import ControladorInscricoes
from ..controllers.meta import ControladorMeta
from ..controllers.partida import ControladorPartida
from ..controllers.relatorios import ControladorRelatorios
from ..controllers.responsaveis import ControladorResponsaveis
from ..utils import datas
from . import (classificacoes as vista_classificacoes, common, configuracoes as vista_config,
               importacoes as vista_importacoes, inscricoes as vista_inscricoes, login,
               meta as vista_meta, partida as vista_partida, relatorios as vista_relatorios,
               responsaveis as vista_responsaveis)

MENU = [
    ("inicio", "Início", ft.Icons.DASHBOARD_OUTLINED, None),
    ("configuracoes", "Configurações", ft.Icons.SETTINGS_OUTLINED, P_CONFIG),
    ("importacoes", "Importações CSV", ft.Icons.UPLOAD_FILE, P_IMPORTAR),
    ("inscricoes", "Inscrições", ft.Icons.EDIT_NOTE, P_INSCRICOES_CONSULTA),
    ("partida", "Partida (dorsais)", ft.Icons.CONFIRMATION_NUMBER, P_PARTIDA),
    ("meta", "Meta (chegadas)", ft.Icons.TIMER_OUTLINED, P_META),
    ("classificacoes", "Classificações", ft.Icons.LEADERBOARD, P_CLASSIFICACOES),
    ("relatorios", "Relatórios", ft.Icons.DESCRIPTION_OUTLINED, P_RELATORIOS),
    ("responsaveis", "Responsáveis", ft.Icons.MANAGE_ACCOUNTS, P_RESPONSAVEIS),
]

GRUPOS = [
    ("Principal", ["inicio"]),
    ("Configuração", ["configuracoes", "importacoes"]),
    ("Operação", ["inscricoes", "partida", "meta"]),
    ("Resultados", ["classificacoes", "relatorios"]),
    ("Administração", ["responsaveis"]),
]

#: Larguras da barra lateral (expandida e recolhida no modo "hambúrguer").
LARGURA_MENU = 252
LARGURA_MENU_ENCURTADA = 76

#: Abaixo desta largura a aplicação usa o layout de telemóvel (menu em gaveta).
LARGURA_MOVEL = 820



class Aplicacao:
    """Composição das vistas com os controladores (camada de apresentação)."""

    def __init__(self, page: ft.Page, bd) -> None:
        self.page = page
        self.bd = bd
        self.sessao = Sessao()

        self.auth = ControladorAuth(bd, self.sessao)
        self.responsaveis = ControladorResponsaveis(bd, self.sessao)
        self.configuracoes = ControladorConfiguracoes(bd, self.sessao)
        self.importacao = ControladorImportacao(bd, self.sessao)
        self.inscricoes = ControladorInscricoes(bd, self.sessao)
        self.partida = ControladorPartida(bd, self.sessao)
        self.meta = ControladorMeta(bd, self.sessao)
        self.classificacoes = ControladorClassificacoes(bd, self.sessao)
        self.relatorios = ControladorRelatorios(bd, self.sessao)

        self.area = ft.Container(expand=True, padding=24, bgcolor=common.CINZA_FUNDO)
        self.pagina_atual = "inicio"
        self.menu_expandido = True
        self._barra: ft.Container | None = None
        self._raiz: ft.Control | None = None
        self.mov = False
        self._botao_menu = ft.IconButton(
            ft.Icons.MENU,
            tooltip="Recolher menu",
            icon_color="#D6E8DC",
            on_click=self.alternar_menu,
        )
        self._botao_movel = ft.IconButton(
            ft.Icons.MENU,
            tooltip="Abrir menu",
            icon_color=common.VERDE_ESCURO,
            on_click=self.abrir_menu_movel,
            visible=False,
        )
        self.page.on_resized = self._ao_redimensionar
        self._menu_coluna = ft.Column(
            spacing=2, expand=True, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )

    # ------------------------------------------------------------------
    # Arranque e navegação
    # ------------------------------------------------------------------
    def _registar_erro(self, erro: Exception) -> str:
        """Guarda o rasto completo da exceção e devolve um resumo apresentável."""
        detalhe = f"{type(erro).__name__}: {erro}"
        try:
            pasta = Path(__file__).resolve().parents[2] / "dados"
            pasta.mkdir(parents=True, exist_ok=True)
            with (pasta / "erros.log").open("a", encoding="utf-8") as ficheiro:
                ficheiro.write(f"\n[{datas.agora_texto()}] {detalhe}\n")
                ficheiro.write(traceback.format_exc())
        except Exception:  # noqa: BLE001 - o registo nunca deve bloquear a interface
            pass
        return detalhe

    def _ecra_de_erro(self, titulo: str, detalhe: str) -> ft.Control:
        """Ecrã de recuperação sem detalhes técnicos.

        O rasto da exceção (`detalhe`) é guardado em `dados/erros.log` por
        `_registar_erro`, mas não é mostrado na interface.
        """
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.ERROR_OUTLINE, size=44, color=common.TEXTO_SUAVE),
                    ft.Text(
                        titulo,
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=common.TEXTO,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "Não foi possível preparar este ecrã. Tente novamente.",
                        size=12,
                        color=common.TEXTO_SUAVE,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    common.botao(
                        "Tentar novamente",
                        self._repetir,
                        principal=True,
                        icone=ft.Icons.REFRESH,
                    ),
                ],
                spacing=14,
                tight=True,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.Alignment(0, 0),
            expand=True,
            padding=24,
        )

    def iniciar(self) -> None:
        self.page.controls.clear()
        try:
            self.page.add(login.construir(self))
        except Exception as erro:  # noqa: BLE001
            detalhe = self._registar_erro(erro)
            self.page.add(self._ecra_de_erro("Erro ao construir o ecrã de entrada", detalhe))
        self.page.update()

    def mostrar_aplicacao(self, pagina: str = "inicio") -> None:
        self.page.controls.clear()
        try:
            largura = self._largura_ecra()
            if largura:
                self.mov = largura < LARGURA_MOVEL
            self.area.padding = 12 if self.mov else 24
            conteudo = ft.Column([self._cabecalho(), self.area], spacing=0, expand=True)
            if self.mov:
                # Telemóvel: o menu abre por cima do conteúdo, em gaveta.
                self.menu_expandido = True
                self._barra = None
                self._raiz = ft.Stack([conteudo], expand=True)
            else:
                self._barra = self._barra_lateral()
                self._raiz = ft.Row(
                    [self._barra, conteudo],
                    spacing=0,
                    expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                )
            self.page.add(self._raiz)
            self.navegar(pagina, atualizar=False)
        except Exception as erro:  # noqa: BLE001
            detalhe = self._registar_erro(erro)
            self.page.controls.clear()
            self.page.add(self._ecra_de_erro("Erro ao abrir a aplicação", detalhe))
        self.page.update()

    def navegar(self, pagina: str, atualizar: bool = True) -> None:
        permissoes = {chave: permissao for chave, _rotulo, _icone, permissao in MENU}
        permissao = permissoes.get(pagina)
        if permissao and not self.sessao.tem(permissao):
            common.mensagem(self.page, "Sem permissão para aceder a este módulo.", erro=True)
            return

        construtores = {
            # `_dashboard` é um método ligado; as restantes são funções de vista
            # que recebem a instância da aplicação como argumento.
            "inicio": lambda _app: self._dashboard(),
            "configuracoes": vista_config.construir,
            "importacoes": vista_importacoes.construir,
            "inscricoes": vista_inscricoes.construir,
            "partida": vista_partida.construir,
            "meta": vista_meta.construir,
            "classificacoes": vista_classificacoes.construir,
            "relatorios": vista_relatorios.construir,
            "responsaveis": vista_responsaveis.construir,
        }
        construtor = construtores.get(pagina)
        if construtor is None:
            return

        self.pagina_atual = pagina
        try:
            conteudo = construtor(self)
        except PermissaoNegada as erro:
            conteudo = common.aviso(str(erro), common.ERRO)
        except ErroValidacao as erro:
            conteudo = common.aviso(str(erro), common.ERRO)
        except Exception as erro:  # noqa: BLE001 - evita bloquear a interface
            detalhe = self._registar_erro(erro)
            conteudo = self._ecra_de_erro("Erro inesperado", detalhe)

        self.area.content = conteudo
        self._atualizar_menu()
        self.fechar_menu_movel()
        if atualizar:
            self.page.update()

    def terminar_sessao(self) -> None:
        self.auth.terminar_sessao()
        self.iniciar()

    def _largura_ecra(self) -> int:
        """Largura atual da janela/ecrã, com recurso à largura da janela."""
        largura = getattr(self.page, "width", None) or 0
        if not largura:
            largura = getattr(getattr(self.page, "window", None), "width", 0) or 0
        return int(largura or 0)

    def _ao_redimensionar(self, _evento=None) -> None:
        """Troca entre o layout de secretária e o de telemóvel."""
        largura = self._largura_ecra()
        if not largura:
            return
        mov = largura < LARGURA_MOVEL
        if mov == self.mov:
            return
        self.mov = mov
        if self.sessao.autenticado():
            self.mostrar_aplicacao(self.pagina_atual)

    def abrir_menu_movel(self, _evento=None) -> None:
        """Mostra a barra lateral por cima do conteúdo (telemóvel)."""
        if not self.mov or not isinstance(self._raiz, ft.Stack):
            return
        if len(self._raiz.controls) > 1:
            return
        self.menu_expandido = True
        self._barra = ft.Container(
            content=self._conteudo_barra(),
            width=min(LARGURA_MENU, self._largura_ecra() or LARGURA_MENU),
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[common.VERDE_ESCURO, common.VERDE_PROFUNDO],
            ),
            padding=ft.padding.only(top=16),
        )
        fundo = ft.Container(
            expand=True, bgcolor="#66000000", on_click=self.fechar_menu_movel
        )
        self._raiz.controls.append(ft.Row([self._barra, fundo], spacing=0, expand=True))
        self.page.update()

    def fechar_menu_movel(self, _evento=None) -> None:
        """Fecha a gaveta do menu em telemóvel (se estiver aberta)."""
        if isinstance(self._raiz, ft.Stack) and len(self._raiz.controls) > 1:
            self._raiz.controls.pop()
            self._barra = None
            self.page.update()

    def alternar_menu(self, _evento=None) -> None:
        """Recolhe/expande a barra lateral (modo "hambúrguer")."""
        self.menu_expandido = not self.menu_expandido
        self._botao_menu.icon = ft.Icons.MENU_OPEN if not self.menu_expandido else ft.Icons.MENU
        self._botao_menu.tooltip = "Expandir menu" if not self.menu_expandido else "Recolher menu"
        if self._barra is not None:
            self._barra.width = LARGURA_MENU if self.menu_expandido else LARGURA_MENU_ENCURTADA
            self._barra.content = self._conteudo_barra()
        self._atualizar_menu()
        self.page.update()

    def _repetir(self, _evento=None) -> None:
        """Reconstrói o ecrã atual depois de um erro."""
        if self.sessao.autenticado():
            self.navegar(self.pagina_atual)
        else:
            self.iniciar()

    # ------------------------------------------------------------------
    # Componentes estruturais
    # ------------------------------------------------------------------
    def _item_menu(self, chave: str, rotulo: str, icone) -> ft.Container:
        selecionado = chave == self.pagina_atual
        if not self.menu_expandido:
            return ft.Container(
                content=ft.Icon(
                    icone,
                    size=20,
                    color=common.VERDE_ESCURO if selecionado else "#9CC7AE",
                ),
                width=48,
                height=42,
                margin=ft.margin.symmetric(horizontal=10, vertical=2),
                bgcolor="#FFFFFF" if selecionado else None,
                border_radius=10,
                alignment=ft.Alignment(0, 0),
                ink=not selecionado,
                tooltip=rotulo,
                on_click=lambda _e, destino=chave: self.navegar(destino),
            )
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        icone,
                        size=18,
                        color=common.VERDE_ESCURO if selecionado else "#9CC7AE",
                    ),
                    ft.Text(
                        rotulo,
                        size=12,
                        color=common.VERDE_ESCURO if selecionado else "#D6E8DC",
                        weight=ft.FontWeight.BOLD if selecionado else None,
                        expand=True,
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=12, vertical=9),
            margin=ft.margin.symmetric(horizontal=10, vertical=1),
            bgcolor="#FFFFFF" if selecionado else None,
            border_radius=9,
            ink=not selecionado,
            tooltip=None if self.menu_expandido else rotulo,
            on_click=lambda _e, destino=chave: self.navegar(destino),
        )

    def _itens_menu(self) -> list[ft.Control]:
        catalogo = {chave: (rotulo, icone, permissao)
                    for chave, rotulo, icone, permissao in MENU}
        itens: list[ft.Control] = []
        for grupo, chaves in GRUPOS:
            visiveis = [
                chave for chave in chaves
                if chave in catalogo
                and (not catalogo[chave][2] or self.sessao.tem(catalogo[chave][2]))
            ]
            if not visiveis:
                continue
            if self.menu_expandido:
                itens.append(
                    ft.Container(
                        content=ft.Text(
                            grupo.upper(), size=9, weight=ft.FontWeight.BOLD, color="#7FB295"
                        ),
                        padding=ft.padding.only(left=14, top=12, bottom=4),
                    )
                )
            else:
                itens.append(
                    ft.Container(
                        height=1,
                        bgcolor="#1FFFFFFF",
                        margin=ft.margin.symmetric(horizontal=20, vertical=7),
                    )
                )
            for chave in visiveis:
                rotulo, icone, _permissao = catalogo[chave]
                itens.append(self._item_menu(chave, rotulo, icone))
        return itens

    def _atualizar_menu(self) -> None:
        self._menu_coluna.controls = self._itens_menu()

    def _marca_menu(self) -> ft.Control:
        if not self.menu_expandido:
            return ft.Container(
                content=ft.Container(
                    content=ft.Image(
                        src=common.LOGO,
                        height=26,
                        fit=ft.ImageFit.CONTAIN,
                        semantics_label="Desporto Escolar",
                    ),
                    width=44,
                    height=44,
                    border_radius=11,
                    padding=7,
                    alignment=ft.Alignment(0, 0),
                ),
                alignment=ft.Alignment(0, 0),
                padding=ft.padding.only(left=10, right=10, bottom=16),
            )
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Image(
                            src=common.LOGO,
                            height=46,
                            fit=ft.ImageFit.CONTAIN,
                            semantics_label="Desporto Escolar",
                        ),
                        padding=10,
                        border_radius=12,
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Text(
                        "Corta-Mato AEPBS",
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color="#FFFFFF",
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.only(left=10, right=10, top=0, bottom=14),
        )

    def _conteudo_barra(self) -> ft.Control:
        self._menu_coluna = ft.Column(
            spacing=2,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        self._atualizar_menu()

        if self.mov:
            topo = ft.Container(
                content=ft.Row(
                    [
                        ft.IconButton(
                            ft.Icons.CLOSE,
                            tooltip="Fechar menu",
                            icon_color="#D6E8DC",
                            on_click=self.fechar_menu_movel,
                        )
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
                padding=ft.padding.only(left=4, right=6, bottom=2),
            )
        else:
            topo = ft.Container(
                content=ft.Row(
                    [self._botao_menu],
                    alignment=(
                        ft.MainAxisAlignment.END if self.menu_expandido
                        else ft.MainAxisAlignment.CENTER
                    ),
                ),
                padding=ft.padding.only(left=4, right=6, bottom=2),
            )

        if not self.menu_expandido:
            return ft.Column(
                [topo, self._marca_menu(), self._menu_coluna], spacing=0, expand=True
            )

        rodape = ft.Container(
            content=ft.Column(
                [
                    common.separador(),
                    ft.Text(
                        "Agrupamento de Escolas de Padre Benjamim Salgado",
                        size=9,
                        color="#7FB295",
                    ),
                ],
                spacing=8,
            ),
            padding=ft.padding.only(left=16, right=16, top=6, bottom=4),
        )
        return ft.Column(
            [topo, self._marca_menu(), self._menu_coluna, rodape], spacing=0, expand=True
        )

    def _barra_lateral(self) -> ft.Control:
        return ft.Container(
            content=self._conteudo_barra(),
            width=LARGURA_MENU if self.menu_expandido else LARGURA_MENU_ENCURTADA,
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[common.VERDE_ESCURO, common.VERDE_PROFUNDO],
            ),
            padding=ft.padding.only(top=16),
        )

    def _cabecalho(self) -> ft.Control:
        dados = self.configuracoes.dados_atividade()
        nome = self.sessao.nome or "Responsável"
        iniciais = "".join(parte[0] for parte in nome.split()[:2]).upper() or "?"

        self._botao_movel.visible = self.mov
        # O logótipo original é branco (feito para fundos escuros); sobre o
        # cabeçalho claro usa-se a versão verde gerada em `assets`.
        marca_cabecalho = common.LOGO_ESCURO
        if not (common.PASTA_ASSETS / marca_cabecalho).is_file():
            marca_cabecalho = common.LOGO
        return ft.Container(
            content=ft.Row(
                [
                    self._botao_movel,
                    ft.Image(
                        src=marca_cabecalho,
                        height=22 if self.mov else 26,
                        fit=ft.ImageFit.CONTAIN,
                        semantics_label="Desporto Escolar",
                    ),
                    ft.Text(
                        dados["designacao"],
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=common.TEXTO,
                        expand=True,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.PopupMenuButton(
                        tooltip="Conta",
                        # Superfície clara e cantos suaves, para o menu não herdar
                        # o tom bege do esquema de cores do Material 3.
                        bgcolor="#FFFFFF",
                        surface_tint_color="#FFFFFF",
                        elevation=8,
                        shadow_color="#33033A23",
                        shape=ft.RoundedRectangleBorder(radius=12),
                        menu_padding=ft.padding.all(6),
                        content=ft.Container(
                            content=ft.Row(
                                [
                                    ft.Container(
                                        content=ft.Text(
                                            iniciais,
                                            size=12,
                                            weight=ft.FontWeight.BOLD,
                                            color=common.VERDE_ESCURO,
                                        ),
                                        bgcolor=common.VERDE_CLARO,
                                        width=36,
                                        height=36,
                                        border_radius=18,
                                        alignment=ft.Alignment(0, 0),
                                    ),
                                    ft.Column(
                                        [
                                            ft.Text(nome, size=12, weight=ft.FontWeight.BOLD,
                                                    color=common.TEXTO),
                                            ft.Text(self.sessao.perfil, size=10,
                                                    color=common.TEXTO_SUAVE),
                                        ],
                                        spacing=0,
                                        visible=not self.mov,
                                    ),
                                    ft.Icon(
                                        ft.Icons.KEYBOARD_ARROW_DOWN,
                                        size=16,
                                        color=common.TEXTO_SUAVE,
                                    ),
                                ],
                                spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            padding=ft.padding.symmetric(horizontal=8, vertical=6),
                            border_radius=10,
                        ),
                        items=[
                            ft.PopupMenuItem(
                                content=ft.Container(
                                    content=ft.Column(
                                        [
                                            ft.Text(
                                                nome,
                                                size=12,
                                                weight=ft.FontWeight.BOLD,
                                                color=common.TEXTO,
                                                max_lines=1,
                                                overflow=ft.TextOverflow.ELLIPSIS,
                                            ),
                                            ft.Text(
                                                self.sessao.perfil,
                                                size=10,
                                                color=common.TEXTO_SUAVE,
                                            ),
                                        ],
                                        spacing=0,
                                        tight=True,
                                    ),
                                    padding=ft.padding.only(bottom=6),
                                    border=ft.border.only(
                                        bottom=ft.BorderSide(1, common.CINZA_BORDA)
                                    ),
                                ),
                                height=52,
                                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                            ),
                            ft.PopupMenuItem(
                                content=ft.Row(
                                    [
                                        ft.Container(
                                            content=ft.Icon(
                                                ft.Icons.LOGOUT, size=15, color=common.ERRO
                                            ),
                                            bgcolor="#FBEAE8",
                                            width=28,
                                            height=28,
                                            border_radius=8,
                                            alignment=ft.Alignment(0, 0),
                                        ),
                                        ft.Text(
                                            "Terminar sessão",
                                            size=12,
                                            color=common.ERRO,
                                            weight=ft.FontWeight.W_600,
                                        ),
                                    ],
                                    spacing=10,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                height=46,
                                padding=ft.padding.symmetric(horizontal=10),
                                on_click=lambda _e: self.terminar_sessao(),
                            ),
                        ],
                    ),
                ],
                spacing=8 if self.mov else 16,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(
                horizontal=12 if self.mov else 24,
                vertical=10 if self.mov else 12,
            ),
            border=ft.Border(bottom=ft.BorderSide(1, common.CINZA_BORDA)),
        )

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------
    @staticmethod
    def _pastilha(icone, texto: str) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icone, size=12, color="#FFFFFF"),
                    ft.Text(texto, size=10, color="#FFFFFF"),
                ],
                spacing=5,
                tight=True,
            ),
            bgcolor="#26FFFFFF",
            padding=ft.padding.symmetric(horizontal=9, vertical=4),
            border_radius=20,
        )

    def _dashboard(self) -> ft.Control:
        resumo = self.inscricoes.resumo()
        dados = self.configuracoes.dados_atividade()
        turmas = self.configuracoes.listar_turmas()
        alunos = self.configuracoes.listar_alunos()
        participantes = resumo["participantes"] or 0
        cobertura = round(100 * resumo["chegadas"] / participantes) if participantes else 0

        # --- Contagem decrescente até 18 de novembro do próximo ano -----
        fim = date(date.today().year + 1, 11, 18)
        dias = max((fim - date.today()).days, 0)
        contagem = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.HOURGLASS_BOTTOM, size=13, color="#FFFFFF"),
                    ft.Text(
                        f"Faltam {dias} {'dia' if dias == 1 else 'dias'} · {fim:%d/%m/%Y}",
                        size=10,
                        color="#FFFFFF",
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
                spacing=6,
                tight=True,
            ),
            bgcolor="#26FFFFFF",
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
            border_radius=20,
            tooltip="Contagem decrescente até 18 de novembro do próximo ano",
        )

        # --- Faixa de destaque -----------------------------------------
        imagem_fundo = common.imagem_fundo()
        estilo_faixa = (
            {"image": common.fundo(imagem_fundo, 0.34), "bgcolor": common.VERDE_PROFUNDO}
            if imagem_fundo
            else {
                "gradient": ft.LinearGradient(
                    begin=ft.Alignment(-1, -1),
                    end=ft.Alignment(1, 1),
                    colors=[common.VERDE_PROFUNDO, common.VERDE],
                )
            }
        )
        titulo_faixa = ft.Column(
            [
                ft.Text("Painel de controlo", size=15,
                        weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                ft.Text(
                    dados["designacao"],
                    size=10,
                    color="#CFE9DA",
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
            spacing=0,
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        )
        pastilhas = ft.Row(
            [
                self._pastilha(ft.Icons.CALENDAR_MONTH,
                               dados["data_prova"] or "Data a definir"),
                self._pastilha(ft.Icons.TIMER_OUTLINED,
                               dados["hora_partida"] or "Hora a definir"),
                self._pastilha(ft.Icons.LOCATION_ON_OUTLINED,
                               dados["local"] or "Local a definir"),
                self._pastilha(ft.Icons.EMOJI_EVENTS,
                               f"Edição {dados['edicao'] or '—'}"),
            ],
            spacing=6,
            wrap=True,
            run_spacing=6,
        )
        if self.mov:
            # Telemóvel: marca + título numa linha, depois pastilhas e contagem.
            conteudo_faixa: ft.Control = ft.Column(
                [titulo_faixa, pastilhas, contagem],
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.START,
            )
        else:
            # `expand` só é válido numa `Row` normal; dentro de uma `Row` com
            # `wrap` provoca erro de layout no Flutter (área cinzenta).
            conteudo_faixa = ft.Row(
                [
                    ft.Column([titulo_faixa, pastilhas], spacing=6, tight=True,
                              expand=True,
                              horizontal_alignment=ft.CrossAxisAlignment.START),
                    contagem,
                ],
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        faixa = ft.Container(
            content=conteudo_faixa,
            padding=12 if self.mov else 16,
            border_radius=14,
            shadow=common.SOMBRA,
            **estilo_faixa,
        )

        # --- Indicadores -----------------------------------------------
        def cartao_indicador(rotulo, valor, icone, cor) -> ft.Control:
            return common.indicador(
                rotulo, valor, icone, cor,
                centrado=True,
                tamanho_icone=22,
                tamanho_valor=28,
                col={"xs": 6, "sm": 4, "md": 2},
            )

        indicadores = ft.ResponsiveRow(
            [
                cartao_indicador("Inscrições", resumo["total"],
                                 ft.Icons.EDIT_NOTE, common.VERDE),
                cartao_indicador("Participantes", resumo["participantes"],
                                 ft.Icons.DIRECTIONS_RUN, common.AZUL),
                cartao_indicador("Dorsais", resumo["com_dorsal"],
                                 ft.Icons.CONFIRMATION_NUMBER, common.VERMELHO),
                cartao_indicador("Chegadas", resumo["chegadas"],
                                 ft.Icons.TIMER_OUTLINED, "#B07A00"),
                cartao_indicador("Organização", resumo["organizacao"],
                                 ft.Icons.GROUPS, "#5B4B8A"),
                cartao_indicador("Turmas", len(turmas), ft.Icons.SCHOOL, "#0E7490"),
            ],
            spacing=12,
            run_spacing=12,
        )

        # --- Fluxo da atividade ----------------------------------------
        passos = [
            ("Configurar a atividade e os escalões", bool(dados["data_prova_iso"]),
             "configuracoes"),
            ("Importar turmas, DT e alunos (CSV)", len(turmas) > 0, "importacoes"),
            ("Registar inscrições", resumo["total"] > 0, "inscricoes"),
            ("Entregar dorsais (secretariado de partida)", resumo["com_dorsal"] > 0, "partida"),
            ("Registar chegadas (secretariado de meta)", resumo["chegadas"] > 0, "meta"),
            ("Produzir classificações e relatórios", resumo["chegadas"] > 0, "classificacoes"),
        ]

        permissoes = {chave: permissao for chave, _r, _i, permissao in MENU}
        linhas_passo: list[ft.Control] = []
        proximo = None
        # Cada passo só abre depois de o anterior estar concluído (fluxo sequencial).
        liberado = True
        for rotulo, concluido, destino in passos:
            if not concluido and proximo is None:
                proximo = (rotulo, destino)
            permitido = (not permissoes.get(destino)
                         or self.sessao.tem(permissoes[destino])) and liberado
            destacado = proximo is not None and proximo[1] == destino and not concluido
            linhas_passo.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.CHECK_CIRCLE if concluido
                                else ft.Icons.RADIO_BUTTON_UNCHECKED,
                                size=18,
                                color=common.VERDE if concluido else "#B7C4BB",
                            ),
                            ft.Text(
                                rotulo,
                                size=12,
                                expand=True,
                                color=common.TEXTO if concluido else common.TEXTO_SUAVE,
                                weight=ft.FontWeight.BOLD if destacado else None,
                            ),
                            ft.Icon(
                                ft.Icons.CHEVRON_RIGHT,
                                size=16,
                                color="#93A69A" if permitido else "#C8D4CC",
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    # Cada passo reparte a altura do cartão, para a lista ir
                    # até ao fim (no telemóvel fica com a altura do conteúdo).
                    expand=0 if self.mov else 1,
                    alignment=ft.Alignment(-1, 0),
                    padding=ft.padding.symmetric(horizontal=8),
                    border_radius=8,
                    bgcolor=common.CINZA_SUAVE if destacado else None,
                    ink=permitido,
                    on_click=(lambda _e, d=destino: self.navegar(d))
                    if permitido else None,
                    tooltip=None if permitido else (
                        "Sem permissão para este módulo." if liberado
                        else "Conclua o passo anterior para abrir."
                    ),
                )
            )
            liberado = liberado and concluido

        cartao_fluxo = common.cartao(
            common.titulo_seccao("Fluxo da atividade", ft.Icons.ACCOUNT_TREE),
            common.subtitulo("Sequência de trabalho dos secretariados, do início à divulgação."),
            *linhas_passo,
            espacamento=8,
            preenchimento=14,
        )

        # --- Pendências por módulo (gráfico de barras) -----------------
        # Cada barra agrupa as pendências do respetivo módulo. A altura do
        # gráfico (150) é a mesma do gráfico de setores ao lado.
        inscricoes = self.inscricoes.listar()
        inscritos_ids = {linha["aluno_id"] for linha in inscricoes}
        alunos_ativos = [aluno for aluno in alunos if aluno.get("ativo", 1)]
        por_modulo = [
            ("Importação",
             sum(1 for turma in turmas if not (turma.get("dt_nome") or "").strip())
             + sum(1 for aluno in alunos_ativos if not aluno.get("turma_id"))
             + sum(1 for aluno in alunos_ativos if not aluno.get("data_nascimento")),
             "#0E7490",
             "turmas sem diretor de turma, alunos sem turma ou sem data de nascimento"),
            ("Inscrições",
             sum(1 for aluno in alunos_ativos if aluno["id"] not in inscritos_ids)
             + sum(1 for linha in inscricoes if not linha.get("escalao_id")),
             common.VERDE,
             "alunos sem inscrição e inscrições sem escalão"),
            ("Partida",
             max(resumo["total"] - resumo["com_dorsal"], 0),
             common.VERMELHO,
             "inscrições ainda sem dorsal entregue"),
            ("Meta",
             max(resumo["com_dorsal"] - resumo["chegadas"], 0),
             "#B07A00",
             "participantes ainda sem chegada registada"),
        ]
        total_pendencias = sum(valor for _rotulo, valor, _cor, _nota in por_modulo)
        maximo = max(valor for _rotulo, valor, _cor, _nota in por_modulo)

        if total_pendencias:
            # Escala do eixo vertical em degraus inteiros (no máximo 4 intervalos).
            passo = max(1, -(-maximo // 4))
            topo_y = passo * (maximo // passo + 1)
            grafico_pendencias: ft.Control = ft.BarChart(
                bar_groups=[
                    ft.BarChartGroup(
                        x=indice,
                        bar_rods=[
                            ft.BarChartRod(
                                from_y=0,
                                to_y=valor,
                                width=58,
                                color=cor,
                                border_radius=ft.border_radius.vertical(top=4),
                                tooltip=f"{rotulo}: {valor} — {nota}",
                            )
                        ],
                    )
                    for indice, (rotulo, valor, cor, nota) in enumerate(por_modulo)
                ],
                min_y=0,
                max_y=float(topo_y),
                groups_space=20,
                bgcolor="#FFFFFF",
                tooltip_bgcolor=common.VERDE_PROFUNDO,
                horizontal_grid_lines=ft.ChartGridLines(
                    interval=passo, color=common.CINZA_BORDA, width=1
                ),
                bottom_axis=ft.ChartAxis(
                    labels=[
                        ft.ChartAxisLabel(
                            value=indice,
                            label=ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text(rotulo, size=9,
                                                weight=ft.FontWeight.BOLD,
                                                color=common.TEXTO_SUAVE),
                                        ft.Text(str(valor), size=9,
                                                color=common.TEXTO_SUAVE),
                                    ],
                                    spacing=0,
                                    tight=True,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                padding=ft.padding.only(top=6),
                            ),
                        )
                        for indice, (rotulo, valor, _cor, _nota) in enumerate(por_modulo)
                    ],
                    labels_size=34,
                ),
                left_axis=ft.ChartAxis(labels_size=26, labels_interval=passo),
                height=150,
            )
        else:
            grafico_pendencias = ft.Container(
                content=common.vazio(
                    "Sem pendências: os dados essenciais estão completos.",
                    ft.Icons.CHECK_CIRCLE_OUTLINE,
                ),
                height=150,
                alignment=ft.Alignment(0, 0),
            )

        cartao_pendencias = common.cartao(
            common.titulo_seccao("Pendências por módulo", ft.Icons.BAR_CHART),
            common.subtitulo(
                "Nada por completar: os dados essenciais estão prontos."
                if not total_pendencias
                else f"{total_pendencias} registo(s) por completar antes da prova."
            ),
            grafico_pendencias,
            espacamento=6,
            preenchimento=12,
        )

        def linha_estado(rotulo: str, valor) -> ft.Control:
            """Linha do resumo: rótulo à esquerda, número à direita.

            Cada linha ocupa a mesma fatia da altura do cartão (`expand`), para
            a lista preencher o espaço em vez de se encostar ao topo.
            """
            return ft.Container(
                content=ft.Row(
                    [
                        ft.Text(rotulo, size=12, color=common.TEXTO_SUAVE, expand=True),
                        ft.Text(str(valor), size=18, weight=ft.FontWeight.BOLD,
                                color=common.TEXTO),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                # `expand` só com altura definida (desktop); no telemóvel os
                # cartões têm a altura do conteúdo.
                expand=0 if self.mov else 1,
                padding=ft.padding.symmetric(horizontal=2),
                alignment=ft.Alignment(0, 0),
            )

        cartao_estado = common.cartao(
            common.titulo_seccao("Informações", ft.Icons.STORAGE),
            linha_estado("Alunos carregados", len(alunos)),
            linha_estado("Turmas", len(turmas)),
            linha_estado("Escalões definidos", len(self.configuracoes.listar_escaloes())),
            linha_estado("Inscrições", resumo["total"]),
            linha_estado("Dorsais entregues", resumo["com_dorsal"]),
            linha_estado("Chegadas", resumo["chegadas"]),
            common.separador(),
            ft.Text(f"Cobertura da meta: {cobertura}%", size=11,
                    weight=ft.FontWeight.BOLD, color=common.TEXTO_SUAVE),
            ft.ProgressBar(value=cobertura / 100, color=common.VERDE,
                           bgcolor=common.VERDE_CLARO, height=8),
            espacamento=8,
            preenchimento=14,
        )

        # --- Gráfico de informação de base ------------------------------
        estados = [
            ("Inscritos", resumo["inscritos"], common.VERDE),
            ("Participantes", resumo["participantes"], common.AZUL),
            ("Organização", resumo["organizacao"], "#5B4B8A"),
        ]
        total_inscricoes = sum(valor for _rotulo, valor, _cor in estados)
        if total_inscricoes:
            seccoes = [
                ft.PieChartSection(
                    value=valor,
                    title=str(valor) if valor else "",
                    color=cor,
                    radius=40,
                    title_style=ft.TextStyle(size=10, weight=ft.FontWeight.BOLD,
                                             color="#FFFFFF"),
                )
                for rotulo, valor, cor in estados
                if valor
            ]
        else:
            # Sem dados: anel neutro, para o gráfico não aparecer vazio.
            seccoes = [ft.PieChartSection(value=1, title="", color=common.CINZA_BORDA,
                                          radius=40)]
        grafico = ft.Stack(
            [
                ft.PieChart(
                    sections=seccoes,
                    sections_space=2,
                    center_space_radius=32,
                    expand=True,
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(str(total_inscricoes), size=16,
                                    weight=ft.FontWeight.BOLD, color=common.TEXTO),
                            ft.Text("inscrições", size=8, color=common.TEXTO_SUAVE),
                        ],
                        spacing=0,
                        tight=True,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.Alignment(0, 0),
                    expand=True,
                ),
            ],
            height=150,
        )
        legenda = ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(width=9, height=9, border_radius=5, bgcolor=cor),
                        ft.Text(rotulo, size=10, color=common.TEXTO_SUAVE, expand=True),
                        ft.Text(str(valor), size=10, weight=ft.FontWeight.BOLD,
                                color=common.TEXTO),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
                for rotulo, valor, cor in estados
            ],
            spacing=6,
            tight=True,
        )
        cartao_grafico = common.cartao(
            common.titulo_seccao("Inscrições por estado", ft.Icons.PIE_CHART),
            grafico,
            legenda,
            espacamento=6,
            preenchimento=12,
        )
        # --- Composição -------------------------------------------------
        # No desktop os dois pares de cartões repartem a altura que sobra da
        # janela: a página não faz scroll e as colunas ficam niveladas. Se a
        # janela for baixa, o conteúdo rola dentro de cada cartão.
        if not self.mov:
            for bloco, flex in ((cartao_fluxo, 2), (cartao_pendencias, 2),
                                (cartao_estado, 1), (cartao_grafico, 1)):
                bloco.expand = flex
                # Os cartões repartem a altura da janela e o conteúdo é
                # distribuído dentro de cada um (sem barras de scroll).
                bloco.content.tight = False
            grelha: ft.Control = ft.Column(
                [
                    ft.Row(
                        [cartao_fluxo, cartao_estado],
                        spacing=12,
                        expand=True,
                        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                    ),
                    ft.Row(
                        [cartao_pendencias, cartao_grafico],
                        spacing=12,
                        expand=True,
                        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                    ),
                ],
                spacing=12,
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            )
        else:
            grelha = ft.Column(
                [cartao_fluxo, cartao_pendencias, cartao_estado, cartao_grafico],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            )

        # --- Atalhos ---------------------------------------------------
        # Ocupa a faixa que sobra sob as duas colunas com os destinos mais usados.
        atalhos = [
            ("Nova inscrição", ft.Icons.EDIT_NOTE, "inscricoes", common.VERDE),
            ("Dorsais", ft.Icons.CONFIRMATION_NUMBER, "partida", common.VERMELHO),
            ("Chegadas", ft.Icons.TIMER_OUTLINED, "meta", "#B07A00"),
            ("Relatórios", ft.Icons.DESCRIPTION_OUTLINED, "relatorios", common.AZUL),
        ]

        def atalho(rotulo: str, icone, destino: str, cor: str) -> ft.Control:
            permitido = not permissoes.get(destino) or self.sessao.tem(permissoes[destino])
            return ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(icone, size=15, color=cor if permitido else "#93A69A"),
                            bgcolor=common._tom(cor, "14") if permitido else common.CINZA_SUAVE,
                            width=30,
                            height=30,
                            border_radius=9,
                            alignment=ft.Alignment(0, 0),
                        ),
                        ft.Text(
                            rotulo,
                            size=11.5,
                            weight=ft.FontWeight.BOLD,
                            color=common.TEXTO if permitido else common.TEXTO_SUAVE,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            expand=True,
                        ),
                        ft.Icon(
                            ft.Icons.CHEVRON_RIGHT,
                            size=16,
                            color="#93A69A",
                            visible=permitido,
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                col={"xs": 6, "sm": 3},
                bgcolor=common.CINZA_SUAVE,
                border=ft.border.all(1, common.CINZA_BORDA),
                border_radius=10,
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                ink=permitido,
                tooltip=None if permitido else "Sem permissão para este módulo.",
                on_click=(lambda _e, d=destino: self.navegar(d)) if permitido else None,
            )

        cartao_atalhos = common.cartao(
            ft.ResponsiveRow(
                [atalho(*item) for item in atalhos],
                spacing=10,
                run_spacing=10,
            ),
            preenchimento=8,
        )

        return ft.Column(
            [
                faixa,
                indicadores,
                grelha,
                cartao_atalhos,
            ],
            spacing=12,
            # No desktop o dashboard cabe na janela (sem scroll de página).
            scroll=None if not self.mov else ft.ScrollMode.AUTO,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
