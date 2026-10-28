; Script do Inno Setup para o instalador do DIGEP - Sistema de Gestao de Folhas de Ponto (UnDF)
;
; Como gerar o instalador (no Windows):
;   1. Rode "python build_exe.py" na raiz do projeto (gera dist\DIGEP_Folha_de_Ponto.exe).
;   2. Rode "python installer\preparar_tesseract.py" (copia o Tesseract OCR deste computador para
;      installer\Tesseract-OCR, para o instalador leva-lo junto). Sem esse passo o instalador e gerado
;      sem OCR, e folhas escaneadas nao sao reconhecidas nos computadores sem Tesseract.
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
PrivilegesRequiredOverridesAllowed=commandline dialog
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
  #pragma warning "installer\Tesseract-OCR nao encontrado: o instalador sera gerado SEM OCR. Rode installer\preparar_tesseract.py."
#endif

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
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

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and not WordInstalado then
    SuppressibleMsgBox('O Microsoft Word não foi encontrado neste computador.' + #13#10#13#10 +
      'O DIGEP funciona normalmente, mas as folhas de ponto geradas sairão apenas em Word (.docx), ' +
      'sem a versão em PDF. Para gerar os PDFs, instale o Microsoft Word.',
      mbInformation, MB_OK, IDOK);
end;
