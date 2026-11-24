"""Estrutura principal da aplicação: barra lateral, navegação e dashboard."""

from __future__ import annotations

import traceback
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
        self._botao_menu = ft.IconButton(
            ft.Icons.MENU,
            tooltip="Recolher menu",
            icon_color=common.VERDE_ESCURO,
            on_click=self.alternar_menu,
        )
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
            self._barra = self._barra_lateral()
            self.page.add(
                ft.Row(
                    [
                        self._barra,
                        ft.Column([self._cabecalho(), self.area], spacing=0, expand=True),
                    ],
                    spacing=0,
                    expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                )
            )
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
        if atualizar:
            self.page.update()

    def terminar_sessao(self) -> None:
        self.auth.terminar_sessao()
        self.iniciar()

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
                    bgcolor="#FFFFFF",
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
                        bgcolor="#FFFFFF",
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

        if not self.menu_expandido:
            return ft.Column(
                [self._marca_menu(), self._menu_coluna], spacing=0, expand=True
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
            [self._marca_menu(), self._menu_coluna, rodape], spacing=0, expand=True
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

        return ft.Container(
            content=ft.Row(
                [
                    self._botao_menu,
                    ft.Container(width=1, height=30, bgcolor=common.CINZA_BORDA),
                    ft.Column(
                        [
                            ft.Text(dados["designacao"], size=14,
                                    weight=ft.FontWeight.BOLD, color=common.TEXTO),
                            ft.Text(
                                f"Edição {dados['edicao'] or '—'} · "
                                f"{dados['data_prova'] or 'data a definir'} · "
                                f"{dados['hora_partida'] or '--:--'} · "
                                f"{dados['local'] or 'local a definir'}",
                                size=11,
                                color=common.TEXTO_SUAVE,
                            ),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                    ft.PopupMenuButton(
                        tooltip="Conta",
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
                                content=ft.Row(
                                    [
                                        ft.Icon(ft.Icons.LOGOUT, size=16, color=common.ERRO),
                                        ft.Text("Terminar sessão", size=12, color=common.TEXTO),
                                    ],
                                    spacing=10,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                on_click=lambda _e: self.terminar_sessao(),
                            ),
                        ],
                    ),
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor="#FFFFFF",
            padding=ft.padding.symmetric(horizontal=24, vertical=12),
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
                    ft.Icon(icone, size=13, color="#FFFFFF"),
                    ft.Text(texto, size=11, color="#FFFFFF"),
                ],
                spacing=6,
            ),
            bgcolor="#26FFFFFF",
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            border_radius=20,
        )

    def _dashboard(self) -> ft.Control:
        resumo = self.inscricoes.resumo()
        dados = self.configuracoes.dados_atividade()
        turmas = self.configuracoes.listar_turmas()
        participantes = resumo["participantes"] or 0
        cobertura = round(100 * resumo["chegadas"] / participantes) if participantes else 0

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
        faixa = ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text("Painel de controlo", size=26,
                                    weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                            ft.Text(dados["designacao"], size=13, color="#CFE9DA"),
                            ft.Row(
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
                                spacing=8,
                                wrap=True,
                                run_spacing=8,
                            ),
                        ],
                        spacing=8,
                        expand=True,
                    ),
                    ft.Container(
                        content=ft.Image(
                            src=common.LOGO,
                            height=82,
                            fit=ft.ImageFit.CONTAIN,
                            semantics_label="Desporto Escolar",
                        ),
                        bgcolor="#FFFFFF",
                        padding=14,
                        border_radius=12,
                        alignment=ft.Alignment(0, 0),
                    ),
                ],
                spacing=20,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=24,
            border_radius=16,
            shadow=common.SOMBRA,
            **estilo_faixa,
        )

        # --- Indicadores -----------------------------------------------
        indicadores = ft.ResponsiveRow(
            [
                common.indicador("Inscrições", resumo["total"], ft.Icons.EDIT_NOTE,
                                 common.VERDE, col={"xs": 6, "sm": 4, "md": 2}),
                common.indicador("Participantes", resumo["participantes"],
                                 ft.Icons.DIRECTIONS_RUN, common.AZUL,
                                 col={"xs": 6, "sm": 4, "md": 2}),
                common.indicador("Dorsais", resumo["com_dorsal"],
                                 ft.Icons.CONFIRMATION_NUMBER, common.VERMELHO,
                                 col={"xs": 6, "sm": 4, "md": 2}),
                common.indicador("Chegadas", resumo["chegadas"], ft.Icons.TIMER_OUTLINED,
                                 "#B07A00", col={"xs": 6, "sm": 4, "md": 2}),
                common.indicador("Organização", resumo["organizacao"], ft.Icons.GROUPS,
                                 "#5B4B8A", col={"xs": 6, "sm": 4, "md": 2}),
                common.indicador("Turmas", len(turmas), ft.Icons.SCHOOL, "#0E7490",
                                 col={"xs": 6, "sm": 4, "md": 2}),
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
        for rotulo, concluido, destino in passos:
            if not concluido and proximo is None:
                proximo = (rotulo, destino)
            permitido = not permissoes.get(destino) or self.sessao.tem(permissoes[destino])
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
                            ft.TextButton(
                                "Abrir",
                                disabled=not permitido,
                                on_click=lambda _e, d=destino: self.navegar(d),
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.symmetric(horizontal=8, vertical=2),
                    border_radius=8,
                    bgcolor=common.CINZA_SUAVE if destacado else None,
                )
            )

        sugestao = (
            common.aviso(f"Próximo passo sugerido: {proximo[0]}.", common.VERDE)
            if proximo else common.aviso(
                "Processo completo: inscrições, partida, meta e resultados.", common.VERDE
            )
        )

        cartao_fluxo = common.cartao(
            common.titulo_seccao("Fluxo da atividade", ft.Icons.ACCOUNT_TREE),
            common.subtitulo("Sequência de trabalho dos secretariados, do início à divulgação."),
            *linhas_passo,
            col={"xs": 12, "lg": 8},
        )

        cartao_estado = common.cartao(
            common.titulo_seccao("InFormaçoes", ft.Icons.STORAGE),
            common.linha_info("Alunos carregados", len(self.configuracoes.listar_alunos())),
            common.linha_info("Turmas", len(turmas)),
            common.linha_info("Escalões definidos", len(self.configuracoes.listar_escaloes())),
            common.linha_info("Inscrições", resumo["total"]),
            common.linha_info("Dorsais entregues", resumo["com_dorsal"]),
            common.linha_info("Chegadas", resumo["chegadas"]),
            common.separador(),
            ft.Text(f"Cobertura da meta: {cobertura}%", size=11,
                    weight=ft.FontWeight.BOLD, color=common.TEXTO_SUAVE),
            ft.ProgressBar(value=cobertura / 100, color=common.VERDE,
                           bgcolor=common.VERDE_CLARO, height=8),
            col={"xs": 12, "lg": 4},
        )

        return ft.Column(
            [
                faixa,
                indicadores,
                sugestao,
                ft.ResponsiveRow(
                    [cartao_fluxo, cartao_estado],
                    spacing=16,
                    run_spacing=16,
                ),
            ],
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
