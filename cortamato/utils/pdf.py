

from __future__ import annotations

from pathlib import Path

LARGURA = 595.0   # A4 em pontos
ALTURA = 842.0
MARGEM = 45.0


def _escapar(texto: str) -> str:
    """Converte o texto para a sintaxe literal de strings do PDF (WinAnsi)."""
    partes: list[str] = []
    for byte in str(texto).encode("cp1252", "replace"):
        if byte in (0x28, 0x29, 0x5C):          # ( ) \
            partes.append("\\" + chr(byte))
        elif byte < 32 or byte > 126:
            partes.append("\\%03o" % byte)
        else:
            partes.append(chr(byte))
    return "".join(partes)


def _truncar(texto: str, largura: float, tamanho: float = 8.0) -> str:
    limite = max(4, int(largura / (tamanho * 0.5)))
    valor = str(texto)
    if len(valor) <= limite:
        return valor
    return valor[: limite - 3] + "..."


class PDFSimples:
    """Construtor de documentos PDF com quebras de página automáticas."""

    def __init__(self, titulo: str = "Relatório", rodape: str = "") -> None:
        self.titulo = titulo
        self.rodape = rodape
        self.paginas: list[list[tuple[float, float, int, bool, str]]] = [[]]
        self._y = ALTURA - MARGEM

    # ------------------------------------------------------------------
    # Conteúdo
    # ------------------------------------------------------------------
    def _nova_pagina(self) -> None:
        self.paginas.append([])
        self._y = ALTURA - MARGEM

    def _garantir_espaco(self, altura: float) -> None:
        if self._y - altura < MARGEM:
            self._nova_pagina()

    def _escrever(self, x: float, texto: str, tamanho: int, negrito: bool) -> None:
        self.paginas[-1].append((x, self._y, tamanho, negrito, texto))

    def texto(self, texto: str, tamanho: int = 10, negrito: bool = False,
              espaco_depois: float | None = None) -> None:
        altura = espaco_depois if espaco_depois is not None else tamanho * 1.5
        self._garantir_espaco(altura)
        self._escrever(MARGEM, texto, tamanho, negrito)
        self._y -= altura

    def titulo_principal(self, texto: str) -> None:
        self.texto(texto, 16, True, 26)

    def subtitulo(self, texto: str) -> None:
        self.texto(texto, 12, True, 20)

    def espaco(self, pontos: float = 10) -> None:
        self._garantir_espaco(pontos)
        self._y -= pontos

    def tabela(self, cabecalho: list[str], registos: list[list], larguras: list[float]) -> None:
        util = LARGURA - 2 * MARGEM
        posicoes: list[float] = []
        posicao = MARGEM
        for fracao in larguras:
            posicoes.append(posicao)
            posicao += util * fracao
        altura_linha = 13.0

        if cabecalho:
            self._garantir_espaco(altura_linha)
            for x, celula, fracao in zip(posicoes, cabecalho, larguras):
                self._escrever(x, _truncar(celula, util * fracao), 8, True)
            self._y -= altura_linha
            self._garantir_espaco(altura_linha)

        if not registos:
            self._escrever(MARGEM, "(sem registos)", 8, False)
            self._y -= altura_linha
            return

        for registo in registos:
            self._garantir_espaco(altura_linha)
            for x, celula, fracao in zip(posicoes, registo, larguras):
                self._escrever(x, _truncar(celula, util * fracao), 8, False)
            self._y -= altura_linha

    # ------------------------------------------------------------------
    # Serialização
    # ------------------------------------------------------------------
    def _fluxos(self) -> list[bytes]:
        fluxos: list[bytes] = []
        for pagina in self.paginas:
            operacoes = ["BT"]
            for x, y, tamanho, negrito, texto in pagina:
                fonte = "F2" if negrito else "F1"
                operacoes.append(
                    "/%s %d Tf 1 0 0 1 %.2f %.2f Tm (%s) Tj"
                    % (fonte, tamanho, x, y, _escapar(texto))
                )
            operacoes.append("ET")
            fluxos.append("\n".join(operacoes).encode("cp1252", "replace"))
        return fluxos

    def guardar(self, caminho: str | Path) -> Path:
        destino = Path(caminho)
        destino.parent.mkdir(parents=True, exist_ok=True)
        fluxos = self._fluxos()
        total_paginas = len(fluxos)
        total_objetos = 4 + 2 * total_paginas

        saida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        posicoes: dict[int, int] = {}

        def adicionar(numero: int, corpo: bytes) -> None:
            posicoes[numero] = len(saida)
            saida.extend(b"%d 0 obj\n" % numero)
            saida.extend(corpo)
            saida.extend(b"\nendobj\n")

        adicionar(1, b"<< /Type /Catalog /Pages 2 0 R >>")
        filhos = " ".join("%d 0 R" % (5 + 2 * indice) for indice in range(total_paginas))
        adicionar(
            2,
            ("<< /Type /Pages /Kids [%s] /Count %d >>" % (filhos, total_paginas)).encode("latin-1"),
        )
        adicionar(
            3,
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        )
        adicionar(
            4,
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        )

        for indice, fluxo in enumerate(fluxos):
            numero_pagina = 5 + 2 * indice
            numero_conteudo = 6 + 2 * indice
            adicionar(
                numero_pagina,
                (
                    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.0f %.0f] "
                    "/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents %d 0 R >>"
                    % (LARGURA, ALTURA, numero_conteudo)
                ).encode("latin-1"),
            )
            adicionar(
                numero_conteudo,
                b"<< /Length %d >>\nstream\n" % len(fluxo) + fluxo + b"\nendstream",
            )

        inicio_xref = len(saida)
        total_xref = total_objetos + 1
        saida.extend(b"xref\n0 %d\n" % total_xref)
        saida.extend(b"0000000000 65535 f \n")
        for numero in range(1, total_objetos + 1):
            saida.extend(b"%010d 00000 n \n" % posicoes.get(numero, 0))
        saida.extend(
            b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (total_xref, inicio_xref)
        )

        destino.write_bytes(bytes(saida))
        return destino
