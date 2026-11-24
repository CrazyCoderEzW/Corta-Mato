"""Infraestrutura da base de dados relacional MySQL (camada Model)."""

from __future__ import annotations

import os
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pymysql
from pymysql.cursors import DictCursor

CAMINHO_SCHEMA = Path(__file__).resolve().parents[1] / "schema.sql"

SERVIDOR = os.getenv("CORTAMATO_BD_HOST", "localhost")
PORTA = int(os.getenv("CORTAMATO_BD_PORTA", "3306"))
UTILIZADOR = os.getenv("CORTAMATO_BD_UTILIZADOR", "root")
PASSWORD = os.getenv("CORTAMATO_BD_PASSWORD", "")
NOME_BD_PADRAO = os.getenv("CORTAMATO_BD_NOME", "corta_mato")


class ErroLigacaoBD(RuntimeError):
    """Falha ao ligar ao servidor MySQL (servidor desligado, credenciais, ...)."""


def _configuracao(nome_bd: str | None = None) -> dict:
    config: dict = {
        "host": SERVIDOR,
        "port": PORTA,
        "user": UTILIZADOR,
        "password": PASSWORD,
        "charset": "utf8mb4",
        "connect_timeout": 10,
        "autocommit": False,
    }
    if nome_bd:
        config["database"] = nome_bd
    return config


def _dica_erro(erro: Exception) -> str:
    codigo = erro.args[0] if erro.args else None
    if codigo == 1130:
        return (
            "O servidor recusou a ligação antes de verificar a palavra-passe: não "
            f"existe conta para '{UTILIZADOR}' a partir deste host ('localhost'). "
            "No Shell do MySQL do XAMPP execute:\n"
            f"  CREATE USER IF NOT EXISTS '{UTILIZADOR}'@'localhost' IDENTIFIED BY '';\n"
            f"  GRANT ALL PRIVILEGES ON *.* TO '{UTILIZADOR}'@'localhost' WITH GRANT OPTION;\n"
            "  FLUSH PRIVILEGES;\n"
            "Se até o Shell der o mesmo erro 1130, pare o MySQL no painel do XAMPP e "
            "arranque-o com 'C:\\xampp\\mysql\\bin\\mysqld --console "
            "--skip-grant-tables', corra os comandos acima, pare e volte a arrancar o "
            "MySQL normalmente."
        )
    if codigo == 1045:
        return (
            f"A conta '{UTILIZADOR}' existe mas a palavra-passe está errada. Defina "
            "CORTAMATO_BD_PASSWORD com a palavra-passe correta (no XAMPP, por omissão, "
            "o root não tem palavra-passe)."
        )
    if codigo == 1049:
        return (
            "A ligação funcionou mas a base de dados não existe. A aplicação cria-a na "
            "primeira execução, desde que o utilizador tenha permissão CREATE."
        )
    if codigo in (1044, 1142):
        return (
            "A ligação funcionou mas faltam privilégios sobre a base de dados. Conceda-os "
            f"com: GRANT ALL PRIVILEGES ON *.* TO '{UTILIZADOR}'@'localhost'; "
            "FLUSH PRIVILEGES;"
        )
    if codigo in (2003, 2006, 2013):
        return (
            f"Não há nenhum servidor a escutar em {SERVIDOR}:{PORTA}. Arranque o MySQL "
            "no painel do XAMPP e confirme que nenhum outro programa ocupa essa porta."
        )
    return ""


def _mensagem_erro(erro: Exception, nome_bd: str | None = None) -> str:
    alvo = f"em {SERVIDOR}:{PORTA}"
    if nome_bd:
        alvo += f" (base de dados '{nome_bd}')"
    texto = (
        f"Não foi possível ligar ao servidor MySQL {alvo} "
        f"com o utilizador '{UTILIZADOR}'.\n"
        f"Detalhe do servidor: {erro}\n\n"
        "Confirme que o servidor MySQL está a correr e que as credenciais estão "
        "corretas. Pode configurá-las nas variáveis de ambiente CORTAMATO_BD_HOST, "
        "CORTAMATO_BD_PORTA, CORTAMATO_BD_UTILIZADOR, CORTAMATO_BD_PASSWORD e "
        "CORTAMATO_BD_NOME."
    )
    dica = _dica_erro(erro)
    return f"{texto}\n\n{dica}" if dica else texto


def _normalizar_valor(valor):
    """Devolve datas/horas como texto, tal como eram guardadas no modelo anterior."""
    if isinstance(valor, (datetime, date, time, timedelta)):
        return str(valor)
    return valor


def _normalizar_linha(linha: dict) -> dict:
    return {chave: _normalizar_valor(valor) for chave, valor in linha.items()}


def dividir_instrucoes(script: str) -> list[str]:
    """Separa um script SQL em instruções, ignorando linhas de comentário."""
    linhas = [
        linha for linha in script.splitlines()
        if not linha.strip().startswith("--")
    ]
    return [parte.strip() for parte in "\n".join(linhas).split(";") if parte.strip()]


