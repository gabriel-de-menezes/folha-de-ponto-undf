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

O envio pode ser feito via **SMTP** (recomendado, funciona em qualquer
computador) ou via **MS Outlook Desktop** (requer Outlook instalado e
configurado no Windows).

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

1. **📥 Servidores** — importe a planilha Excel com os servidores (nome,
   matrícula, CPF, e-mail pessoal, carga horária, se acumula cargo). Também é
   possível editar um servidor manualmente (duplo clique na lista).
2. **📄 Gerar Folhas** — gera folhas de ponto em branco (.docx/.pdf) a partir
   do modelo, para impressão e assinatura mensal.
3. **🔍 OCR & Digitalizações** — depois que as folhas assinadas forem
   digitalizadas, faça o upload em lote. O sistema roda OCR e tenta
   identificar automaticamente o servidor e a competência pelo texto
   extraído. Use **Conferência / Validação Manual** para revisar ou corrigir
   folhas que não foram identificadas automaticamente — esse é o passo de
   "conferência/validação" antes do arquivamento.
4. **🔎 Consulta & Arquivo** — busque qualquer folha já arquivada por nome,
   matrícula ou competência, e abra/baixe o arquivo original.
5. **✉️ Envio Acumuladores** — envia a folha arquivada (a digitalizada
   assinada, se existir; senão a gerada) para o e-mail pessoal de cada
   servidor que acumula cargo, na competência selecionada. Mostra o status
   (Pendente/Enviado/Erro) por servidor e permite reenviar individualmente.
6. **📊 Auditoria de Envios** — histórico completo de tentativas de envio,
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
