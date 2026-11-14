# Runs one tracker pass. Called by Windows Task Scheduler (see register_task.ps1).
# Secrets come from user environment variables (set once with setx, see README).
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
python -m src.main @args
exit $LASTEXITCODE
