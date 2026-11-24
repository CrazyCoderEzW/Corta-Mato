

from __future__ import annotations

import binascii
import shutil
import struct
import zlib
from collections import deque
from pathlib import Path

ASSINATURA = b"\x89PNG\r\n\x1a\n"

#: Canal mínimo para um pixel contar como fundo claro.
LIMIAR_CLARO = 236

#: Versão gerada a partir do logótipo com fundo (guardada em `assets`).
NOME_GERADO = "desporto_escolar_transparente.png"

#: Emblema recortado, sem a legenda (para fundos escuros).
NOME_EMBLEMA = "desporto_escolar_emblema.png"

#: Versão do logótipo numa cor sólida, para fundos claros.
NOME_ESCURO = "desporto_escolar_escuro.png"

#: Verde da marca (equivalente a `common.VERDE_PROFUNDO`).
COR_ESCURA = (3, 58, 35)

#: Ficheiros sem fundo aceites, vindos da pasta do projeto.
NOMES_ENTRADA = (
    "desporto_escolar-removebg-preview.png",
    "desporto_escolar_sem_fundo.png",
)


# ---------------------------------------------------------------------------
# Instalação
# ---------------------------------------------------------------------------
def instalar(pasta_assets: Path, nome: str = "desporto_escolar.png") -> None:
    """Garante que `pasta_assets/nome` é o logótipo com fundo transparente."""
    destino = pasta_assets / nome
    gerado = pasta_assets / NOME_GERADO
    emblema = pasta_assets / NOME_EMBLEMA

    if gerado.is_file():
        _copiar(gerado, destino)
        if emblema.is_file():
            return
    else:
        origem = _entrada(pasta_assets, destino)
        if origem is not None:
            _copiar(origem, destino)

    if not destino.is_file():
        return

    dados = _abrir(destino)
    if dados is None:
        return
    pixeis, largura, altura = dados

    if not _tem_alfa(pixeis) and _limpar_fundo(pixeis, largura, altura):
        _gravar(destino, pixeis, largura, altura)
    if not gerado.is_file():
        _copiar(destino, gerado)

    regiao = _regiao_emblema(pixeis, largura, altura)
    if regiao is not None:
        _gravar_regiao(emblema, pixeis, largura, altura, regiao)


def instalar_escuro(pasta_assets: Path, origem_nome: str = "desporto_escolar.png",
                    destino_nome: str = NOME_ESCURO,
                    cor: tuple[int, int, int] = COR_ESCURA) -> None:
    """Gera o logótipo numa cor sólida (mantendo a transparência).

    O ficheiro original é branco, feito para fundos escuros; esta versão é
    usada sobre cabeçalhos e cartões claros.
    """
    origem = pasta_assets / origem_nome
    destino = pasta_assets / destino_nome
    if not origem.is_file():
        return
    try:
        if destino.is_file() and destino.stat().st_mtime >= origem.stat().st_mtime:
            return
    except OSError:
        pass

    dados = _abrir(origem)
    if dados is None:
        return
    pixeis, largura, altura = dados
    for i in range(0, len(pixeis), 4):
        if pixeis[i + 3]:
            pixeis[i], pixeis[i + 1], pixeis[i + 2] = cor
    _gravar(destino, pixeis, largura, altura)


def _entrada(pasta_assets: Path, destino: Path) -> Path | None:
    """Procura o logótipo sem fundo na pasta do projeto."""
    for pasta in (pasta_assets, *pasta_assets.parents[:4]):
        for nome in NOMES_ENTRADA:
            origem = pasta / nome
            if origem.is_file() and origem.resolve() != destino.resolve():
                return origem
    return None


def _copiar(origem: Path, destino: Path) -> None:
    try:
        if origem.resolve() != destino.resolve():
            shutil.copyfile(origem, destino)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Conversão
# ---------------------------------------------------------------------------
def _abrir(caminho: Path) -> tuple[bytearray, int, int] | None:
    """Lê o PNG e devolve os pixéis RGBA, a largura e a altura."""
    try:
        info, linhas = _descomprimir(caminho.read_bytes())
        return _para_rgba(linhas, info), info["largura"], info["altura"]
    except (OSError, ValueError, struct.error, zlib.error):
        return None


