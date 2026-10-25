$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$outPath = Join-Path $repoRoot 'artifacts/full-app/mirror-results'
New-Item -ItemType Directory -Force -Path $outPath | Out-Null
docker run --rm --name wemo-matter-outlet-build --network none `
    -v 'wemo-matter-sdk-build:/sdk' -v "${repoRoot}:/work:ro" `
    -v "${outPath}:/export" wemo-matter-build-and-test:bookworm `
    sh -c 'sed "s/\r$//" /work/scripts/build_mirror_outlet_inner.sh | sh'
if ($LASTEXITCODE -ne 0) { throw "Offline Matter build failed: $LASTEXITCODE" }
