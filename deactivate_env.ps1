# Check if deactivate function exists
deactivate

# Set environment variable
$env:PAWNPASSANT_DEV = "false"

Write-Host "Venv deactivated and PAWNPASSANT_DEV set to false"