def _tem_alfa(pixeis: bytearray) -> bool:
    return any(pixeis[i] < 250 for i in range(3, len(pixeis), 4))


def _limpar_fundo(pixeis: bytearray, largura: int, altura: int) -> int:
    """Torna transparentes os pixéis claros ligados às margens; devolve quantos."""
    total = largura * altura
    vistos = bytearray(total)
    fila: deque[int] = deque()

    for x in range(largura):
        fila.append(x)
        fila.append((altura - 1) * largura + x)
    for y in range(altura):
        fila.append(y * largura)
        fila.append(y * largura + largura - 1)

    removidos = 0
    while fila:
        indice = fila.pop()
        if vistos[indice]:
            continue
        vistos[indice] = 1

        pos = indice * 4
        alfa = pixeis[pos + 3]
        if alfa != 0 and not (
            pixeis[pos] >= LIMIAR_CLARO
            and pixeis[pos + 1] >= LIMIAR_CLARO
            and pixeis[pos + 2] >= LIMIAR_CLARO
        ):
            continue
        if alfa != 0:
            pixeis[pos + 3] = 0
            removidos += 1

        linha, coluna = divmod(indice, largura)
        if coluna > 0:
            fila.append(indice - 1)
        if coluna + 1 < largura:
            fila.append(indice + 1)
        if linha > 0:
            fila.append(indice - largura)
        if linha + 1 < altura:
            fila.append(indice + largura)

    return removidos


def _regiao_emblema(pixeis: bytearray, largura: int, altura: int
                    ) -> tuple[int, int, int, int] | None:
    """Encontra a primeira banda de pixéis visíveis (o emblema do logótipo)."""
    ocupadas = [
        any(pixeis[y * largura * 4 + x * 4 + 3] > 8 for x in range(largura))
        for y in range(altura)
    ]
    inicio = next((y for y, valor in enumerate(ocupadas) if valor), None)
    if inicio is None:
        return None

    fim = inicio
    for y in range(inicio, altura):
        if ocupadas[y]:
            fim = y
        elif fim > inicio + 4:
            break

    topo = max(0, inicio - 2)
    base = min(altura, fim + 3)
    esquerda, direita = largura, 0
    for y in range(topo, base):
        linha = y * largura * 4
        for x in range(largura):
            if pixeis[linha + x * 4 + 3] > 8:
                esquerda = min(esquerda, x)
                direita = max(direita, x)
    if direita <= esquerda:
        return None
    return topo, base, max(0, esquerda - 2), min(largura, direita + 3)


def _gravar_regiao(caminho: Path, pixeis: bytearray, largura: int, altura: int,
                   regiao: tuple[int, int, int, int]) -> bool:
    topo, base, esquerda, direita = regiao
    largura_regiao = direita - esquerda
    altura_regiao = base - topo
    if largura_regiao <= 0 or altura_regiao <= 0:
        return False

    recorte = bytearray()
    for y in range(topo, base):
        inicio = (y * largura + esquerda) * 4
        recorte += pixeis[inicio:inicio + largura_regiao * 4]
    return _gravar(caminho, recorte, largura_regiao, altura_regiao)


# ---------------------------------------------------------------------------
# Leitura e escrita de PNG
# ---------------------------------------------------------------------------
def _blocos(dados: bytes):
    posicao = 8
    while posicao + 8 <= len(dados):
        (tamanho,) = struct.unpack(">I", dados[posicao:posicao + 4])
        tipo = dados[posicao + 4:posicao + 8]
        corpo = dados[posicao + 8:posicao + 8 + tamanho]
        posicao += 12 + tamanho
        yield tipo, corpo
        if tipo == b"IEND":
            return


