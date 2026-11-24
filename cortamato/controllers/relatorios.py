"""Relatórios, exportações (PDF/CSV) e comunicação aos diretores de turma."""

from __future__ import annotations

from ..models import repos_cadastro, repos_inscricoes, repos_prova
from ..models.repos_inscricoes import ETIQUETAS_ESTADO
from ..utils import datas, email_msg, exportacao
from .base import (P_EMAIL, P_RELATORIOS, ControladorBase, ErroValidacao, requer)
from .classificacoes import ControladorClassificacoes
from .configuracoes import ControladorConfiguracoes

DEFINICOES = [
    ("inscritos", "Participantes inscritos"),
    ("por_escalao", "Participantes por escalão"),
    ("dorsais", "Listas de dorsais"),
    ("individuais", "Classificações individuais"),
    ("coletivas", "Classificações coletivas"),
    ("apurados", "Lista de apurados para a fase seguinte"),
    ("organizacao", "Elementos de apoio à organização"),
    ("estatisticas", "Estatísticas da prova"),
]


class ControladorRelatorios(ControladorBase):
    def __init__(self, bd, sessao) -> None:
        super().__init__(bd, sessao)
        self._classificacoes = ControladorClassificacoes(bd, sessao)
        self._config = ControladorConfiguracoes(bd, sessao)

    # ------------------------------------------------------------------
    # Catálogo
    # ------------------------------------------------------------------
    def definicoes(self) -> list[tuple[str, str]]:
        return DEFINICOES

    def _subtitulo(self) -> str:
        dados = self._config.dados_atividade()
        return (
            f"{dados['designacao']} — {dados['edicao']} | "
            f"Prova: {dados['data_prova'] or '—'} | Local: {dados['local'] or '—'}"
        )

    # ------------------------------------------------------------------
    # Relatórios
    # ------------------------------------------------------------------
    def obter(self, chave: str) -> dict:
        construtores = {
            "inscritos": self._inscritos,
            "por_escalao": self._por_escalao,
            "dorsais": self._dorsais,
            "individuais": self._individuais,
            "coletivas": self._coletivas,
            "apurados": self._apurados,
            "organizacao": self._organizacao,
            "estatisticas": self._estatisticas,
        }
        construtor = construtores.get(chave)
        if construtor is None:
            raise ErroValidacao("Relatório desconhecido.")
        relatorio = construtor()
        relatorio["chave"] = chave
        relatorio["subtitulo"] = self._subtitulo()
        return relatorio

    def _inscritos(self) -> dict:
        registos = []
        for linha in repos_inscricoes.listar_inscricoes(self.bd):
            registos.append([
                linha["numero"] or "—",
                linha["aluno"],
                "M" if linha["sexo"] == "M" else "F",
                datas.formatar_data(linha["data_nascimento"]),
                linha["turma"] or "—",
                linha["escalao"] or "—",
                ETIQUETAS_ESTADO.get(linha["estado"], linha["estado"]),
                datas.formatar_data(linha["data_inscricao"]),
            ])
        return {
            "nome": "participantes_inscritos",
            "titulo": "Participantes inscritos",
            "cabecalho": ["Nº", "Nome", "Sexo", "Nascimento", "Turma", "Escalão", "Estado", "Inscrição"],
            "registos": registos,
            "larguras": [0.07, 0.29, 0.06, 0.12, 0.09, 0.13, 0.12, 0.12],
            "resumo": [f"Total de inscrições registadas: {len(registos)}"],
        }

    def _por_escalao(self) -> dict:
        grupos: dict[tuple[str, str], dict[str, int]] = {}
        for linha in repos_inscricoes.listar_inscricoes(self.bd):
            chave = (linha["escalao"] or "Sem escalão", linha["sexo"])
            dados = grupos.setdefault(chave, {"inscritos": 0, "participantes": 0, "chegadas": 0})
            dados["inscritos"] += 1
            if linha["estado"] == "participante":
                dados["participantes"] += 1
            if linha["chegada_ordem"]:
                dados["chegadas"] += 1

        registos = []
        for (escalao, sexo) in sorted(grupos):
            dados = grupos[(escalao, sexo)]
            registos.append([
                escalao,
                "Masculino" if sexo == "M" else "Feminino",
                dados["inscritos"],
                dados["participantes"],
                dados["chegadas"],
            ])
        return {
            "nome": "participantes_por_escalao",
            "titulo": "Participantes por escalão",
            "cabecalho": ["Escalão", "Sexo", "Inscritos", "Participantes", "Chegadas"],
            "registos": registos,
            "larguras": [0.30, 0.16, 0.18, 0.18, 0.18],
            "resumo": [f"Total de escalões/sexo com inscrições: {len(registos)}"],
        }

    def _dorsais(self) -> dict:
        registos = []
        for linha in sorted(repos_prova.listar_participantes(self.bd), key=lambda x: x["dorsal"]):
            registos.append([
                linha["dorsal"],
                linha["aluno"],
                linha["turma"] or "—",
                linha["escalao"] or "—",
                "M" if linha["sexo"] == "M" else "F",
                linha["hora_dorsal"] or "—",
            ])
        return {
            "nome": "listas_de_dorsais",
            "titulo": "Listas de dorsais",
            "cabecalho": ["Dorsal", "Nome", "Turma", "Escalão", "Sexo", "Hora entrega"],
            "registos": registos,
            "larguras": [0.10, 0.33, 0.11, 0.18, 0.08, 0.20],
            "resumo": [f"Dorsais entregues: {len(registos)}"],
        }

    def _individuais(self) -> dict:
        registos = []
        for linha in self._classificacoes.geral():
            registos.append([
                linha.ordem,
                linha.dorsal,
                linha.aluno,
                linha.turma,
                linha.escalao,
                "M" if linha.sexo == "Masculino" else "F",
                "—",
            ])
        return {
            "nome": "classificacoes_individuais",
            "titulo": "Classificações individuais",
            "cabecalho": ["Pos.", "Dorsal", "Nome", "Turma", "Escalão", "Sexo", "Obs."],
            "registos": registos,
            "larguras": [0.08, 0.10, 0.31, 0.11, 0.20, 0.08, 0.12],
            "resumo": [f"Atletas classificados: {len(registos)}"],
        }

    def _coletivas(self) -> dict:
        registos = []
        for linha in self._classificacoes.coletiva():
            registos.append([
                linha.posicao,
                linha.turma,
                linha.total_pontos,
                linha.classificados,
                linha.detalhe,
            ])
        return {
            "nome": "classificacoes_coletivas",
            "titulo": "Classificações coletivas",
            "cabecalho": ["Pos.", "Turma", "Pontos", "Classificados", "Melhores classificados"],
            "registos": registos,
            "larguras": [0.08, 0.15, 0.11, 0.15, 0.51],
            "resumo": [
                "A pontuação coletiva soma as posições obtidas nos respetivos escalões/sexo "
                f"(melhores {self._config._valor_config('pontos_coletiva', '4')} por turma). "
                "Menor pontuação = melhor classificação."
            ],
        }

    def _apurados(self) -> dict:
        registos = []
        for linha in self._classificacoes.apurados():
            registos.append([
                linha["grupo"],
                linha["posicao"],
                linha["dorsal"],
                linha["aluno"],
                linha["turma"],
            ])
        return {
            "nome": "apurados",
            "titulo": "Apurados para a fase seguinte",
            "cabecalho": ["Escalão", "Pos.", "Dorsal", "Nome", "Turma"],
            "registos": registos,
            "larguras": [0.26, 0.08, 0.10, 0.34, 0.22],
            "resumo": [f"Total de apurados: {len(registos)}"],
        }

    def _organizacao(self) -> dict:
        registos = []
        for linha in repos_inscricoes.listar_inscricoes(self.bd, estado="organizacao"):
            registos.append([
                linha["numero"] or "—",
                linha["aluno"],
                linha["turma"] or "—",
                ETIQUETAS_ESTADO.get(linha["estado"], linha["estado"]),
            ])
        return {
            "nome": "elementos_organizacao",
            "titulo": "Elementos de apoio à organização",
            "cabecalho": ["Nº", "Nome", "Turma", "Estado"],
            "registos": registos,
            "larguras": [0.13, 0.49, 0.17, 0.21],
            "resumo": [f"Total de elementos de apoio: {len(registos)}"],
        }

    def _estatisticas(self) -> dict:
        dados = self._classificacoes.estatisticas()
        inscricoes = repos_inscricoes.contar_inscricoes(self.bd)
        rotulos = [
            ("Inscrições registadas", inscricoes),
            ("Alunos inscritos como organização", repos_inscricoes.contar_inscricoes(self.bd, "organizacao")),
            ("Participantes com dorsal entregue", dados["participantes"]),
            ("Chegadas registadas", dados["chegadas"]),
            ("Desistências", dados["desistentes"]),
            ("Desclassificações", dados["desclassificados"]),
            ("Taxa de conclusão (%)", dados["cobertura"]),
            ("Turmas envolvidas", len(repos_cadastro.listar_turmas(self.bd))),
            ("Alunos carregados no sistema", repos_cadastro.contar_alunos(self.bd)),
        ]
        return {
            "nome": "estatisticas_prova",
            "titulo": "Estatísticas da prova",
            "cabecalho": ["Indicador", "Valor"],
            "registos": [[rotulo, valor] for rotulo, valor in rotulos],
            "larguras": [0.70, 0.30],
            "resumo": [],
        }

    # ------------------------------------------------------------------
    # Exportações
    # ------------------------------------------------------------------
    @requer(P_RELATORIOS)
    def exportar(self, chave: str, formato: str = "pdf"):
        relatorio = self.obter(chave)
        formato = (formato or "pdf").lower()
        if formato == "csv":
            return exportacao.exportar_csv(
                relatorio["nome"], relatorio["cabecalho"], relatorio["registos"]
            )
        if formato == "pdf":
            return exportacao.exportar_pdf(
                relatorio["nome"],
                relatorio["titulo"],
                relatorio["subtitulo"],
                relatorio["cabecalho"],
                relatorio["registos"],
                relatorio["larguras"],
                relatorio["resumo"],
            )
        raise ErroValidacao("Formato de exportação não suportado (use PDF ou CSV).")

    # ------------------------------------------------------------------
    # Comunicação aos diretores de turma
    # ------------------------------------------------------------------
    @requer(P_EMAIL)
    def comunicacao_dt(self) -> dict:
        por_turma: dict[str, dict] = {}
        for linha in repos_inscricoes.listar_inscricoes(self.bd):
            turma_codigo = linha["turma"] or "Sem turma"
            turma = repos_cadastro.obter_turma_por_codigo(self.bd, turma_codigo)
            dados = por_turma.setdefault(
                turma_codigo,
                {
                    "dt": (turma or {}).get("dt_nome") or "",
                    "email": (turma or {}).get("dt_email") or "",
                    "participantes": [],
                    "organizacao": [],
                },
            )
            if linha["estado"] == "participante":
                dados["participantes"].append(linha["aluno"])
            elif linha["estado"] == "organizacao":
                dados["organizacao"].append(linha["aluno"])

        atividade = self._config.dados_atividade()
        corpo = email_msg.construir_mensagem(
            atividade["designacao"], atividade["data_prova"], por_turma
        )
        destinatarios = [dados["email"] for dados in por_turma.values() if dados["email"]]
        return {
            "corpo": corpo,
            "por_turma": por_turma,
            "destinatarios": destinatarios,
            "remetente": self._config._valor_config("email_remetente", "direcao@aepbs.pt"),
            "assunto": f"Justificação de faltas — {atividade['designacao']} ({atividade['data_prova']})",
        }

    @requer(P_EMAIL)
    def exportar_comunicacao(self) -> tuple:
        dados = self.comunicacao_dt()
        texto = email_msg.guardar_texto(dados["corpo"])
        eml = email_msg.guardar_eml(
            dados["assunto"], dados["corpo"], dados["destinatarios"], dados["remetente"]
        )
        return texto, eml
