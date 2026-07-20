$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$tmp = Join-Path ([IO.Path]::GetTempPath()) ("mtc-test-" + [IO.Path]::GetRandomFileName())

try {
    New-Item -ItemType Directory $tmp | Out-Null
    $env:MTC_CACHE_DIR = "$tmp\cache"
    Copy-Item "$root\mtc.exe" "$tmp\mtc.exe"

    Push-Location $tmp
    if ((& .\mtc.exe "$root\examples\ex1.c") -ne "Hello World") { throw "run failed" }
    & .\mtc.exe build "$root\examples\ex1.c" -o "$tmp\hello.exe"
    if ($LASTEXITCODE -or (& "$tmp\hello.exe") -ne "Hello World") { throw "build failed" }
    & .\mtc.exe lint "$root\examples\ex1.c"
    if ($LASTEXITCODE) { throw "lint failed" }
    & .\mtc.exe tcc -v
    if ($LASTEXITCODE) { throw "raw TCC failed" }
    if (-not (Test-Path "$env:MTC_CACHE_DIR\include\stddef.h")) { throw "headers not extracted" }
    if (-not (Test-Path "$env:MTC_CACHE_DIR\lib\libtcc1.a")) { throw "runtime not extracted" }
    Pop-Location
}
finally {
    if ((Get-Location).Path -ne $root) { Pop-Location }
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
