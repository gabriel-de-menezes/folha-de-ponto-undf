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
   Windows (de preferência marcando o idioma *Portuguese*). O app encontra o
   `tesseract.exe` na pasta padrão de instalação automaticamente. Sem Tesseract,
   as digitalizações continuam sendo aceitas — o servidor é indicado na conferência.
4. (Opcional) Microsoft Word ou LibreOffice para gerar as folhas também em PDF.

## Executando

```
python main.py
```

## Configurando o envio de e-mail (menu "Configurações")

Há duas opções: **Servidor SMTP** (Gmail, Office 365 ou servidor institucional) ou
**MS Outlook** (usa o Outlook instalado e configurado no Windows).

### SMTP com Gmail

1. Na conta Google que vai enviar os e-mails, ative a **Verificação em duas etapas**
   (Conta Google → Segurança).
2. Em Conta Google → Segurança → **Senhas de app**, crie uma senha de app
   (ex.: nome "DIGEP"). O Google mostra uma senha de 16 letras — copie-a.
3. No app, em **Configurações → Envio de e-mail → Servidor SMTP**, preencha:

| Campo | Gmail | Office 365 / Outlook.com |
|---|---|---|
| Servidor (host) | `smtp.gmail.com` | `smtp.office365.com` |
| Porta | `587` | `587` |
| Usuário / e-mail | seu e-mail completo | seu e-mail completo |
| Senha de aplicativo | a senha de app de 16 letras | senha da conta ou senha de app (conforme a política do domínio) |
| STARTTLS | marcado | marcado |

4. Clique em **Testar conexão** (valida login sem enviar nada) e depois em **Salvar**.

> A senha normal da conta Google **não funciona** — o Gmail exige senha de app.
> Com porta `465`, o app usa SSL direto (desmarque STARTTLS). Para o servidor
> de e-mail institucional, peça host, porta e credenciais à equipe de TI.
> O Gmail gratuito permite cerca de 500 envios por dia.

A configuração fica salva só neste computador, no banco `folha_ponto.db`.

## Fluxo de uso

A tela **Início** tem dois fluxos guiados. Ao final de cada um (ou se ele for
interrompido), é gerado um **relatório de auditoria em PDF** em
`Relatorios_Auditoria/`, com usuário do Windows, computador, datas/horas, origem
dos dados, SHA-256 de cada arquivo, servidores envolvidos e o resultado de cada envio.

### 1. Gerar e enviar folhas de ponto
1. **Mês e planilha** — escolha o mês (vai no cabeçalho e define o calendário da
   folha) e **use a planilha base do sistema** ou **envie uma nova planilha**
   (no formato de `recursos/Planilha de professores - exemplo.xlsx`).
2. **Conferir folhas** — lista dos servidores; clique no nome para ver a folha
   gerada (.pdf, ou .docx se não houver Word/LibreOffice).
3. **Enviar por e-mail** — lista de destinatários com caixas de seleção; confirme
   e cada servidor recebe a própria folha. Um pop-up mostra o resultado.

### 2. Enviar folhas assinadas
1. **Mês e arquivos** — escolha o mês e selecione até 200 folhas em PDF ou imagem
   (JPG, PNG, TIFF, BMP). Nos PDFs, o sistema lê o texto (matrícula/nome via regex)
   e, se não conseguir, usa **OCR**; imagens vão direto para o OCR.
2. **Conferir folhas** — clique em cada linha para ver a folha e confirmar/corrigir
   o servidor; **Substituir arquivo…** troca a folha atribuída a alguém.
3. **Enviar por e-mail** — igual ao fluxo 1, anexando a folha assinada importada.

### Outras telas
- **Servidores** — define a **planilha base** (usada no fluxo 1) e permite editar
  cada servidor (dois cliques).
- **Arquivo de folhas** — todas as folhas geradas e assinadas, com busca e prévia.
- **Auditoria** — todas as operações (dois cliques abrem o relatório PDF) e o
  histórico de cada e-mail enviado.

## Gerando o executável (.exe)

```
python build_exe.py
```

O executável único é gerado em `dist/DIGEP_Folha_de_Ponto.exe`.

## Gerando o instalador (Setup.exe)

