"""Funções de segurança para autenticação (PBKDF2-HMAC-SHA256 com salt)."""

from __future__ import annotations

import hashlib
import hmac
import os

ITERACOES = 120_000


def gerar_hash(password: str) -> str:
    """Gera o hash da password no formato pbkdf2_sha256$iteracoes$salt$hash."""
    salt = os.urandom(16)
    derivado = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERACOES)
    return f"pbkdf2_sha256${ITERACOES}${salt.hex()}${derivado.hex()}"


def verificar_password(password: str, hash_guardado: str) -> bool:
    try:
        algoritmo, iteracoes, salt_hex, hash_hex = hash_guardado.split("$")
    except (ValueError, AttributeError):
        return False
    if algoritmo != "pbkdf2_sha256":
        return False
    try:
        salt = bytes.fromhex(salt_hex)
        esperado = bytes.fromhex(hash_hex)
        iteracoes_int = int(iteracoes)
    except ValueError:
        return False
    derivado = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iteracoes_int)
    return hmac.compare_digest(derivado, esperado)
