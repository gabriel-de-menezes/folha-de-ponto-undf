; Script do Inno Setup para o instalador do DIGEP - Sistema de Gestao de Folhas de Ponto (UnDF)
;
; Como gerar o instalador (no Windows): de dois cliques em installer\gerar_instalador.bat (ou rode
; "python installer\gerar_instalador.py"). Ele faz os passos abaixo sozinho:
;   1. Usa o dist\DIGEP_Folha_de_Ponto.exe (gerado por "python build_exe.py").
;   2. Roda "python installer\preparar_tesseract.py --baixar", que baixa o Tesseract OCR oficial para
;      installer\Tesseract-OCR (leitura das folhas escaneadas).
;   3. Roda "python installer\preparar_libreoffice.py", que baixa o LibreOffice portatil oficial para
;      installer\LibreOffice (conversao das folhas em PDF sem Microsoft Word), e
;      "python installer\gerar_media_foundation.py" (substitutas do Media Foundation para as edicoes "N").
;      Sem essas duas pastas a compilacao para com erro: o instalador sempre leva tudo o que o sistema usa,
;      para funcionar num Windows recem-instalado, sem Python, Office nem internet.
;   4. Instala o Inno Setup pelo winget, se faltar (https://jrsoftware.org/isdl.php).
;   5. Compila este arquivo ("ISCC installer\DIGEP_Setup.iss").
;   6. O instalador final fica em installer\output\DIGEP_Folha_de_Ponto_Setup.exe.

#define MyAppName "DIGEP - Folha de Ponto"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "DIGEP - UnDF"
#define MyAppExeName "DIGEP_Folha_de_Ponto.exe"
#define ComTesseract DirExists(AddBackslash(SourcePath) + "Tesseract-OCR")
#define ComLibreOffice FileExists(AddBackslash(SourcePath) + "LibreOffice\program\soffice.exe")
#define ComMediaFoundation FileExists(AddBackslash(SourcePath) + "MediaFoundation\mfplat.dll")

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
; O instalador leva ~700 MB (LibreOffice e Tesseract). "ultra" e varias threads esgotam a memoria do
; compilador (32 bits): "max" num processo separado compacta quase igual, sem "Out of memory".
Compression=lzma2/max
SolidCompression=yes
LZMAUseSeparateProcess=yes
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

[InstallDelete]
; Numa atualizacao, tira as copias antigas do Tesseract e do LibreOffice antes de gravar as novas
; (sem misturar arquivos de versoes diferentes). O banco e as folhas nao sao tocados.
Type: filesandordirs; Name: "{app}\Tesseract-OCR"
Type: filesandordirs; Name: "{app}\LibreOffice"

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
#if ComTesseract
Source: "Tesseract-OCR\*"; DestDir: "{app}\Tesseract-OCR"; Flags: ignoreversion recursesubdirs createallsubdirs
#else
  #error "installer\Tesseract-OCR nao encontrado: rode python installer\gerar_instalador.py (ou python installer\preparar_tesseract.py --baixar) antes de compilar."
#endif
#if ComLibreOffice
Source: "LibreOffice\*"; DestDir: "{app}\LibreOffice"; Flags: ignoreversion recursesubdirs createallsubdirs
#else
  #error "installer\LibreOffice nao encontrado: rode python installer\gerar_instalador.py (ou python installer\preparar_libreoffice.py) antes de compilar."
#endif
; Edicoes "N" do Windows vem sem Media Foundation, e sem ele o LibreOffice nao abre. Nelas (e so nelas)
; vao substitutas que so respondem "nao implementado" (o LibreOffice as usa so para tocar midia).
#if ComMediaFoundation
Source: "MediaFoundation\*.dll"; DestDir: "{app}\LibreOffice\program"; Flags: ignoreversion; Check: SemMediaFoundation
#else
  #error "installer\MediaFoundation nao encontrado: rode python installer\gerar_instalador.py (ou python installer\gerar_media_foundation.py) antes de compilar."
#endif

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Verificar instalação do {#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--verificar"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
// Windows sem Media Foundation (edicao "N" sem o Media Feature Pack)
function SemMediaFoundation: Boolean;
begin
  Result := not FileExists(ExpandConstant('{sys}\mfplat.dll'));
end;

// Roda o próprio DIGEP em modo de verificação (planilha, geração das folhas, PDF, OCR, e-mail) numa pasta
// temporária. O PDF sai pelo Word, se houver, ou pelo LibreOffice que vai junto.
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
end;
