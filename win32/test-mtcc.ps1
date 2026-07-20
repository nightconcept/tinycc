$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$tmp = Join-Path ([IO.Path]::GetTempPath()) ("mtcc-test-" + [IO.Path]::GetRandomFileName())

try {
    New-Item -ItemType Directory $tmp | Out-Null
    $env:MTCC_CACHE_DIR = "$tmp\cache"
    Copy-Item "$root\mtcc.exe" "$tmp\mtcc.exe"

    Push-Location $tmp
    if ((& .\mtcc.exe "$root\src\examples\ex1.c") -ne "Hello World") { throw "run failed" }
    & .\mtcc.exe build "$root\src\examples\ex1.c" -o "$tmp\hello.exe"
    if ($LASTEXITCODE -or (& "$tmp\hello.exe") -ne "Hello World") { throw "build failed" }
    & .\mtcc.exe lint "$root\src\examples\ex1.c"
    if ($LASTEXITCODE) { throw "lint failed" }
    & .\mtcc.exe tcc -v
    if ($LASTEXITCODE) { throw "raw TCC failed" }
    if (-not (Test-Path "$env:MTCC_CACHE_DIR\include\stddef.h")) { throw "headers not extracted" }
    if (-not (Test-Path "$env:MTCC_CACHE_DIR\lib\libtcc1.a")) { throw "runtime not extracted" }
    Pop-Location
}
finally {
    if ((Get-Location).Path -ne $root) { Pop-Location }
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
