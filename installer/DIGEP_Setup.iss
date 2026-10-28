; Script do Inno Setup para o instalador do DIGEP - Sistema de Gestao de Folhas de Ponto (UnDF)
;
; Como gerar o instalador (no Windows):
;   1. Rode "python build_exe.py" na raiz do projeto (gera dist\DIGEP_Folha_de_Ponto.exe).
;   2. Rode "python installer\preparar_tesseract.py" (copia o Tesseract OCR deste computador para
;      installer\Tesseract-OCR, para o instalador leva-lo junto). Sem esse passo a compilacao para com erro.
;   3. Instale o Inno Setup (gratuito): https://jrsoftware.org/isdl.php
;   4. Abra este arquivo no Inno Setup Compiler e clique em "Compile" (ou rode
;      "ISCC installer\DIGEP_Setup.iss" pelo prompt de comando).
;   5. O instalador final fica em installer\output\DIGEP_Folha_de_Ponto_Setup.exe.

#define MyAppName "DIGEP - Folha de Ponto"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "DIGEP - UnDF"
#define MyAppExeName "DIGEP_Folha_de_Ponto.exe"
#define ComTesseract DirExists(AddBackslash(SourcePath) + "Tesseract-OCR")

[Setup]
AppId={{B39F2C2E-6E7C-4B7F-9C2E-6C1E4C0F5A11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\DIGEP Folha de Ponto
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=DIGEP_Folha_de_Ponto_Setup
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Instala só para o usuário atual (em %LOCALAPPDATA%\Programs), sem pedir administrador. A TI ainda pode
; instalar para todos com "/ALLUSERS" na linha de comando.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline
; Se o DIGEP estiver aberto, fecha antes de substituir o .exe (senão a atualização não é gravada)
CloseApplications=force
RestartApplications=no
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar um atalho na Área de Trabalho"; GroupDescription: "Atalhos adicionais:"

[Dirs]
; O banco, as folhas e os relatorios ficam ao lado do .exe. Em "Arquivos de Programas" um usuario comum
; nao pode gravar, entao a pasta do sistema recebe permissao de modificacao para os usuarios.
Name: "{app}"; Permissions: users-modify

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
#if ComTesseract
Source: "Tesseract-OCR\*"; DestDir: "{app}\Tesseract-OCR"; Flags: ignoreversion recursesubdirs createallsubdirs
#else
  #error "installer\Tesseract-OCR nao encontrado: rode python installer\preparar_tesseract.py antes de compilar."
#endif

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Verificar instalação do {#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--verificar"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
// O Word converte as folhas geradas em PDF. Ele nao pode ir no instalador, entao avisamos se faltar.
function WordInstalado: Boolean;
begin
  Result := RegKeyExists(HKEY_CLASSES_ROOT, 'Word.Application\CLSID');
end;

// Roda o próprio DIGEP em modo de verificação (planilha, geração das folhas, OCR, e-mail) numa pasta temporária.
procedure VerificarInstalacao;
var
  Codigo: Integer;
begin
  WizardForm.StatusLabel.Caption := 'Verificando a instalação…';
  if not Exec(ExpandConstant('{app}\{#MyAppExeName}'), '--verificar --silencioso', ExpandConstant('{app}'),
              SW_HIDE, ewWaitUntilTerminated, Codigo) or (Codigo <> 0) then
    SuppressibleMsgBox('A verificação da instalação encontrou problemas.' + #13#10#13#10 +
      'Os detalhes estão em:' + #13#10 + ExpandConstant('{app}\verificacao.txt') + #13#10#13#10 +
      'Envie esse arquivo para quem dá suporte ao DIGEP.', mbError, MB_OK, IDOK);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep <> ssPostInstall then
    exit;
  VerificarInstalacao;
  if not WordInstalado then
    SuppressibleMsgBox('O Microsoft Word não foi encontrado neste computador.' + #13#10#13#10 +
      'O DIGEP funciona normalmente, mas as folhas de ponto geradas sairão apenas em Word (.docx), ' +
      'sem a versão em PDF. Para gerar os PDFs, instale o Microsoft Word.',
      mbInformation, MB_OK, IDOK);
end;
