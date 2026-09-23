"""Relatório de auditoria em PDF (HTML/CSS renderizado pelo PyMuPDF)."""
import html
import io
import os

import pymupdf

from .. import VERSAO
from ..dominio.competencia import rotulo_competencia
from ..dominio.entidades import StatusEnvio
from ..dominio.regras import data_br, mascarar_cpf

CSS = """
* { font-family: sans-serif; }
body { font-size: 8.5pt; color: #1E293B; }
h1 { font-size: 17pt; color: #1F4E8C; margin: 0 0 2pt 0; }
h2 { font-size: 11pt; color: #1F4E8C; margin: 14pt 0 5pt 0; }
p.sub { color: #64748B; margin: 0 0 8pt 0; font-size: 9pt; }
table { border-collapse: collapse; width: 100%; }
th { background-color: #1F4E8C; color: #FFFFFF; text-align: left; padding: 3pt 4pt; font-size: 7.5pt; }
td { border-bottom: 1px solid #E2E8F0; padding: 3pt 4pt; font-size: 7.5pt; vertical-align: top; }
td.k { color: #64748B; }
td.v { font-weight: bold; }
tr.par td { background-color: #F4F6FA; }
.ok { color: #2E9E6B; font-weight: bold; }
.erro { color: #C0392B; font-weight: bold; }
.aviso { color: #B7791F; font-weight: bold; }
td.num { font-size: 15pt; font-weight: bold; color: #1F4E8C; text-align: center; border: none; }
td.lbl { font-size: 7.5pt; color: #64748B; text-align: center; border: none; }
.hash { font-family: monospace; font-size: 6.5pt; color: #64748B; }
p.nota { color: #64748B; font-size: 7pt; margin-top: 10pt; }
"""


def _e(valor):
    return html.escape(str(valor if valor not in (None, "") else "—"))


def _classe_envio(status):
    return {StatusEnvio.ENVIADO: "ok", StatusEnvio.ERRO: "erro", StatusEnvio.NAO_SELECIONADO: "aviso"}.get(status, "")


