"""Configurações da atividade, escalões etários e regras de apuramento."""

from __future__ import annotations

import pymysql

from ..models import repos_cadastro
from ..utils import datas
from .base import P_CONFIG, ControladorBase, ErroValidacao, requer

CHAVES_ATIVIDADE = (
    "designacao_atividade",
    "edicao",
    "data_prova",
    "hora_partida",
    "local",
    "prazo_inscricoes",
    "ano_referencia_idades",
    "dorsais_inicio",
    "apurados_por_escalao",
    "pontos_coletiva",
    "email_remetente",
)


class ControladorConfiguracoes(ControladorBase):
    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------
    def todas(self) -> dict[str, str]:
        return repos_cadastro.todas_configuracoes(self.bd)

    def ano_referencia(self) -> int:
        try:
            return int(self._valor_config("ano_referencia_idades", "2026"))
        except ValueError:
            return 2026

    def dados_atividade(self) -> dict:
        config = self.todas()
        return {
            "designacao": config.get("designacao_atividade", "Corta-Mato Escolar"),
            "edicao": config.get("edicao", ""),
            "data_prova": datas.formatar_data(config.get("data_prova", "")),
            "hora_partida": config.get("hora_partida", ""),
            "local": config.get("local", ""),
            "data_prova_iso": config.get("data_prova", ""),
        }

    def listar_escaloes(self, apenas_ativos: bool = False) -> list[dict]:
        return repos_cadastro.listar_escaloes(self.bd, apenas_ativos)

    def listar_turmas(self) -> list[dict]:
        return repos_cadastro.listar_turmas(self.bd)

    def listar_alunos(self, pesquisa: str = "") -> list[dict]:
        return repos_cadastro.listar_alunos(self.bd, pesquisa)

    def aluno_por_cartao(self, codigo: str) -> dict | None:
        """Identifica o aluno pelo código do cartão (leitura do QRCode)."""
        return repos_cadastro.obter_aluno_por_cartao(self.bd, (codigo or "").strip())

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------
    @requer(P_CONFIG)
    def guardar_atividade(self, valores: dict[str, str]) -> None:
        if not (valores.get("designacao_atividade") or "").strip():
            raise ErroValidacao("A designação da atividade é obrigatória.")

        data_prova = datas.normalizar_data(valores.get("data_prova", ""))
        if valores.get("data_prova") and not data_prova:
            raise ErroValidacao("Data da prova inválida (use dd/mm/aaaa).")
        prazo = datas.normalizar_data(valores.get("prazo_inscricoes", ""))
        if valores.get("prazo_inscricoes") and not prazo:
            raise ErroValidacao("Prazo de inscrições inválido (use dd/mm/aaaa).")

        ano = str(valores.get("ano_referencia_idades", "")).strip()
        if not ano.isdigit() or not (2000 <= int(ano) <= 2100):
            raise ErroValidacao("Ano de referência das idades inválido.")

        for chave in ("apurados_por_escalao", "pontos_coletiva", "dorsais_inicio"):
            valor = str(valores.get(chave, "")).strip()
            if not valor.isdigit():
                raise ErroValidacao(f"O campo {chave.replace('_', ' ')} deve ser numérico.")

        dados = dict(valores)
        if data_prova:
            dados["data_prova"] = data_prova
        if prazo:
            dados["prazo_inscricoes"] = prazo
        for chave in CHAVES_ATIVIDADE:
            if chave in dados:
                repos_cadastro.definir_configuracao(self.bd, chave, str(dados[chave]).strip())

    @requer(P_CONFIG)
    def criar_escalao(self, designacao: str, sexo: str, idade_min: str,
                      idade_max: str, apurados: str) -> int:
        designacao = (designacao or "").strip()
        if not designacao:
            raise ErroValidacao("Indique a designação do escalão.")
        if sexo not in ("M", "F"):
            raise ErroValidacao("Selecione o sexo do escalão.")
        try:
            minimo, maximo, num_apurados = int(idade_min), int(idade_max), int(apurados or 0)
        except (TypeError, ValueError):
            raise ErroValidacao("As idades e o número de apurados devem ser numéricos.")
        if minimo > maximo:
            raise ErroValidacao("A idade mínima não pode ser superior à idade máxima.")
        try:
            return repos_cadastro.criar_escalao(
                self.bd, designacao, sexo, minimo, maximo, num_apurados
            )
        except pymysql.err.IntegrityError:
            raise ErroValidacao("Já existe um escalão com essa designação para esse sexo.")

    @requer(P_CONFIG)
    def atualizar_escalao(self, escalao_id: int, designacao: str, sexo: str,
                          idade_min: str, idade_max: str, apurados: str,
                          ativo: bool) -> None:
        try:
            minimo, maximo, num_apurados = int(idade_min), int(idade_max), int(apurados or 0)
        except (TypeError, ValueError):
            raise ErroValidacao("As idades e o número de apurados devem ser numéricos.")
        if minimo > maximo:
            raise ErroValidacao("A idade mínima não pode ser superior à idade máxima.")
        try:
            repos_cadastro.atualizar_escalao(
                self.bd, int(escalao_id), (designacao or "").strip(), sexo,
                minimo, maximo, num_apurados, 1 if ativo else 0,
            )
        except pymysql.err.IntegrityError:
            raise ErroValidacao("Já existe um escalão com essa designação para esse sexo.")

    # ------------------------------------------------------------------
    # Regras
    # ------------------------------------------------------------------
    def determinar_escalao(self, sexo: str, data_nascimento: str | None) -> dict | None:
        idade = datas.idade_em_ano(data_nascimento, self.ano_referencia())
        return repos_cadastro.escalao_para(self.bd, sexo, idade)

    def apurados_por_escalao(self, escalao: dict | None) -> int:
        if escalao and escalao.get("apurados"):
            return int(escalao["apurados"])
        return self._config_inteiro("apurados_por_escalao", 6)
