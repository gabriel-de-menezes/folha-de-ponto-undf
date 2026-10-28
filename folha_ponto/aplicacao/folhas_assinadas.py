"""Caso de uso: importar folhas assinadas (PDF), separar uma folha por página, identificar o servidor e o mês
de cada uma e conferir antes de arquivar."""
import os
from collections import Counter

from ..dominio.competencia import normalizar_competencia, rotulo_competencia
from ..dominio.entidades import FolhaAssinada, ItemOperacao, MetodoIdentificacao, TipoOperacao
from ..dominio.regras import ErroDominio, identificar_servidor, resolver_conflitos
from .portas import sem_progresso

LIMITE_ARQUIVOS = 200
EXTENSOES = (".pdf",)
VARIOS_MESES = "VÁRIOS MESES"


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
    def validar_arquivos(self, caminhos):
        """Só PDFs de verdade (extensão e cabeçalho). Levanta ErroDominio listando os recusados."""
        if len(caminhos) > LIMITE_ARQUIVOS:
            raise ErroDominio(f"Selecione no máximo {LIMITE_ARQUIVOS} arquivos por vez (foram {len(caminhos)}).")
        invalidos = [os.path.basename(c) for c in caminhos if not self.leitor.e_pdf(c)]
        if invalidos:
            raise ErroDominio("Apenas arquivos PDF (.pdf) são aceitos. Arquivo(s) recusado(s): "
                              + ", ".join(invalidos[:5]) + ("…" if len(invalidos) > 5 else "") + ".")

    def identificar(self, caminho, pagina, servidores):
        """1º lê o texto da própria página (matrícula/nome); se não identificar, usa OCR — tentando outras
        variações da imagem enquanto faltar o servidor ou o mês. Retorna (servidor_id, competência lida, método, texto)."""
        texto = self.leitor.texto_pagina(caminho, pagina)
        servidor_id, competencia = identificar_servidor(texto, servidores) if texto.strip() else (None, "")
        if servidor_id and competencia:
            return servidor_id, competencia, MetodoIdentificacao.TEXTO, texto
        metodo = MetodoIdentificacao.TEXTO if servidor_id else MetodoIdentificacao.NAO_IDENTIFICADO
        if self.leitor.ocr_disponivel():
            try:
                for texto_ocr in self.leitor.leituras_ocr(caminho, pagina):
                    if not texto_ocr.strip():
                        continue
                    id_ocr, comp_ocr = identificar_servidor(texto_ocr, servidores)
                    if not servidor_id and id_ocr:
                        servidor_id, metodo = id_ocr, MetodoIdentificacao.OCR
                    competencia = competencia or comp_ocr
                    texto = texto_ocr
                    if servidor_id and competencia:
                        break
            except Exception as e:
                texto = texto or f"Erro OCR: {e}"
        return servidor_id, competencia, metodo, texto

    def processar_arquivo(self, caminho, servidores, competencia_padrao=""):
        """Separa o PDF em folhas (uma por página), guarda cada página na área de importação e registra.
        Se a mesma página já foi importada antes, reaproveita o registro existente."""
        original = os.path.basename(caminho)
        resultado = []
        for pagina in range(1, self.leitor.contar_paginas(caminho) + 1):
            hash_pagina = self.leitor.assinatura_pagina(caminho, pagina)
            existente = self.folhas.digitalizada_por_hash(hash_pagina)
            if existente and self.armazenamento.existe(existente["caminho_arquivo"]):
                lida = existente["competencia"] or ""
                resultado.append(FolhaAssinada(
                    doc_id=existente["id"], caminho=existente["caminho_arquivo"], hash=hash_pagina, original=original,
                    pagina=pagina, servidor_id=existente["servidor_id"], competencia_lida=lida, competencia=lida,
                    metodo=existente["metodo_identificacao"] or MetodoIdentificacao.TEXTO, duplicado=True,
                    observacao="Folha já importada anteriormente"))
                continue
            servidor_id, lida, metodo, texto = self.identificar(caminho, pagina, servidores)
            lida = normalizar_competencia(lida) if lida else ""
            destino = os.path.join(self.armazenamento.pasta_importacao(), f"{hash_pagina[:16]}.pdf")
            self.leitor.salvar_pagina(caminho, pagina, destino)
            doc_id = self.folhas.registrar_digitalizada(
                destino, servidor_id, lida, "Processado" if servidor_id else "Pendente Validação",
                texto[:2000], hash_pagina, metodo)
            folha = FolhaAssinada(doc_id=doc_id, caminho=destino, hash=hash_pagina, original=original, pagina=pagina,
                                  servidor_id=servidor_id, metodo=metodo, competencia_lida=lida, competencia=lida)
            if not lida:
                folha.competencia = competencia_padrao
                folha.observacao = "Mês não identificado na folha — informe na conferência"
            resultado.append(folha)
        return resultado

    def importar_lote(self, caminhos, progresso=sem_progresso):
        """Lê os PDFs (uma folha por página) e abre a operação de auditoria. Retorna (op_id, folhas)."""
        self.validar_arquivos(caminhos)
        servidores = self.servidores.listar()
        if not servidores:
            raise ErroDominio("Nenhum servidor cadastrado. Cadastre ou importe os servidores primeiro.")
        op_id = self.auditoria.iniciar(TipoOperacao.ASSINADAS, VARIOS_MESES, f"{len(caminhos)} arquivo(s) importado(s)")
        folhas, vistos, ilegiveis = [], set(), []
        for n, caminho in enumerate(caminhos):
            progresso(n, len(caminhos), f"Lendo {os.path.basename(caminho)}")
            try:
                lidas = self.processar_arquivo(caminho, servidores)
            except Exception as e:
                self.auditoria.evento(op_id, f"Erro ao ler {os.path.basename(caminho)}: {e}")
                ilegiveis.append(os.path.basename(caminho))
                continue
            for folha in lidas:
                if folha.doc_id not in vistos:
                    vistos.add(folha.doc_id)
                    folhas.append(folha)
        if not folhas:
            self.auditoria.finalizar(op_id, "Falha na leitura", [])
            motivo = (f"Não foi possível ler: {', '.join(ilegiveis[:5])}. O PDF pode estar corrompido ou protegido "
                      "por senha." if ilegiveis else "Os arquivos selecionados não têm páginas.")
            raise ErroDominio(motivo)
        resolver_conflitos(folhas)
        self._marcar_substituicoes(folhas)
        self._atualizar_competencia_operacao(op_id, folhas)
        por_texto = sum(1 for f in folhas if f.servidor_id and f.metodo == MetodoIdentificacao.TEXTO)
        por_ocr = sum(1 for f in folhas if f.servidor_id and f.metodo == MetodoIdentificacao.OCR)
        sem = sum(1 for f in folhas if not f.servidor_id)
        sem_mes = sum(1 for f in folhas if not f.competencia)
        self.auditoria.atualizar(op_id, origem=f"{len(caminhos)} arquivo(s) importado(s)",
                                 origem_hash=folhas[0].hash if len(folhas) == 1 else "")
        self.auditoria.evento(
            op_id, f"{len(caminhos)} arquivo(s) / {len(folhas)} folha(s) lida(s): {por_texto} identificada(s) pelo "
                   f"texto do PDF, {por_ocr} por OCR, {sem} sem servidor"
                   + (f", {sem_mes} sem mês identificado." if sem_mes else "."))
        self.auditoria.salvar_itens(op_id, self.itens_auditoria(self.itens(folhas), folhas))
        return op_id, folhas

    def _marcar_substituicoes(self, folhas):
        """Avisa quando a folha vai substituir uma já arquivada (a antiga vira _OLD_ ao concluir)."""
        for f in folhas:
            f.substitui = ""
            if not (f.servidor_id and f.competencia) or f.duplicado:
                continue
            servidor = self.servidores.obter(f.servidor_id)
            existente = self.armazenamento.caminho_folha_arquivada(servidor.nome, f.competencia)
            if self.armazenamento.existe(existente) and os.path.abspath(existente) != os.path.abspath(f.caminho):
                f.substitui = existente
                if not f.observacao or f.observacao.startswith("Substitui"):
                    f.observacao = f"Substitui a folha já arquivada de {rotulo_competencia(f.competencia)} (backup automático)"
            elif f.observacao.startswith("Substitui"):
                f.observacao = ""

    def _atualizar_competencia_operacao(self, op_id, folhas):
        meses = {f.competencia for f in folhas if f.competencia}
        valor = next(iter(meses)) if len(meses) == 1 else VARIOS_MESES
        self.auditoria.atualizar(op_id, competencia=valor)
        return valor

    @staticmethod
    def competencia_predominante(folhas):
        contagem = Counter(f.competencia for f in folhas if f.competencia)
        return contagem.most_common(1)[0][0] if contagem else ""

    def servidores_sem_folha(self, folhas, competencia):
        """Servidores sem folha assinada do mês: nem neste lote nem arquivada em importações anteriores."""
        com = {f.servidor_id for f in folhas if f.servidor_id and f.competencia == competencia}
        com |= self.folhas.servidores_com_folha_assinada(competencia)
        return [s for s in self.servidores.listar() if s.id not in com]

    # ---------- conferência ----------
    @staticmethod
    def folha_do_servidor(folhas, servidor_id, competencia=None):
        """Folha do servidor no lote; se `competencia` for informada, a daquele mês."""
        return next((f for f in folhas if f.servidor_id == servidor_id
                     and (competencia is None or f.competencia == competencia)), None)

    def atribuir(self, op_id, folhas, folha, servidor_id):
        """Atribui a folha a um servidor. Se ele já tinha outra folha do mesmo mês no lote, a anterior fica sem dono."""
        servidor = self.servidores.obter(servidor_id)
        if folha.servidor_id == servidor_id:
            return
        anterior_dono = self.servidores.obter(folha.servidor_id) if folha.servidor_id else None
        atual = self.folha_do_servidor(folhas, servidor_id, folha.competencia) if folha.competencia else None
        if atual and atual is not folha:
            atual.servidor_id, atual.observacao, atual.substitui = None, "Substituída por outra folha", ""
        folha.servidor_id, folha.metodo, folha.observacao = servidor_id, MetodoIdentificacao.MANUAL, ""
        self._marcar_substituicoes(folhas)
        self.auditoria.evento(op_id, f"Conferência: folha “{folha.original}” (pág. {folha.pagina}) atribuída "
                                     f"manualmente a {servidor.nome} (matrícula {servidor.matricula})"
                              + (f"; antes estava com {anterior_dono.nome}." if anterior_dono else "."))

    def definir_competencia(self, op_id, folhas, folha, competencia):
        """Informa (ou corrige) o mês de uma folha na conferência."""
        competencia = normalizar_competencia(competencia)
        antes = folha.competencia
        if competencia == antes:
            return
        folha.competencia = competencia
        if folha.servidor_id:
            outra = next((f for f in folhas if f is not folha and f.servidor_id == folha.servidor_id
                          and f.competencia == competencia), None)
            if outra:
                folha.servidor_id, folha.observacao = None, (f"Duplicada: já existe folha deste servidor em "
                                                             f"{rotulo_competencia(competencia)} no lote")
        if folha.observacao.startswith("Mês não identificado"):
            folha.observacao = ""
        self._marcar_substituicoes(folhas)
        self._atualizar_competencia_operacao(op_id, folhas)
        self.auditoria.evento(op_id, f"Conferência: mês da folha “{folha.original}” (pág. {folha.pagina}) definido "
                                     f"manualmente como {rotulo_competencia(competencia)}"
                              + (f" (antes: {rotulo_competencia(antes)})." if antes else "."))

    def substituir(self, op_id, folhas, servidor_id, caminho, competencia=""):
        """Troca (ou define) a folha de um servidor por outro PDF escolhido pelo usuário.
        Se o PDF tiver várias páginas, a 1ª é do servidor e as demais entram no lote normalmente."""
        self.validar_arquivos([caminho])
        servidor = self.servidores.obter(servidor_id)
        novas = self.processar_arquivo(caminho, self.servidores.listar(), competencia)
        if not novas:
            raise ErroDominio("O arquivo não tem páginas.")
        principal = novas[0]
        principal_existente = next((f for f in folhas if f.doc_id == principal.doc_id), None)
        principal = principal_existente or principal
        if not principal.competencia:
            principal.competencia = competencia
        atual = self.folha_do_servidor(folhas, servidor_id, principal.competencia)
        if atual and atual is not principal:
            atual.servidor_id, atual.observacao, atual.substitui = None, f"Substituída na folha de {servidor.nome}", ""
        principal.servidor_id, principal.metodo, principal.observacao = servidor_id, MetodoIdentificacao.MANUAL, ""
        if not principal_existente:
            folhas.append(principal)
        for extra in novas[1:]:
            if not any(f.doc_id == extra.doc_id for f in folhas):
                folhas.append(extra)
        resolver_conflitos([f for f in folhas if f is not principal])
        self._marcar_substituicoes(folhas)
        self._atualizar_competencia_operacao(op_id, folhas)
        self.auditoria.evento(op_id, f"Conferência: folha de {servidor.nome} (matrícula {servidor.matricula}) substituída "
                                     f"manualmente por “{os.path.basename(caminho)}”"
                              + (f" (antes: “{atual.original}”)." if atual and atual is not principal else "."))
        return principal

    def itens(self, folhas, anteriores=()):
        """Um item de envio por folha atribuída, mantendo a seleção feita anteriormente."""
        selecao = {(i.servidor_id, i.competencia): i.selecionado for i in anteriores}
        itens = []
        for f in folhas:
            servidor = self.servidores.obter(f.servidor_id) if f.servidor_id else None
            if servidor:
                itens.append(ItemOperacao.de_servidor(
                    servidor, competencia=f.competencia, arquivo=f.caminho, arquivo_hash=f.hash,
                    identificacao=f.metodo, observacao=f.observacao,
                    selecionado=selecao.get((servidor.id, f.competencia), True)))
        return itens

    @staticmethod
    def itens_auditoria(itens, folhas):
        """Itens de envio + folhas que ficaram sem servidor (também aparecem no relatório)."""
        extras = [ItemOperacao(servidor_id=None, nome="(folha sem servidor atribuído)", competencia=f.competencia,
                               arquivo=f.caminho, arquivo_hash=f.hash, identificacao=f.metodo,
                               observacao=f.observacao or f"{f.original} (pág. {f.pagina})",
                               selecionado=False) for f in folhas if not f.servidor_id]
        return list(itens) + extras

    def concluir_conferencia(self, op_id, folhas, anteriores=()):
        """Arquiva cada folha atribuída em Folhas_AAAA-MM/Nome-AAAA-MM.pdf (a versão anterior, se houver, vira
        _OLD_ com data e hora) e devolve os itens prontos para envio."""
        atribuidas = [f for f in folhas if f.servidor_id]
        if not atribuidas:
            raise ErroDominio("Nenhuma folha está atribuída a um servidor.")
        sem_mes = [f for f in atribuidas if not f.competencia]
        if sem_mes:
            raise ErroDominio(f"{len(sem_mes)} folha(s) atribuída(s) estão sem mês de referência. "
                              "Informe o mês de cada uma na conferência.")
        for f in folhas:
            if not f.servidor_id:  # substituída ou sem dono: não fica vinculada a quem a leitura sugeriu
                self.folhas.vincular_digitalizada(f.doc_id, None, f.competencia, "Pendente Validação")
                continue
            servidor = self.servidores.obter(f.servidor_id)
            origem = f.caminho
            destino, backup = self.armazenamento.arquivar_folha(origem, servidor.nome, f.competencia)
            if backup:
                self.folhas.substituir_digitalizada(destino, backup)
                self.auditoria.evento(op_id, f"Versão anterior de {servidor.nome} ({rotulo_competencia(f.competencia)}) "
                                             f"preservada como {os.path.basename(backup)}.")
            self.folhas.vincular_digitalizada(f.doc_id, f.servidor_id, f.competencia, "Validado", destino)
            f.caminho, f.substitui = destino, ""
            if origem != destino:
                self.armazenamento.descartar_importacao(origem)
        itens = self.itens(folhas, anteriores)
        sem = len(folhas) - len(atribuidas)
        self._atualizar_competencia_operacao(op_id, folhas)
        self.auditoria.evento(op_id, f"Conferência concluída: {len(itens)} folha(s) atribuída(s) e arquivada(s)"
                              + (f"; {sem} sem servidor." if sem else "."))
        self.auditoria.salvar_itens(op_id, self.itens_auditoria(itens, folhas))
        return itens