def montar_html(op, itens, eventos, gerado_em):
    com_servidor = [i for i in itens if i.servidor_id]
    resumo = [(len(com_servidor), "servidores"), (sum(1 for i in com_servidor if i.arquivo), "com folha"),
              (sum(1 for i in itens if i.selecionado), "selecionados p/ envio"),
              (sum(1 for i in itens if i.envio_status == StatusEnvio.ENVIADO), "e-mails enviados"),
              (sum(1 for i in itens if i.envio_status == StatusEnvio.ERRO), "erros de envio")]
    sem_dono = len(itens) - len(com_servidor)
    if sem_dono:
        resumo.append((sem_dono, "arquivos sem servidor"))
    largura = f"{100 // len(resumo)}%"
    cards = ("<table><tr>" + "".join(f'<td class="num" style="width:{largura}">{n}</td>' for n, _ in resumo)
             + "</tr><tr>" + "".join(f'<td class="lbl" style="width:{largura}">{_e(t)}</td>' for _, t in resumo)
             + "</tr></table>")

    dados = [
        ("Operação", op.codigo), ("Tipo", op.descricao_tipo),
        ("Competência (mês de referência)", rotulo_competencia(op.competencia)), ("Situação", op.status),
        ("Início", data_br(op.iniciado_em)), ("Conclusão", data_br(op.concluido_em)),
        ("Usuário (Windows)", op.usuario), ("Computador", op.computador),
        ("Origem dos dados", op.origem), ("SHA-256 da origem", op.origem_hash),
        ("Método de envio de e-mail", op.metodo_envio or "Nenhum e-mail enviado"),
        ("Relatório gerado em", data_br(gerado_em)),
    ]
    linhas_dados = "".join(f'<tr><td class="k" style="width:26%">{_e(k)}</td><td class="v" style="width:74%">{_e(v)}</td></tr>'
                           for k, v in dados)

    linhas = []
    for n, i in enumerate(itens, start=1):
        envio = i.envio_status or (StatusEnvio.NAO_SELECIONADO if i.servidor_id else "—")
        erro = f"<br/>{_e(i.envio_detalhe)}" if i.envio_detalhe and envio == StatusEnvio.ERRO else ""
        obs = f"<br/>{_e(i.observacao)}" if i.observacao else ""
        linhas.append(
            f'<tr class="{"par" if n % 2 == 0 else ""}"><td>{n}</td><td>{_e(i.nome)}</td><td>{_e(i.matricula)}</td>'
            f'<td>{_e(mascarar_cpf(i.cpf))}</td><td>{_e(i.email)}</td>'
            f'<td>{_e(os.path.basename(i.arquivo or ""))}<br/><span class="hash">{_e((i.arquivo_hash or "")[:32])}</span></td>'
            f'<td>{_e(i.identificacao)}{obs}</td><td><span class="{_classe_envio(envio)}">{_e(envio)}</span>{erro}</td>'
            f'<td>{_e(data_br(i.enviado_em))}</td></tr>')
    tabela_itens = ("<table><tr><th>#</th><th>Servidor</th><th>Matrícula</th><th>CPF</th><th>E-mail</th>"
                    "<th>Arquivo da folha / SHA-256</th><th>Identificação</th><th>Envio</th><th>Data/hora envio</th></tr>"
                    + "".join(linhas) + "</table>") if linhas else "<p>Nenhum servidor nesta operação.</p>"
    tabela_eventos = "<table><tr><th>Data/hora</th><th>Evento</th></tr>" + "".join(
        f'<tr class="{"par" if n % 2 == 0 else ""}"><td>{_e(data_br(ev.momento))}</td><td>{_e(ev.descricao)}</td></tr>'
        for n, ev in enumerate(eventos, start=1)) + "</table>"

    return f"""
    <h1>Relatório de Auditoria — {op.codigo}</h1>
    <p class="sub">DIGEP · Universidade do Distrito Federal (UnDF) — Sistema de Gestão de Folhas de Ponto v{VERSAO}</p>
    <h2>Dados da operação</h2><table>{linhas_dados}</table>
    <h2>Resumo</h2>{cards}
    <h2>Servidores, folhas e envios</h2>{tabela_itens}
    <h2>Linha do tempo</h2>{tabela_eventos}
    <p class="nota">O código SHA-256 identifica de forma única o conteúdo de cada arquivo: qualquer alteração no arquivo
    gera um código diferente, o que permite comprovar que a folha enviada é a mesma registrada neste relatório.
    CPFs exibidos parcialmente mascarados (LGPD). Horários no fuso do computador que executou a operação.</p>
    """


class GeradorRelatorioPDF:
    def gerar(self, operacao, itens, eventos, gerado_em, destino):
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        pagina = pymupdf.paper_rect("a4-l")
        area = pagina + (36, 36, -36, -48)
        story = pymupdf.Story(html=montar_html(operacao, itens, eventos, gerado_em), user_css=CSS)
        buffer = io.BytesIO()
        writer = pymupdf.DocumentWriter(buffer)
        mais = True
        while mais:
            device = writer.begin_page(pagina)
            mais, _ = story.place(area)
            story.draw(device)
            writer.end_page()
        writer.close()

        # Rodapé com identificação da operação e numeração em todas as páginas
        doc = pymupdf.open(stream=buffer.getvalue(), filetype="pdf")
        total = doc.page_count
        for n, page in enumerate(doc, start=1):
            rodape = (f"{operacao.codigo} · {operacao.descricao_tipo} · {rotulo_competencia(operacao.competencia)} · "
                      f"gerado em {data_br(gerado_em)} · página {n} de {total}")
            page.insert_text((36, pagina.height - 24), rodape, fontsize=7, color=(0.39, 0.45, 0.55))
        doc.save(destino)
        doc.close()
        return destino
