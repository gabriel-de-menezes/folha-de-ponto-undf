; Script do Inno Setup para o instalador do DIGEP - Sistema de Gestao de Folhas de Ponto (UnDF)
;
; Como gerar o instalador (no Windows):
;   1. Rode "python build_exe.py" na raiz do projeto (gera dist\DIGEP_Folha_de_Ponto.exe).
;   2. Instale o Inno Setup (gratuito): https://jrsoftware.org/isdl.php
;   3. Abra este arquivo no Inno Setup Compiler e clique em "Compile" (ou rode
;      "ISCC installer\DIGEP_Setup.iss" pelo prompt de comando).
;   4. O instalador final fica em installer\output\DIGEP_Folha_de_Ponto_Setup.exe.

#define MyAppName "DIGEP - Folha de Ponto"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "DIGEP - UnDF"
#define MyAppExeName "DIGEP_Folha_de_Ponto.exe"

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
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar um atalho na Area de Trabalho"; GroupDescription: "Atalhos adicionais:"

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent
