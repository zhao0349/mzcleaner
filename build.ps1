param([string]$Python = '.\.venv\Scripts\python.exe')
$ErrorActionPreference = 'Stop'
$Python = (Resolve-Path -LiteralPath $Python).Path
Push-Location $PSScriptRoot
try {
    & $Python -m PyInstaller --noconfirm --clean --onedir --windowed `
        --name MzCleanerFree --collect-all flet_desktop `
        --copy-metadata flet --copy-metadata flet-desktop `
        --distpath dist --workpath build main.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed' }
    Copy-Item -LiteralPath LICENSE -Destination dist/MzCleanerFree/LICENSE
    Copy-Item -LiteralPath README.md -Destination dist/MzCleanerFree/README.md
} finally {
    Pop-Location
}
