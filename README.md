# DIGEP — Sistema de Gestão de Folhas de Ponto (UnDF)

Aplicação desktop (Python + CustomTkinter) para automatizar o fluxo mensal de
folhas de ponto da Diretoria de Gestão de Pessoas (DIGEP): importação de
servidores, geração/preenchimento de folhas, OCR e arquivamento de folhas
digitalizadas, consulta/download e envio automático por e-mail para
servidores que acumulam cargo — conforme os requisitos RF01–RF12 do projeto.

## Instalação

1. Python 3.11+ instalado.
2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
3. (Opcional, apenas para OCR de imagens/PDFs escaneados sem camada de texto)
   Instale o [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) no
   Windows e garanta que `tesseract.exe` esteja no PATH, ou aponte
   `pytesseract.pytesseract.tesseract_cmd` para o executável.

## Executando

```
python main.py
```

## Configurando o envio de e-mail (aba "⚙️ Configurações")

O envio pode ser feito via **API Resend** (recomendado — mais simples,
sem senha, funciona em qualquer sistema operacional), via **SMTP**
(Gmail/Office365/servidor institucional) ou via **MS Outlook Desktop**
(requer Outlook instalado e configurado no Windows).

### Opção recomendada: API Resend

1. Crie uma conta gratuita em [resend.com](https://resend.com) (plano grátis
   cobre ~3.000 e-mails/mês).
2. Gere uma **API Key** em Resend → API Keys.
3. (Opcional, mas recomendado para produção) Verifique um domínio próprio em
   Resend → Domains, para poder enviar como `digep@seudominio.com`. Para
   testes rápidos, pode-se usar o remetente de teste `onboarding@resend.dev`.
4. Na aba **⚙️ Configurações**, seção "Envio via API Resend", cole a API Key
   e informe o e-mail/nome do remetente. Use **Testar API Key Resend** para
   validar antes de salvar.
5. Na aba **✉️ Envio Acumuladores**, selecione o método **"API Resend"**.

Vantagens sobre o SMTP: não precisa de senha de e-mail/senha de app, não
depende de porta 587/465 liberada na rede, e a API responde de forma mais
clara em caso de erro.

Para SMTP, preencha:

| Campo | Gmail | Office 365 |
|---|---|---|
| Servidor (host) | `smtp.gmail.com` | `smtp.office365.com` |
| Porta | `587` | `587` |
| STARTTLS | ativado | ativado |
| Usuário | seu e-mail completo | seu e-mail completo |
| Senha | **senha de aplicativo** (não é a senha normal da conta) | senha da conta ou senha de app, conforme política do domínio |

> No Gmail, crie uma "Senha de app" em
> Conta Google → Segurança → Verificação em duas etapas → Senhas de app.
> Isso é necessário porque o Gmail bloqueia login de apps de terceiros com a
> senha normal.

Use o botão **Testar Conexão** para validar host/porta/usuário/senha antes de
salvar. A configuração é salva localmente no banco SQLite (`folha_ponto.db`)
e nunca é enviada a terceiros.

## Fluxo de uso

1. **🏠 Painel** — visão geral do andamento da competência selecionada: quantos
   servidores estão cadastrados, quantas folhas já foram geradas, quantas
   digitalizações ainda aguardam conferência e quantos acumuladores já
   receberam o e-mail. Cada cartão tem um atalho direto para a aba
   correspondente, além de um feed com as últimas tentativas de envio.
2. **📥 Servidores** — importe a planilha Excel com os servidores (nome,
   matrícula, CPF, e-mail pessoal, carga horária, se acumula cargo). Também é
   possível editar um servidor manualmente (duplo clique na lista).
3. **📄 Gerar Folhas** — gera folhas de ponto em branco (.docx/.pdf) a partir
   do modelo institucional padrão (fixo, não personalizável pela interface),
   para impressão e assinatura mensal.
4. **🔍 OCR & Conferência** — depois que as folhas assinadas forem
   digitalizadas, faça o upload em lote. O sistema roda OCR e tenta
   identificar automaticamente o servidor e a competência pelo texto
   extraído. Clique em qualquer folha na lista à esquerda para ver uma
   prévia da imagem/PDF e confirmar (ou corrigir) o servidor/competência no
   painel à direita — sem pop-ups, tudo na mesma tela.
5. **📚 Histórico** — lista todas as folhas já arquivadas (geradas e
   digitalizadas), com busca por nome/matrícula/competência e preview do
   arquivo ao selecionar um item.
6. **✉️ Envio Acumuladores** — envia a folha arquivada (a digitalizada
   assinada, se existir; senão a gerada) para o e-mail pessoal de cada
   servidor que acumula cargo, na competência selecionada. Mostra o status
   (Pendente/Enviado/Erro) por servidor e permite reenviar individualmente.
7. **📊 Auditoria de Envios** — histórico completo de tentativas de envio,
   com destinatário, competência, status e detalhes de erro (RF12).

## Gerando o executável (.exe)

```
python build_exe.py
```

O executável único é gerado em `dist/DIGEP_Folha_de_Ponto.exe`.

## Estrutura do projeto

| Arquivo | Responsabilidade |
|---|---|
| `gui.py` | Interface gráfica (abas e interações) |
| `db.py` | Schema SQLite e configurações persistidas |
| `excel_service.py` | Importação de servidores via planilha |
| `docx_service.py` | Preenchimento do modelo de folha de ponto |
| `pdf_service.py` | Conversão .docx → .pdf |
| `ocr_service.py` | OCR e identificação automática de servidor/competência |
| `arquivo_service.py` | Localização/consulta de folhas arquivadas |
| `email_service.py` | Envio de e-mail (SMTP/Outlook) e registro de auditoria |