class BD:
    """Ligação ao MySQL com criação automática da base de dados, do esquema e do admin."""

    def __init__(self, nome_bd: str | None = None, recriar: bool = False) -> None:
        self.nome_bd = nome_bd or NOME_BD_PADRAO
        if not re.fullmatch(r"[A-Za-z0-9_]+", self.nome_bd):
            raise ErroLigacaoBD(f"Nome de base de dados inválido: {self.nome_bd!r}")
        self.criar_base_dados(recriar=recriar)
        self.migrar_estrutura()
        self.criar_estrutura()
        self.criar_administrador()

    def ligar(self):
        try:
            return pymysql.connect(database=self.nome_bd, **_configuracao())
        except pymysql.err.OperationalError as erro:
            raise ErroLigacaoBD(_mensagem_erro(erro, self.nome_bd)) from erro

    def criar_base_dados(self, recriar: bool = False) -> None:
        """Cria a base de dados (utf8mb4); com `recriar` apaga-a e volta a criar."""
        try:
            con = pymysql.connect(**_configuracao())
        except pymysql.err.OperationalError as erro:
            raise ErroLigacaoBD(_mensagem_erro(erro)) from erro
        try:
            with con.cursor() as cursor:
                if recriar:
                    cursor.execute(f"DROP DATABASE IF EXISTS `{self.nome_bd}`")
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{self.nome_bd}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            con.commit()
        finally:
            con.close()

    def migrar_estrutura(self) -> None:
        """Atualiza bases de dados antigas, renomeando a coluna `genero` para `sexo`."""
        con = self.ligar()
        try:
            with con.cursor() as cursor:
                for tabela in ("aluno", "escalao"):
                    if not self._coluna_existe(cursor, tabela, "genero"):
                        continue
                    if self._coluna_existe(cursor, tabela, "sexo"):
                        continue
                    try:
                        cursor.execute(
                            f"ALTER TABLE `{tabela}` CHANGE COLUMN `genero` `sexo` CHAR(1) NOT NULL"
                        )
                    except pymysql.err.MySQLError:
                        # Algumas versões do MySQL/MariaDB recusam renomear uma coluna
                        # usada por uma restrição CHECK; remove-a e volta a criar.
                        for restricao in self._restricoes_com_coluna(cursor, tabela, "genero"):
                            cursor.execute(f"ALTER TABLE `{tabela}` DROP CONSTRAINT `{restricao}`")
                        cursor.execute(
                            f"ALTER TABLE `{tabela}` CHANGE COLUMN `genero` `sexo` CHAR(1) NOT NULL"
                        )
                        cursor.execute(
                            f"ALTER TABLE `{tabela}` ADD CONSTRAINT `chk_{tabela}_sexo` "
                            "CHECK (`sexo` IN ('M', 'F'))"
                        )
            con.commit()
        finally:
            con.close()

    @staticmethod
    def _coluna_existe(cursor, tabela: str, coluna: str) -> bool:
        cursor.execute(
            "SELECT 1 FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
            (tabela, coluna),
        )
        return cursor.fetchone() is not None

    @staticmethod
    def _restricoes_com_coluna(cursor, tabela: str, coluna: str) -> list[str]:
        try:
            cursor.execute(
                "SELECT cc.CONSTRAINT_NAME, cc.CHECK_CLAUSE "
                "FROM information_schema.CHECK_CONSTRAINTS cc "
                "JOIN information_schema.TABLE_CONSTRAINTS tc "
                "  ON tc.CONSTRAINT_SCHEMA = cc.CONSTRAINT_SCHEMA "
                " AND tc.CONSTRAINT_NAME = cc.CONSTRAINT_NAME "
                "WHERE cc.CONSTRAINT_SCHEMA = DATABASE() AND tc.TABLE_NAME = %s",
                (tabela,),
            )
        except pymysql.err.MySQLError:
            return []
        return [nome for nome, clausula in cursor.fetchall() if coluna in (clausula or "")]

    def criar_estrutura(self) -> None:
        instrucoes = dividir_instrucoes(CAMINHO_SCHEMA.read_text(encoding="utf-8"))
        con = self.ligar()
        try:
            with con.cursor() as cursor:
                for instrucao in instrucoes:
                    cursor.execute(instrucao)
            con.commit()
        finally:
            con.close()

    def criar_administrador(self) -> None:
        """Cria a conta inicial (admin / admin123) se ainda não existir nenhum responsável."""
        from ..utils.seguranca import gerar_hash

        existente = self.consultar_um("SELECT id FROM responsavel LIMIT 1")
        if existente:
            return
        perfil = self.consultar_um("SELECT id FROM perfil WHERE nome = 'Administrador'")
        if not perfil:
            return
        self.executar(
            "INSERT INTO responsavel (nome, email, username, password_hash, perfil_id, ativo) "
            "VALUES (%s, %s, %s, %s, %s, 1)",
            ("Administrador do Sistema", "admin@aepbs.pt", "admin", gerar_hash("admin123"), perfil["id"]),
        )

    def consultar(self, sql: str, parametros: tuple = ()) -> list[dict]:
        con = self.ligar()
        try:
            with con.cursor(DictCursor) as cursor:
                cursor.execute(sql, parametros or None)
                return [_normalizar_linha(linha) for linha in cursor.fetchall()]
        finally:
            con.close()

    def consultar_um(self, sql: str, parametros: tuple = ()) -> dict | None:
        con = self.ligar()
        try:
            with con.cursor(DictCursor) as cursor:
                cursor.execute(sql, parametros or None)
                linha = cursor.fetchone()
                return _normalizar_linha(linha) if linha else None
        finally:
            con.close()

    def executar(self, sql: str, parametros: tuple = ()) -> int:
        con = self.ligar()
        try:
            with con.cursor() as cursor:
                cursor.execute(sql, parametros or None)
                con.commit()
                return int(cursor.lastrowid or 0)
        finally:
            con.close()

    def executar_muitos(self, sql: str, registos: list[tuple]) -> None:
        con = self.ligar()
        try:
            with con.cursor() as cursor:
                cursor.executemany(sql, registos)
            con.commit()
        finally:
            con.close()
