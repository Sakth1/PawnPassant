# Activate virtual environment
. ".\.venv\Scripts\Activate.ps1"

# Set environment variable
$env:PAWNPASSANT_DEV = "true"

Write-Host "Venv activated and PAWNPASSANT_DEV set to true"