Para facilitar a instalação e demonstração em outros computadores (sem precisar
copiar o `.exe` avulso), há um instalador feito com o [Inno Setup](https://jrsoftware.org/isdl.php)
(gratuito):

1. Gere o executável primeiro (`python build_exe.py`).
2. Instale o Inno Setup no Windows.
3. Abra `installer/DIGEP_Setup.iss` no Inno Setup Compiler e clique em **Compile**
   (ou rode `ISCC installer\DIGEP_Setup.iss` no prompt de comando).
4. O instalador final é gerado em `installer/output/DIGEP_Folha_de_Ponto_Setup.exe`.

O instalador cria atalho no Menu Iniciar (e, opcionalmente, na Área de Trabalho),
grava um desinstalador em "Adicionar ou remover programas" e, ao final, oferece
abrir o app — tudo em português.

## Testes

```
python -m unittest discover -s tests -t .
```

Cobrem as regras de domínio (competência, identificação de folhas, CPF, e-mails), os casos de uso
de ponta a ponta com SQLite real em pasta temporária (e-mail e geração simulados) e o preenchimento
do modelo `.docx` real (cabeçalho e calendário do mês).

## Arquitetura

O código segue **arquitetura limpa**: as dependências apontam sempre para dentro
(interface → aplicação → domínio). A aplicação não conhece SQLite, Word, Tesseract, SMTP
nem CustomTkinter — ela define **portas** (interfaces) que a infraestrutura implementa, e
`main.py` monta tudo (raiz de composição).

```
main.py                         raiz de composição: monta os serviços e abre a janela
folha_ponto/
├── dominio/                    regras puras, sem I/O
│   ├── entidades.py            Servidor, Operacao, ItemOperacao, FolhaAssinada, ConfiguracaoEmail…
│   ├── competencia.py          mês/ano no formato canônico "JULHO/2026"
│   └── regras.py               identificação da folha (matrícula/nome), conflitos, textos de e-mail, LGPD
├── aplicacao/                  casos de uso + portas
│   ├── portas.py               contratos: repositórios, leitor de planilha, gerador de folhas, OCR, e-mail…
│   ├── servidores.py           importar planilha, planilha base, editar servidor
│   ├── gerar_folhas.py         fluxo 1: gerar as folhas do mês
│   ├── folhas_assinadas.py     fluxo 2: importar, identificar e conferir folhas assinadas
│   ├── envio.py                enviar as folhas por e-mail e encerrar a operação
│   ├── auditoria.py            operações, eventos e relatório
│   ├── configuracoes.py        e-mail e aparência
│   └── consultas.py            leitura para Arquivo e Auditoria
├── infraestrutura/             adaptadores concretos das portas
│   ├── sqlite/                 banco (schema + migrações) e repositórios
│   ├── planilha_excel.py       leitura do .xlsx (openpyxl)
│   ├── folha_docx.py           preenchimento do modelo .docx (python-docx)
│   ├── conversor_pdf.py        .docx → .pdf (Word via COM ou LibreOffice)
│   ├── leitor_folhas.py        texto do PDF (PyMuPDF) e OCR (Tesseract)
│   ├── envio_email.py          SMTP e MS Outlook
│   ├── relatorio_pdf.py        relatório de auditoria (PyMuPDF Story)
│   ├── armazenamento.py        pastas, cópias arquivadas, SHA-256
│   ├── ambiente.py             relógio, usuário e computador
│   └── container.py            liga adaptadores aos casos de uso
└── interface/                  CustomTkinter — só usa casos de uso e entidades
    ├── app.py                  janela, menu lateral, tarefas em segundo plano
    ├── paginas/                Início, Servidores, Arquivo, Auditoria, Configurações
    ├── fluxos/                 os dois fluxos guiados (base + etapa de envio compartilhada)
    ├── componentes.py          tabela, prévia, seletor de mês, diálogos
    ├── tema.py                 cores claro/escuro e fontes
    └── utilitarios.py          abrir/salvar arquivos, miniaturas
tests/                          unittest
recursos/                       modelo .docx e planilha padrão usados em runtime (embutidos no .exe)
exemplos/                       planilhas de demonstração (não usadas pelo código)
docs/                           plano de implementação e prompt original do projeto
installer/                      script do instalador (Inno Setup)
```