def _descomprimir(dados: bytes) -> tuple[dict, list[bytearray]]:
    if not dados.startswith(ASSINATURA):
        raise ValueError("não é um ficheiro PNG")

    info: dict = {"largura": 0, "altura": 0, "tipo": 0, "paleta": b"", "alfa": b""}
    idat = bytearray()
    for tipo, corpo in _blocos(dados):
        if tipo == b"IHDR":
            (largura, altura, profundidade, tipo_cor, _compressao, _filtro,
             entrelacado) = struct.unpack(">IIBBBBB", corpo)
            if entrelacado:
                raise ValueError("PNG entrelaçado não é suportado")
            if profundidade != 8:
                raise ValueError("apenas PNG de 8 bits por canal")
            info.update(largura=largura, altura=altura, tipo=tipo_cor)
        elif tipo == b"PLTE":
            info["paleta"] = corpo
        elif tipo == b"tRNS":
            info["alfa"] = corpo
        elif tipo == b"IDAT":
            idat += corpo
        elif tipo == b"IEND":
            break

    canais = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(info["tipo"])
    if not canais:
        raise ValueError("formato de cor PNG não suportado")

    bruto = zlib.decompress(bytes(idat))
    return info, _desfiltragem(bruto, info["largura"], info["altura"], canais)


def _desfiltragem(bruto: bytes, largura: int, altura: int,
                  canais: int) -> list[bytearray]:
    passo = largura * canais
    linhas: list[bytearray] = []
    anterior = bytearray(passo)
    posicao = 0

    for _ in range(altura):
        if posicao + 1 + passo > len(bruto):
            raise ValueError("PNG incompleto")
        filtro = bruto[posicao]
        linha = bytearray(bruto[posicao + 1:posicao + 1 + passo])
        posicao += 1 + passo

        if filtro == 1:
            for i in range(canais, passo):
                linha[i] = (linha[i] + linha[i - canais]) & 0xFF
        elif filtro == 2:
            for i in range(passo):
                linha[i] = (linha[i] + anterior[i]) & 0xFF
        elif filtro == 3:
            for i in range(passo):
                esquerda = linha[i - canais] if i >= canais else 0
                linha[i] = (linha[i] + ((esquerda + anterior[i]) >> 1)) & 0xFF
        elif filtro == 4:
            for i in range(passo):
                a = linha[i - canais] if i >= canais else 0
                b = anterior[i]
                c = anterior[i - canais] if i >= canais else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                previsor = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                linha[i] = (linha[i] + previsor) & 0xFF
        elif filtro != 0:
            raise ValueError(f"filtro PNG desconhecido: {filtro}")

        linhas.append(linha)
        anterior = linha

    return linhas


def _para_rgba(linhas: list[bytearray], info: dict) -> bytearray:
    tipo = info["tipo"]
    pixeis = bytearray(info["largura"] * info["altura"] * 4)
    destino = 0

    if tipo == 6:
        for linha in linhas:
            pixeis[destino:destino + len(linha)] = linha
            destino += len(linha)
        return pixeis

    if tipo == 2:
        for linha in linhas:
            for i in range(0, len(linha), 3):
                pixeis[destino:destino + 3] = linha[i:i + 3]
                pixeis[destino + 3] = 255
                destino += 4
        return pixeis

    if tipo == 3:
        paleta = info["paleta"]
        alfa = info["alfa"]
        for linha in linhas:
            for indice in linha:
                base = indice * 3
                pixeis[destino:destino + 3] = paleta[base:base + 3]
                pixeis[destino + 3] = alfa[indice] if indice < len(alfa) else 255
                destino += 4
        return pixeis

    raise ValueError("formato de cor PNG não suportado")


def _gravar(caminho: Path, pixeis: bytearray, largura: int, altura: int) -> bool:
    passo = largura * 4
    bruto = bytearray()
    for linha in range(altura):
        bruto.append(0)
        bruto += pixeis[linha * passo:(linha + 1) * passo]

    def bloco(tipo: bytes, corpo: bytes) -> bytes:
        return (struct.pack(">I", len(corpo)) + tipo + corpo
                + struct.pack(">I", binascii.crc32(tipo + corpo) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", largura, altura, 8, 6, 0, 0, 0)
    dados = (ASSINATURA
             + bloco(b"IHDR", ihdr)
             + bloco(b"IDAT", zlib.compress(bytes(bruto), 9))
             + bloco(b"IEND", b""))

    temporario = caminho.with_name(caminho.name + ".tmp")
    try:
        temporario.write_bytes(dados)
        temporario.replace(caminho)
    except OSError:
        try:
            temporario.unlink()
        except OSError:
            pass
        return False
    return True
