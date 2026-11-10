$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Cannot create virtual environment' }
    & ./.venv/Scripts/python.exe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
}
& ./.venv/Scripts/python.exe -m joblab.pipeline
if ($LASTEXITCODE -ne 0) { throw 'Pipeline failed' }
& ./.venv/Scripts/python.exe -m streamlit run app.py
