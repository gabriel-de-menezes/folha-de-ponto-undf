# Roda dentro de um Windows recém-instalado (contêiner com a imagem oficial "Windows Server" da Microsoft,
# sem Python, Visual C++, Office, Tesseract nem nenhum outro programa): instala o DIGEP só com o instalador
# e roda a verificação da instalação. Usado pelo workflow .github/workflows/instalador.yml.
#
# Uso (no contêiner):  powershell -File C:\teste\testar_windows_novo.ps1
#   C:\teste deve ter o DIGEP_Folha_de_Ponto_Setup.exe; os resultados ficam em C:\teste\resultado.
$ErrorActionPreference = "Stop"
$teste = "C:\teste"
$resultado = "$teste\resultado"
New-Item -ItemType Directory -Force $resultado | Out-Null
$destino = "$env:LOCALAPPDATA\Programs\DIGEP Folha de Ponto"  # instalação "só para mim"

# 1. Prova de que é um Windows limpo: nada do que o DIGEP usa está instalado
$ambiente = @(
  "Windows: $((Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').ProductName) build $([Environment]::OSVersion.Version)",
  "Python no PATH: $([bool](Get-Command python -ErrorAction SilentlyContinue))",
  "Tesseract no PATH: $([bool](Get-Command tesseract -ErrorAction SilentlyContinue))",
  "LibreOffice instalado: $(Test-Path "$env:ProgramFiles\LibreOffice")",
  "Microsoft Word: $(Test-Path 'Registry::HKEY_CLASSES_ROOT\Word.Application')",
  "Runtime do Visual C++ (msvcp140.dll no System32): $(Test-Path "$env:SystemRoot\System32\msvcp140.dll")",
  "Programas instalados: $((Get-ChildItem 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall' -ErrorAction SilentlyContinue | Measure-Object).Count)"
)
$ambiente | Set-Content "$resultado\ambiente.txt" -Encoding UTF8
$ambiente

# 2. Instala como um usuário faria (silencioso, só para o usuário atual)
$instalacao = Start-Process "$teste\DIGEP_Folha_de_Ponto_Setup.exe" -Wait -PassThru `
  -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER", "/LOG=`"$resultado\instalacao.log`""
if ($instalacao.ExitCode -ne 0) { throw "O instalador terminou com código $($instalacao.ExitCode)" }
foreach ($arquivo in "DIGEP_Folha_de_Ponto.exe", "Tesseract-OCR\tesseract.exe", "Tesseract-OCR\tessdata\por.traineddata",
                     "LibreOffice\program\soffice.exe") {
  if (-not (Test-Path "$destino\$arquivo")) { throw "Faltou na instalação: $arquivo" }
}
"Instalado em: $destino"

# 3. Verificação da instalação: planilha, geração das folhas, PDF (LibreOffice), OCR (Tesseract), e-mail
$relatorio = "$resultado\verificacao.txt"
$verificacao = Start-Process "$destino\DIGEP_Folha_de_Ponto.exe" -Wait -PassThru -WorkingDirectory $destino `
  -ArgumentList "--verificar", "`"$relatorio`"", "--silencioso"
Get-Content $relatorio -Encoding UTF8
if ($verificacao.ExitCode -ne 0) { throw "A verificação da instalação falhou (código $($verificacao.ExitCode))" }
if (Select-String -Path $relatorio -Pattern "^\[(FALHA|AVISO)\]") { throw "A verificação apontou problemas" }
"OK: num Windows recém-instalado, o DIGEP instalado só pelo instalador passou na verificação."
