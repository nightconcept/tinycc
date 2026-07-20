$ErrorActionPreference = "Stop"
$zig = if ($env:ZIG) { $env:ZIG } else { "zig" }
$root = Split-Path -Parent $PSScriptRoot
$stage = Join-Path ([IO.Path]::GetTempPath()) ("mtc-runtime-" + [IO.Path]::GetRandomFileName())

try {
    Push-Location $PSScriptRoot
    $env:TCC_C = "..\tcc.c"
    & .\build-tcc.bat -clean
    & .\build-tcc.bat -c "$zig cc -O2" -t x86_64
    if ($LASTEXITCODE) { throw "TCC build failed" }
    & $zig cc -O2 -shared ..\libtcc.c -o libtcc.dll -DTCC_TARGET_PE -DTCC_TARGET_X86_64 -DLIBTCC_AS_DLL
    if ($LASTEXITCODE) { throw "libtcc build failed" }
    Pop-Location

    Push-Location "$root\tests"
    & .\test-win32.bat all -k
    if ($LASTEXITCODE) { throw "TCC tests failed" }
    Pop-Location

    New-Item -ItemType Directory -Path "$stage\include", "$stage\lib" | Out-Null
    Copy-Item "$PSScriptRoot\include\*" "$stage\include" -Recurse
    Copy-Item "$PSScriptRoot\lib\*" "$stage\lib" -Recurse

    Push-Location $root
    & tar -cf mtc-runtime.tar -C $stage .
    if ($LASTEXITCODE) { throw "runtime archive failed" }
    & $zig cc -O2 -c tcc.c -o mtc-tcc.obj -DTCC_MAIN=tcc_main -DTCC_TARGET_PE -DTCC_TARGET_X86_64
    if ($LASTEXITCODE) { throw "embedded TCC build failed" }
    & $zig build-exe -O ReleaseSafe -femit-bin=mtc.exe mtc.zig mtc-tcc.obj -lc
    if ($LASTEXITCODE) { throw "MTC build failed" }
    & $zig test mtc.zig -lc
    if ($LASTEXITCODE) { throw "MTC unit tests failed" }
    & powershell -NoProfile -ExecutionPolicy Bypass -File win32\test-mtc.ps1
    if ($LASTEXITCODE) { throw "MTC smoke tests failed" }

    New-Item -ItemType Directory -Force dist | Out-Null
    Copy-Item mtc.exe dist\mtc-windows-x64.exe
    Pop-Location
}
finally {
    if ((Get-Location).Path -ne $root) { Pop-Location }
    Remove-Item -Recurse -Force $stage -ErrorAction SilentlyContinue
}
