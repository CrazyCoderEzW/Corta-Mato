"""Importação de turmas, diretores de turma e alunos a partir de ficheiros CSV."""

from __future__ import annotations

import csv
from pathlib import Path

from ..models import repos_cadastro
from ..utils import datas
from .base import P_IMPORTAR, ControladorBase, ErroValidacao, requer

PASTA_MODELOS = Path(__file__).resolve().parents[2] / "modelos_csv"

CABECALHO_TURMAS = ["codigo", "designacao", "ano", "dt_nome", "dt_email"]
CABECALHO_ALUNOS = ["numero", "nome", "sexo", "data_nascimento", "turma", "codigo_cartao"]


def _ler_csv(caminho: str) -> list[dict]:
    ficheiro = Path(caminho)
    if not ficheiro.exists():
        raise ErroValidacao(f"Ficheiro não encontrado: {caminho}")
    if ficheiro.suffix.lower() != ".csv":
        raise ErroValidacao("O ficheiro deve ter a extensão .csv")

    conteudo = ""
    for codificacao in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            conteudo = ficheiro.read_text(encoding=codificacao)
            break
        except UnicodeDecodeError:
            continue
    if not conteudo.strip():
        raise ErroValidacao("O ficheiro CSV está vazio.")

    delimitador = ";"
    try:
        amostra = conteudo[:4096]
        dialeto = csv.Sniffer().sniff(amostra, delimiters=";,")
        delimitador = dialeto.delimiter
    except csv.Error:
        delimitador = ";" if ";" in conteudo.splitlines()[0] else ","

    linhas = list(csv.DictReader(conteudo.splitlines(), delimiter=delimitador))
    if not linhas:
        raise ErroValidacao("O CSV não contém linhas de dados.")

    registos: list[dict] = []
    for linha in linhas:
        registo = {}
        for chave, valor in linha.items():
            if chave is None:
                continue
            registo[chave.strip().lower()] = (valor or "").strip()
        registos.append(registo)
    return registos


def _campo(registo: dict, *nomes: str) -> str:
    for nome in nomes:
        if nome in registo and registo[nome]:
            return registo[nome]
    return ""


def _normalizar_sexo(valor: str) -> str:
    texto = (valor or "").strip().upper()
    if texto in ("M", "MASC", "MASCULINO", "MASCULINO "):
        return "M"
    if texto in ("F", "FEM", "FEMININO"):
        return "F"
    return ""


class ControladorImportacao(ControladorBase):
    def escrever_modelos(self) -> tuple[Path, Path]:
        PASTA_MODELOS.mkdir(parents=True, exist_ok=True)
        turmas = PASTA_MODELOS / "modelo_turmas.csv"
        alunos = PASTA_MODELOS / "modelo_alunos.csv"
        if not turmas.exists():
            turmas.write_text(
                ";".join(CABECALHO_TURMAS) + "\n10A;10º Ano A;10;Prof. Maria Silva;maria.silva@aepbs.pt\n",
                encoding="utf-8-sig",
            )
        if not alunos.exists():
            alunos.write_text(
                ";".join(CABECALHO_ALUNOS)
                + "\n12345;João Pereira;M;14/05/2012;10A;CART-12345\n",
                encoding="utf-8-sig",
            )
        return turmas, alunos

    @requer(P_IMPORTAR)
    def importar_turmas(self, caminho: str) -> dict:
        registos = _ler_csv(caminho)
        criadas = atualizadas = 0
        erros: list[str] = []

        for indice, registo in enumerate(registos, start=2):
            codigo = _campo(registo, "codigo", "turma", "codigo_turma")
            if not codigo:
                erros.append(f"Linha {indice}: código de turma em falta.")
                continue
            designacao = _campo(registo, "designacao", "nome") or codigo
            ano_texto = _campo(registo, "ano", "ano_escolar")
            try:
                ano = int(float(ano_texto)) if ano_texto else None
            except ValueError:
                ano = None
            dt_nome = _campo(registo, "dt_nome", "dt", "diretor_turma", "diretor")
            dt_email = _campo(registo, "dt_email", "email_dt", "email")

            existente = repos_cadastro.obter_turma_por_codigo(self.bd, codigo)
            try:
                if existente:
                    repos_cadastro.atualizar_turma(
                        self.bd, int(existente["id"]), designacao, ano, dt_nome, dt_email
                    )
                    atualizadas += 1
                else:
                    repos_cadastro.criar_turma(self.bd, codigo, designacao, ano, dt_nome, dt_email)
                    criadas += 1
            except Exception as erro:  # noqa: BLE001 - reportado ao utilizador
                erros.append(f"Linha {indice}: {erro}")

        return {"criadas": criadas, "atualizadas": atualizadas, "erros": erros,
                "total": len(registos)}

    @requer(P_IMPORTAR)
    def importar_alunos(self, caminho: str) -> dict:
        registos = _ler_csv(caminho)
        criados = atualizados = 0
        erros: list[str] = []

        for indice, registo in enumerate(registos, start=2):
            numero = _campo(registo, "numero", "nº", "num")
            nome = _campo(registo, "nome", "nome_aluno")
            sexo = _normalizar_sexo(_campo(registo, "sexo", "genero"))
            data_nascimento = datas.normalizar_data(_campo(registo, "data_nascimento", "data_nasc", "nascimento"))
            codigo_turma = _campo(registo, "turma", "codigo_turma", "cod_turma")

            if not numero or not nome:
                erros.append(f"Linha {indice}: número e nome são obrigatórios.")
                continue
            if not sexo:
                erros.append(f"Linha {indice}: sexo inválido (use M ou F).")
                continue
            if not data_nascimento:
                erros.append(f"Linha {indice}: data de nascimento inválida (use dd/mm/aaaa).")
                continue

            turma = repos_cadastro.obter_turma_por_codigo(self.bd, codigo_turma) if codigo_turma else None
            if codigo_turma and not turma:
                erros.append(f"Linha {indice}: turma '{codigo_turma}' não existe (importe as turmas primeiro).")
                continue
            turma_id = int(turma["id"]) if turma else None

            existente = repos_cadastro.obter_aluno_por_numero(self.bd, numero, turma_id)
            try:
                if existente:
                    repos_cadastro.atualizar_aluno(
                        self.bd, int(existente["id"]), nome, sexo, data_nascimento, turma_id, 1
                    )
                    atualizados += 1
                else:
                    repos_cadastro.criar_aluno(
                        self.bd, numero, nome, sexo, data_nascimento, turma_id,
                        _campo(registo, "codigo_cartao", "cartao"),
                    )
                    criados += 1
            except Exception as erro:  # noqa: BLE001 - reportado ao utilizador
                erros.append(f"Linha {indice}: {erro}")

        return {"criados": criados, "atualizados": atualizados, "erros": erros,
                "total": len(registos)}
