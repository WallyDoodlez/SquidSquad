

function Ensure-UTF8 {
    # Fix console output encoding
    if ($PSVersionTable.PSVersion.Major -ge 7) {
        # PowerShell 7+ uses UTF-8 by default, but we enforce it anyway
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    }
    else {
        # Windows PowerShell 5.1 needs both the console code page AND OutputEncoding
        $currentCodePage = (chcp) -replace '[^\d]'
        if ($currentCodePage -ne '65001') {
            chcp 65001 > $null
        }
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    }
}


Ensure-UTF8

Write-Host "     ▲"
Write-Host "    ▲█▲"
Write-Host "  ▐▛███▜▌   S Q U I D S Q U A D   v$v  -  skill"
Write-Host " ▝▜███████▛▘  "
Write-Host "   ▘▘▘▘▘▘▘    "

