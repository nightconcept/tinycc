$ErrorActionPreference = "Stop"
$zig = if ($env:ZIG) { $env:ZIG } else { "zig" }
$root = Split-Path -Parent $PSScriptRoot
$stage = Join-Path ([IO.Path]::GetTempPath()) ("mtcc-runtime-" + [IO.Path]::GetRandomFileName())

try {
    $srcWin32 = "$root\src\win32"
    Push-Location $srcWin32
    $env:TCC_C = "..\tcc.c"
    & .\build-tcc.bat -clean
    & .\build-tcc.bat -c "$zig cc -O2" -t x86_64
    if ($LASTEXITCODE) { throw "TCC build failed" }
    & $zig cc -O2 -shared ..\libtcc.c -I.. -o libtcc.dll -DTCC_TARGET_PE -DTCC_TARGET_X86_64 -DLIBTCC_AS_DLL
    if ($LASTEXITCODE) { throw "libtcc build failed" }
    Pop-Location

    Push-Location "$root\src\tests"
    & .\test-win32.bat all -k
    if ($LASTEXITCODE) { throw "TCC tests failed" }
    Pop-Location

    New-Item -ItemType Directory -Path "$stage\include", "$stage\lib" | Out-Null
    Copy-Item "$srcWin32\include\*" "$stage\include" -Recurse
    Copy-Item "$srcWin32\lib\*" "$stage\lib" -Recurse

    Push-Location $root
    & tar -cf mtcc-runtime.tar -C $stage .
    if ($LASTEXITCODE) { throw "runtime archive failed" }
    & $zig cc -O2 -c src\tcc.c -I. -o mtcc-tcc.obj -DTCC_MAIN=tcc_main -DTCC_TARGET_PE -DTCC_TARGET_X86_64
    if ($LASTEXITCODE) { throw "embedded TCC build failed" }
    & $zig build-exe -O ReleaseSafe mtcc.zig mtcc-tcc.obj -lc
    if ($LASTEXITCODE) { throw "MTCC build failed" }
    & $zig test mtcc.zig -lc
    if ($LASTEXITCODE) { throw "MTCC unit tests failed" }
    & powershell -NoProfile -ExecutionPolicy Bypass -File win32\test-mtcc.ps1
    if ($LASTEXITCODE) { throw "MTCC smoke tests failed" }

    New-Item -ItemType Directory -Force dist | Out-Null
    Copy-Item mtcc.exe dist\mtcc-windows-x64.exe
    Pop-Location
}
finally {
    if ((Get-Location).Path -ne $root) { Pop-Location }
    Remove-Item -Recurse -Force $stage -ErrorAction SilentlyContinue
}
