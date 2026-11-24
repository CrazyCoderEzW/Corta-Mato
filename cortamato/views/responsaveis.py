"""Vista de gestão de responsáveis, contas e matriz de permissões."""

from __future__ import annotations

import flet as ft

from ..controllers.base import ErroValidacao, PermissaoNegada
from . import common


def construir(app) -> ft.Control:
    page = app.page
    controlador = app.responsaveis

    perfis = controlador.listar_perfis()
    opcoes_perfis = [(perfil["id"], perfil["nome"]) for perfil in perfis]
    responsaveis = controlador.listar()

    # ------------------------------------------------------------------
    # Novo responsável
    # ------------------------------------------------------------------
    nome_novo = common.campo("Nome", "", 260)
    email_novo = common.campo("E-mail", "", 260)
    utilizador_novo = common.campo("Utilizador", "", 200)
    password_nova = common.campo("Palavra-passe", "", 200, password=True,
                                 can_reveal_password=True)
    perfil_novo = common.menu_suspenso("Perfil de acesso", opcoes_perfis, largura=300)

    def criar(_evento):
        try:
            controlador.criar(
                nome_novo.value or "", email_novo.value or "", utilizador_novo.value or "",
                password_nova.value or "",
                int(perfil_novo.value) if perfil_novo.value else 0,
            )
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        common.mensagem(page, "Responsável criado com sucesso.")
        app.navegar("responsaveis")

    bloco_novo = common.cartao(
        ft.Text("Novo responsável", size=15, weight=ft.FontWeight.BOLD),
        ft.Row([nome_novo, email_novo, utilizador_novo, password_nova], wrap=True, spacing=12),
        ft.Row([perfil_novo], wrap=True),
        ft.Row([common.botao("Criar responsável", criar, icone=ft.Icons.PERSON_ADD)]),
    )

    # ------------------------------------------------------------------
    # Edição
    # ------------------------------------------------------------------
    seletor = common.menu_suspenso(
        "Responsável",
        [(item["id"], f"{item['nome']} — {item['perfil']}") for item in responsaveis],
        largura=380,
    )
    nome_edicao = common.campo("Nome", "", 260)
    email_edicao = common.campo("E-mail", "", 260)
    perfil_edicao = common.menu_suspenso("Perfil", opcoes_perfis, largura=300)
    ativo_edicao = ft.Checkbox(label="Conta ativa", value=True)
    password_repor = common.campo("Nova palavra-passe", "", 220, password=True,
                                  can_reveal_password=True)

    def preencher(_evento=None):
        escolhido = next(
            (item for item in responsaveis if str(item["id"]) == str(seletor.value)), None
        )
        if not escolhido:
            return
        nome_edicao.value = escolhido["nome"]
        email_edicao.value = escolhido["email"]
        perfil_edicao.value = str(escolhido["perfil_id"])
        ativo_edicao.value = bool(escolhido["ativo"])
        page.update()

    seletor.on_change = preencher

    def guardar(_evento):
        if not seletor.value:
            common.mensagem(page, "Selecione o responsável a alterar.", erro=True)
            return
        try:
            controlador.atualizar(
                int(seletor.value), nome_edicao.value or "", email_edicao.value or "",
                int(perfil_edicao.value) if perfil_edicao.value else 0,
                bool(ativo_edicao.value),
            )
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        common.mensagem(page, "Responsável atualizado.")
        app.navegar("responsaveis")

    def alternar_estado(_evento):
        if not seletor.value:
            common.mensagem(page, "Selecione o responsável.", erro=True)
            return
        try:
            controlador.definir_estado(int(seletor.value), not bool(ativo_edicao.value))
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        common.mensagem(page, "Estado da conta alterado.")
        app.navegar("responsaveis")

    def redefinir(_evento):
        if not seletor.value:
            common.mensagem(page, "Selecione o responsável.", erro=True)
            return
        try:
            controlador.redefinir_password(int(seletor.value), password_repor.value or "")
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        common.mensagem(page, "Palavra-passe redefinida.")
        app.navegar("responsaveis")

    bloco_edicao = common.cartao(
        ft.Text("Editar responsável", size=15, weight=ft.FontWeight.BOLD),
        ft.Row([seletor], wrap=True),
        ft.Row([nome_edicao, email_edicao, perfil_edicao], wrap=True, spacing=12),
        ft.Row([ativo_edicao,
                common.botao("Guardar alterações", guardar, icone=ft.Icons.SAVE),
                common.botao("Ativar/Desativar", alternar_estado, principal=False,
                             icone=ft.Icons.LOCK)], wrap=True, spacing=10),
        common.separador(),
        ft.Row([password_repor,
                common.botao("Redefinir palavra-passe", redefinir, principal=False,
                             icone=ft.Icons.KEY)]),
    )

    # ------------------------------------------------------------------
    # Lista e matriz
    # ------------------------------------------------------------------
    bloco_lista = common.cartao(
        ft.Text(f"Responsáveis registados ({len(responsaveis)})", size=15,
                weight=ft.FontWeight.BOLD),
        common.tabela(
            ["Nome", "Utilizador", "E-mail", "Perfil", "Ativo", "Criado em"],
            [[item["nome"], item["username"], item["email"], item["perfil"],
              "Sim" if item["ativo"] else "Não", item["criado_em"]] for item in responsaveis],
        ),
    )

    matriz = controlador.matriz_permissoes()
    bloco_matriz = common.cartao(
        ft.Text("Matriz de perfis e permissões", size=15, weight=ft.FontWeight.BOLD),
        common.subtitulo(
            "Cada perfil recebe apenas as permissões necessárias à sua função no processo."
        ),
        common.tabela(
            ["Perfil", "Permissões"],
            [[perfil["nome"], ", ".join(perfil["permissoes"]) or "—"] for perfil in matriz],
        ),
    )

    return ft.Column(
        [common.titulo("Gestão de responsáveis"),
         bloco_novo,
         bloco_edicao,
         bloco_lista,
         bloco_matriz],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )
