Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BaseDockerfile = Join-Path $RepoRoot "rom\docker\Dockerfile.base"
$BaseContext = Join-Path $RepoRoot "rom\docker"
$ModDockerfile = Join-Path $RepoRoot "rom\docker\Dockerfile"
$OutRomDir = Join-Path $RepoRoot "web\public\roms"
$OutRomPath = Join-Path $OutRomDir "josephred.gba"

$cid = $null
try {
    $baseExists = docker images -q josephred-rom-base:latest
    if (-not $baseExists) {
        Write-Output "[INFO] Building base pokefirered toolchain image (first-time setup)..."
        docker build -t josephred-rom-base:latest -f "$BaseDockerfile" "$BaseContext"
        if ($LASTEXITCODE -ne 0) {
            throw "Base Docker image build failed."
        }
    }

    Write-Output "[INFO] Building Pokemon JosephRed ROM..."
    docker build -t josephred-rom:latest -f "$ModDockerfile" "$RepoRoot"
    if ($LASTEXITCODE -ne 0) {
        throw "Pokemon JosephRed ROM compilation failed."
    }

    New-Item -ItemType Directory -Force -Path "$OutRomDir" | Out-Null
    $cid = (docker create josephred-rom:latest).Trim()
    if (-not $cid) {
        throw "Failed to create temporary container to extract ROM."
    }

    docker cp "${cid}:/opt/pokefirered/pokefirered.gba" "$OutRomPath"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to copy pokefirered.gba out of container."
    }

    $sizeMB = [math]::Round((Get-Item "$OutRomPath").Length / 1MB, 2)
    Write-Output "[OK] Built ROM: $OutRomPath ($sizeMB MB)"
}
finally {
    if ($cid) {
        docker rm -f "$cid" | Out-Null
    }
}
