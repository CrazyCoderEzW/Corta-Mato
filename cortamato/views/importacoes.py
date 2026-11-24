"""Vista de importação de turmas, diretores de turma e alunos (CSV)."""

from __future__ import annotations

import flet as ft

from ..controllers.base import ErroValidacao, PermissaoNegada
from . import common


def _resultado(page: ft.Page, titulo: str, resultado: dict) -> ft.Control:
    linhas = [
        common.linha_info("Linhas lidas", resultado["total"]),
        common.linha_info("Registos criados", resultado.get("criados", resultado.get("criadas", 0))),
        common.linha_info("Registos atualizados", resultado["atualizados"]),
        common.linha_info("Erros", len(resultado["erros"])),
    ]
    controlos: list[ft.Control] = [
        ft.Text(titulo, size=14, weight=ft.FontWeight.BOLD),
        *linhas,
    ]
    if resultado["erros"]:
        controlos.append(common.aviso("Algumas linhas não foram importadas:", common.ERRO))
        controlos.append(
            ft.Column([ft.Text(f"• {erro}", size=11, color=common.ERRO)
                       for erro in resultado["erros"][:30]],
                      spacing=2, scroll=ft.ScrollMode.AUTO, height=180)
        )
    return common.cartao(*controlos)


def construir(app) -> ft.Control:
    page = app.page
    controlador = app.importacao

    caminho_turmas = common.campo("Caminho do CSV de turmas", "", 420)
    caminho_alunos = common.campo("Caminho do CSV de alunos", "", 420)
    area_resultados = ft.Column([], spacing=12)

    def importar_turmas(_evento):
        try:
            resultado = controlador.importar_turmas(caminho_turmas.value or "")
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        area_resultados.controls.append(_resultado(page, "Importação de turmas", resultado))
        common.mensagem(page, "Importação de turmas concluída.")
        page.update()

    def importar_alunos(_evento):
        try:
            resultado = controlador.importar_alunos(caminho_alunos.value or "")
        except (ErroValidacao, PermissaoNegada) as erro:
            common.mensagem(page, str(erro), erro=True)
            return
        area_resultados.controls.append(_resultado(page, "Importação de alunos", resultado))
        common.mensagem(page, "Importação de alunos concluída.")
        page.update()

    def criar_modelos(_evento):
        try:
            turmas, alunos = controlador.escrever_modelos()
        except Exception as erro:  # noqa: BLE001
            common.mensagem(page, f"Não foi possível criar os modelos: {erro}", erro=True)
            return
        caminho_turmas.value = str(turmas)
        caminho_alunos.value = str(alunos)
        common.mensagem(page, "Modelos CSV criados na pasta modelos_csv.")
        page.update()

    bloco_instrucoes = common.cartao(
        ft.Text("Formato dos ficheiros CSV", size=15, weight=ft.FontWeight.BOLD),
        common.subtitulo(
            "Ficheiros separados por «;» (ou «,»), com cabeçalho. Codificação UTF-8 ou ANSI."
        ),
        ft.Row([
            ft.Column([
                ft.Text("Turmas", size=12, weight=ft.FontWeight.BOLD),
                ft.Text("codigo;designacao;ano;dt_nome;dt_email", size=11,
                        color=common.TEXTO_SUAVE, selectable=True),
            ], spacing=2, width=380),
            ft.Column([
                ft.Text("Alunos", size=12, weight=ft.FontWeight.BOLD),
                ft.Text("numero;nome;sexo;data_nascimento;turma;codigo_cartao", size=11,
                        color=common.TEXTO_SUAVE, selectable=True),
            ], spacing=2, width=420),
        ], wrap=True, spacing=20),
        common.subtitulo(
            "O sexo deve ser M/F e a data de nascimento no formato dd/mm/aaaa. "
            "Importe primeiro as turmas, para que os alunos possam ser associados."
        ),
        ft.Row([common.botao("Criar modelos CSV", criar_modelos, principal=False)])
    )

    bloco_turmas = common.cartao(
        ft.Text("1. Turmas e diretores de turma", size=15, weight=ft.FontWeight.BOLD),
        ft.Row([caminho_turmas,
                common.botao("Importar turmas", importar_turmas, icone=ft.Icons.UPLOAD_FILE)]),
    )

    bloco_alunos = common.cartao(
        ft.Text("2. Alunos", size=15, weight=ft.FontWeight.BOLD),
        ft.Row([caminho_alunos,
                common.botao("Importar alunos", importar_alunos, icone=ft.Icons.UPLOAD_FILE)]),
        common.subtitulo("Os alunos já existentes (mesmo número e turma) são atualizados."),
    )

    resumo = common.cartao(
        ft.Text("Dados atualmente na base de dados", size=15, weight=ft.FontWeight.BOLD),
        common.linha_info("Turmas", len(app.configuracoes.listar_turmas())),
        common.linha_info("Alunos", len(app.configuracoes.listar_alunos())),
        ft.Row([common.botao("Ver configurações", lambda _e: app.navegar("configuracoes"),
                             principal=False)]),
    )

    return ft.Column(
        [common.titulo("Importações CSV"),
         bloco_instrucoes,
         bloco_turmas,
         bloco_alunos,
         area_resultados,
         resumo],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )
