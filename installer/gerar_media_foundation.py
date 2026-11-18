"""
Gera DLLs substitutas do Media Foundation (mfplat.dll, mfplay.dll, mfreadwrite.dll) para as edições "N" do
Windows, que vêm sem os recursos de mídia.

O LibreOffice (mergedlo.dll) importa 6 funções dessas DLLs só para tocar áudio e vídeo dentro de documentos.
Sem elas o Windows nem carrega o LibreOffice, e a conversão das folhas em PDF falha. As substitutas exportam
as mesmas funções, que só respondem E_NOTIMPL ("não implementado"): o LibreOffice abre e converte, apenas sem
reprodução de mídia, que o DIGEP não usa.

O instalador só as copia quando o Windows não tem o Media Foundation de verdade (edição "N"); nos demais
o LibreOffice continua usando o do Windows.

As DLLs são montadas byte a byte aqui (PE32+ x64 mínimo, sem importações), sem precisar de compilador.
Uso:  python installer/gerar_media_foundation.py [pasta_de_saida]   (padrão: installer/MediaFoundation)
"""
import os
import struct
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(AQUI, "MediaFoundation")

# Funções que o LibreOffice importa de cada DLL (conferido em mergedlo.dll do LibreOffice 26.2).
EXPORTACOES = {
    "mfplat.dll": ["MFCreateAttributes", "MFCreateMediaType", "MFShutdown", "MFStartup"],
    "mfplay.dll": ["MFPCreateMediaPlayer"],
    "mfreadwrite.dll": ["MFCreateSourceReaderFromURL"],
}
E_NOTIMPL = 0x80004001

ALINHAMENTO_SECAO = 0x1000
ALINHAMENTO_ARQUIVO = 0x200
RVA_SECAO = 0x1000
BASE_IMAGEM = 0x180000000

DLLMAIN = b"\xB8\x01\x00\x00\x00\xC3"                         # mov eax, 1 (TRUE) ; ret
STUB = b"\xB8" + struct.pack("<I", E_NOTIMPL) + b"\xC3"      # mov eax, E_NOTIMPL ; ret


def _alinhar(valor, alinhamento):
    return (valor + alinhamento - 1) // alinhamento * alinhamento


def montar_dll(nome, funcoes):
    """Bytes de uma DLL x64 que exporta `funcoes`, todas devolvendo E_NOTIMPL."""
    funcoes = sorted(funcoes)  # a tabela de nomes de exportação precisa estar em ordem
    corpo = bytearray(DLLMAIN)
    enderecos = []
    for _ in funcoes:
        corpo += b"\xCC" * (-len(corpo) % 16)  # cada função alinhada em 16 bytes (int3 entre elas)
        enderecos.append(RVA_SECAO + len(corpo))
        corpo += STUB

    # Diretório de exportação: cabeçalho (40 bytes), endereços, ponteiros de nomes, ordinais, nomes
    corpo += b"\x00" * (-len(corpo) % 16)
    rva_exportacao = RVA_SECAO + len(corpo)
    n = len(funcoes)
    rva_enderecos = rva_exportacao + 40
    rva_ponteiros = rva_enderecos + 4 * n
    rva_ordinais = rva_ponteiros + 4 * n
    rva_nome_dll = rva_ordinais + 2 * n
    textos = bytearray(nome.encode() + b"\x00")
    rva_nomes = []
    for funcao in funcoes:
        rva_nomes.append(rva_nome_dll + len(textos))
        textos += funcao.encode() + b"\x00"
    exportacao = struct.pack("<IIHHIIIIIII", 0, 0, 0, 0, rva_nome_dll, 1, n, n,
                             rva_enderecos, rva_ponteiros, rva_ordinais)
    exportacao += b"".join(struct.pack("<I", e) for e in enderecos)
    exportacao += b"".join(struct.pack("<I", r) for r in rva_nomes)
    exportacao += b"".join(struct.pack("<H", i) for i in range(n))
    exportacao += textos
    corpo += exportacao
    tamanho_exportacao = len(exportacao)

    # Realocações: um bloco vazio (só preenchimento). O código não tem endereços absolutos, mas com o
    # diretório presente o Windows pode carregar a DLL em qualquer endereço (ASLR).
    corpo += b"\x00" * (-len(corpo) % 4)
    rva_realocacao = RVA_SECAO + len(corpo)
    realocacao = struct.pack("<IIHH", RVA_SECAO, 12, 0, 0)  # cabeçalho + 2 entradas de preenchimento
    corpo += realocacao

    tamanho_virtual = len(corpo)
    tamanho_bruto = _alinhar(tamanho_virtual, ALINHAMENTO_ARQUIVO)
    corpo += b"\x00" * (tamanho_bruto - tamanho_virtual)
    tamanho_imagem = RVA_SECAO + _alinhar(tamanho_virtual, ALINHAMENTO_SECAO)

    dos = bytearray(64)
    dos[0:2] = b"MZ"
    struct.pack_into("<I", dos, 0x3C, 64)  # e_lfanew: cabeçalho PE logo depois

    coff = struct.pack("<HHIIIHH", 0x8664, 1, 0, 0, 0, 240,
                       0x0002 | 0x0020 | 0x2000)  # executável | endereços altos | DLL
    diretorios = [(0, 0)] * 16
    diretorios[0] = (rva_exportacao, tamanho_exportacao)
    diretorios[5] = (rva_realocacao, len(realocacao))
    opcional = struct.pack("<HBBIIIIIQIIHHHHHHIIIIHHQQQQII",
                           0x20B, 14, 0,                     # PE32+, versão do linker
                           tamanho_bruto, 0, 0,              # código, dados inicializados/não
                           RVA_SECAO, RVA_SECAO,             # ponto de entrada (DllMain), início do código
                           BASE_IMAGEM, ALINHAMENTO_SECAO, ALINHAMENTO_ARQUIVO,
                           6, 0, 0, 0, 6, 0,                 # versões de SO, imagem e subsistema
                           0, tamanho_imagem, ALINHAMENTO_ARQUIVO, 0,
                           2,                                # subsistema: Windows (GUI)
                           0x0020 | 0x0040 | 0x0100,         # ASLR alto | ASLR | DEP
                           0x100000, 0x1000, 0x100000, 0x1000, 0, 16)
    opcional += b"".join(struct.pack("<II", rva, tamanho) for rva, tamanho in diretorios)
    secao = struct.pack("<8sIIIIIIHHI", b".text", tamanho_virtual, RVA_SECAO, tamanho_bruto,
                        ALINHAMENTO_ARQUIVO, 0, 0, 0, 0,
                        0x00000020 | 0x00000040 | 0x20000000 | 0x40000000)  # código, dados, executar, ler

    cabecalhos = bytes(dos) + b"PE\x00\x00" + coff + opcional + secao
    assert len(cabecalhos) <= ALINHAMENTO_ARQUIVO
    return cabecalhos + b"\x00" * (ALINHAMENTO_ARQUIVO - len(cabecalhos)) + bytes(corpo)


def gerar(destino=DESTINO):
    os.makedirs(destino, exist_ok=True)
    caminhos = []
    for nome, funcoes in EXPORTACOES.items():
        caminho = os.path.join(destino, nome)
        with open(caminho, "wb") as arquivo:
            arquivo.write(montar_dll(nome, funcoes))
        caminhos.append(caminho)
    return caminhos


if __name__ == "__main__":
    for caminho in gerar(sys.argv[1] if len(sys.argv) > 1 else DESTINO):
        print(f"{caminho} ({os.path.getsize(caminho)} bytes)")
