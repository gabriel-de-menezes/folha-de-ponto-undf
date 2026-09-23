"""Caso de uso: importar folhas assinadas (PDF/imagem), identificar o dono de cada uma e conferir."""
import os

from ..dominio.competencia import normalizar_competencia, rotulo_competencia
from ..dominio.entidades import FolhaAssinada, ItemOperacao, MetodoIdentificacao, TipoOperacao
from ..dominio.regras import ErroDominio, identificar_servidor, resolver_conflitos
from .portas import sem_progresso

LIMITE_ARQUIVOS = 200
EXTENSOES = (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")


class FolhasAssinadas:
    def __init__(self, repositorio_servidores, repositorio_folhas, leitor, armazenamento, auditoria):
        self.servidores = repositorio_servidores
        self.folhas = repositorio_folhas
        self.leitor = leitor
        self.armazenamento = armazenamento
        self.auditoria = auditoria

    def ocr_disponivel(self):
        return self.leitor.ocr_disponivel()

    # ---------- leitura ----------
    def identificar(self, caminho):
        """1º lê o texto do próprio PDF (matrícula/nome); se não identificar, usa OCR (sempre, para imagens).
        Retorna (servidor_id, competência lida, método, texto)."""
        servidores = self.servidores.listar()
        texto = self.leitor.texto_direto(caminho)
        servidor_id, competencia = identificar_servidor(texto, servidores) if texto.strip() else (None, "")
        if servidor_id:
            return servidor_id, competencia, MetodoIdentificacao.TEXTO, texto
        if self.leitor.ocr_disponivel():
            try:
                texto_ocr = self.leitor.texto_ocr(caminho)
            except Exception as e:
                texto_ocr, texto = "", texto or f"Erro OCR: {e}"
            if texto_ocr.strip():
                servidor_id, comp_ocr = identificar_servidor(texto_ocr, servidores)
                texto, competencia = texto_ocr, competencia or comp_ocr
                if servidor_id:
                    return servidor_id, competencia, MetodoIdentificacao.OCR, texto
        return None, competencia, MetodoIdentificacao.NAO_IDENTIFICADO, texto

    def processar(self, caminho, competencia):
        """Identifica, guarda uma cópia no arquivo do sistema e registra a folha. Se o mesmo conteúdo já
        foi importado antes, reaproveita o registro existente."""
        hash_arquivo = self.armazenamento.hash(caminho)
        existente = self.folhas.digitalizada_por_hash(hash_arquivo)
        if existente and self.armazenamento.existe(existente["caminho_arquivo"]):
            return FolhaAssinada(doc_id=existente["id"], caminho=existente["caminho_arquivo"], hash=hash_arquivo,
                                 original=os.path.basename(caminho), servidor_id=existente["servidor_id"],
                                 metodo=existente["metodo_identificacao"] or MetodoIdentificacao.TEXTO, duplicado=True)
        servidor_id, lida, metodo, texto = self.identificar(caminho)
        arquivado = self.armazenamento.arquivar_digitalizada(caminho, competencia)
        doc_id = self.folhas.registrar_digitalizada(
            arquivado, servidor_id, competencia, "Processado" if servidor_id else "Pendente Validação",
            texto[:2000], hash_arquivo, metodo)
        folha = FolhaAssinada(doc_id=doc_id, caminho=arquivado, hash=hash_arquivo, original=os.path.basename(caminho),
                              servidor_id=servidor_id, metodo=metodo, competencia_lida=lida)
        if lida and normalizar_competencia(lida) != competencia:
            folha.observacao = f"Folha indica {rotulo_competencia(lida)}"
        return folha

    def importar_lote(self, caminhos, competencia, progresso=sem_progresso):
        """Lê até LIMITE_ARQUIVOS arquivos e abre a operação de auditoria. Retorna (op_id, folhas)."""
        if len(caminhos) > LIMITE_ARQUIVOS:
            raise ErroDominio(f"Selecione no máximo {LIMITE_ARQUIVOS} arquivos por vez (foram {len(caminhos)}).")
        if not self.servidores.contar():
            raise ErroDominio("Nenhum servidor cadastrado. Defina a planilha base em Servidores primeiro.")
        op_id = self.auditoria.iniciar(TipoOperacao.ASSINADAS, competencia, f"{len(caminhos)} arquivo(s) importado(s)")
        folhas, vistos = [], set()
        for n, caminho in enumerate(caminhos):
            progresso(n, len(caminhos), f"Lendo {os.path.basename(caminho)}")
            try:
                folha = self.processar(caminho, competencia)
            except Exception as e:
                self.auditoria.evento(op_id, f"Erro ao ler {os.path.basename(caminho)}: {e}")
                continue
            if folha.doc_id not in vistos:
                vistos.add(folha.doc_id)
                folhas.append(folha)
        resolver_conflitos(folhas)
        por_texto = sum(1 for f in folhas if f.servidor_id and f.metodo == MetodoIdentificacao.TEXTO)
        por_ocr = sum(1 for f in folhas if f.servidor_id and f.metodo == MetodoIdentificacao.OCR)
        sem = sum(1 for f in folhas if not f.servidor_id)
        self.auditoria.atualizar(op_id, origem=f"{len(folhas)} arquivo(s) importado(s)",
                                 origem_hash=folhas[0].hash if len(folhas) == 1 else "")
        self.auditoria.evento(op_id, f"{len(folhas)} arquivo(s) lido(s): {por_texto} identificado(s) pelo texto do PDF, "
                                     f"{por_ocr} por OCR, {sem} sem identificação.")
        self.auditoria.salvar_itens(op_id, self.itens_auditoria(self.itens(folhas), folhas))
        return op_id, folhas

    # ---------- conferência ----------
    @staticmethod
    def folha_do_servidor(folhas, servidor_id):
        return next((f for f in folhas if f.servidor_id == servidor_id), None)

    def atribuir(self, op_id, folhas, folha, servidor_id):
        """Atribui a folha a um servidor. Se ele já tinha outra folha no lote, a anterior fica sem dono."""
        servidor = self.servidores.obter(servidor_id)
        if folha.servidor_id == servidor_id:
            if not folha.observacao.startswith("Folha indica"):
                folha.observacao = ""
            return
        anterior_dono = self.servidores.obter(folha.servidor_id) if folha.servidor_id else None
        atual = self.folha_do_servidor(folhas, servidor_id)
        if atual:
            atual.servidor_id, atual.observacao = None, "Substituída por outra folha"
        folha.servidor_id, folha.metodo, folha.observacao = servidor_id, MetodoIdentificacao.MANUAL, ""
        self.auditoria.evento(op_id, f"Conferência: arquivo “{folha.original}” atribuído manualmente a {servidor.nome} "
                                     f"(matrícula {servidor.matricula})"
                              + (f"; antes estava com {anterior_dono.nome}." if anterior_dono else "."))

    def substituir(self, op_id, folhas, servidor_id, caminho, competencia):
        """Troca (ou define) a folha de um servidor por outro arquivo escolhido pelo usuário."""
        servidor = self.servidores.obter(servidor_id)
        nova = self.processar(caminho, competencia)
        existente = next((f for f in folhas if f.doc_id == nova.doc_id), None)
        atual = self.folha_do_servidor(folhas, servidor_id)
        if atual and atual is not existente:
            atual.servidor_id, atual.observacao = None, f"Substituída na folha de {servidor.nome}"
        folha = existente or nova
        folha.servidor_id, folha.metodo, folha.observacao = servidor_id, MetodoIdentificacao.MANUAL, ""
        folha.original = os.path.basename(caminho)
        if not existente:
            folhas.append(folha)
        self.auditoria.evento(op_id, f"Conferência: folha de {servidor.nome} (matrícula {servidor.matricula}) substituída "
                                     f"manualmente por “{os.path.basename(caminho)}”"
                              + (f" (antes: “{atual.original}”)." if atual and atual is not existente else "."))
        return folha

    def itens(self, folhas, anteriores=()):
        """Um item de envio por folha atribuída, mantendo a seleção feita anteriormente."""
        selecao = {i.servidor_id: i.selecionado for i in anteriores}
        itens = []
        for f in folhas:
            servidor = self.servidores.obter(f.servidor_id) if f.servidor_id else None
            if servidor:
                itens.append(ItemOperacao.de_servidor(
                    servidor, arquivo=f.caminho, arquivo_hash=f.hash, identificacao=f.metodo, observacao=f.observacao,
                    selecionado=selecao.get(servidor.id, True)))
        return itens

    @staticmethod
    def itens_auditoria(itens, folhas):
        """Itens de envio + arquivos que ficaram sem servidor (também aparecem no relatório)."""
        extras = [ItemOperacao(servidor_id=None, nome="(arquivo sem servidor atribuído)", arquivo=f.caminho,
                               arquivo_hash=f.hash, identificacao=f.metodo, observacao=f.observacao or f.original,
                               selecionado=False) for f in folhas if not f.servidor_id]
        return list(itens) + extras

    def concluir_conferencia(self, op_id, folhas, competencia, anteriores=()):
        """Arquiva como validadas as folhas atribuídas e devolve os itens prontos para envio."""
        atribuidas = [f for f in folhas if f.servidor_id]
        if not atribuidas:
            raise ErroDominio("Nenhuma folha está atribuída a um servidor.")
        for f in folhas:
            if f.servidor_id:
                self.folhas.vincular_digitalizada(f.doc_id, f.servidor_id, competencia, "Validado")
            else:  # substituída ou sem dono: não pode continuar vinculada a quem a OCR/texto tinha sugerido
                self.folhas.vincular_digitalizada(f.doc_id, None, competencia, "Pendente Validação")
        itens = self.itens(folhas, anteriores)
        sem = len(folhas) - len(atribuidas)
        self.auditoria.evento(op_id, f"Conferência concluída: {len(itens)} folha(s) atribuída(s) e arquivada(s)"
                              + (f"; {sem} sem servidor." if sem else "."))
        self.auditoria.salvar_itens(op_id, self.itens_auditoria(itens, folhas))
        return itens
