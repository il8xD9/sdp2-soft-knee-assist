# Run the Nastran decks one at a time, record wall time and peak memory, move the solver files to runs\<run>,
# list solver errors and non-convergence in runs\solver_messages.csv, then post-process each run with post_process.py.
#   powershell -ExecutionPolicy Bypass -File scripts\run_queue.ps1 -ListFile model\run_list.txt [-Ram 2000] [-Np 4] [-StallMin 45] [-NoPost]
#   or -List "model\CHK_FB\CHK_FB.nas;model\HCC_P20\HCC_P20.nas" (paths relative to the fea folder or absolute; '#' = comment)
# RAM=<MB> and NPROCESSORS=<n> are passed to the solver on the command line. A watchdog stops a run whose load level has not
# advanced for -StallMin minutes (the converged subcases stay in the .OUT and are post-processed).
# -Extra: further solver directives; default HEXREDORD=OFF (full integration of hexahedra). The contact penalty scale
# INITSLINEKSFACT stays at the solver default (1e-2).
param([string]$List = "", [string]$ListFile = "", [int]$Ram = 2500, [int]$Np = 4, [int]$StallMin = 45, [string]$Extra = "HEXREDORD=OFF", [switch]$NoPost,
      [string]$Exe = "C:\Program Files\Autodesk\Inventor Nastran 2026\Nastran\Nastran.exe", [string]$Py = "python")
$ErrorActionPreference = "Continue"
$R = Split-Path $PSScriptRoot -Parent
$exe = $Exe      # Inventor Nastran solver; pass -Exe if installed elsewhere
$py = $Py        # Python 3 with numpy, scipy, matplotlib, openpyxl, python-docx
$elog = Join-Path $R "runs\solver_messages.csv"
$qlog = Join-Path $R "runs\queue_log.txt"
New-Item -ItemType Directory -Force (Join-Path $R "runs") | Out-Null
if (-not (Test-Path $elog)) { [IO.File]::WriteAllText($elog, "ID,Time,Step,Message,Cause,Action,Evidence`r`n") }
function Log([string]$m) { "$(Get-Date -Format s) $m" | Out-File -Append -Encoding utf8 $qlog; Write-Output $m }
function Csv([string]$s) { '"' + ($s -replace '"', "'") + '"' }
function AddErr([string]$step, [string]$msg, [string]$cause, [string]$fix, [string]$proof) {
    $n = (Select-String -Path $elog -Pattern '^E-\d+' | Measure-Object).Count + 1
    $id = "E-{0:D2}" -f $n
    $line = "$id,$(Get-Date -Format 'yyyy-MM-dd HH:mm'),$(Csv $step),$(Csv $msg),$(Csv $cause),$(Csv $fix),$(Csv $proof)"
    [IO.File]::AppendAllText($elog, $line + "`r`n", (New-Object Text.UTF8Encoding $false))
}
$decks = @()
if ($List) { $decks += $List.Split(";") | Where-Object { $_.Trim() } }
if ($ListFile) { $decks += Get-Content $ListFile | Where-Object { $_.Trim() -and -not $_.Trim().StartsWith("#") } }
foreach ($d in $decks) {
    $d = $d.Trim()
    $nas = if ([IO.Path]::IsPathRooted($d)) { $d } else { Join-Path $R $d }
    if (-not (Test-Path $nas)) { Log "missing deck $nas"; AddErr "run_queue" "deck not found: $nas" "queue list" "skipped" $qlog; continue }
    $name = [IO.Path]::GetFileNameWithoutExtension($nas)
    $src = Split-Path $nas -Parent
    $run = Split-Path $src -Leaf
    $dst = Join-Path $R "runs\$run"
    New-Item -ItemType Directory -Force $dst | Out-Null
    $tmp = Join-Path $dst "tmp_$name"
    New-Item -ItemType Directory -Force $tmp | Out-Null
    Log "start $name (RAM=$Ram NP=$Np)"
    $t0 = Get-Date
    $args_ = "`"$nas`" RAM=$Ram NPROCESSORS=$Np FILESPEC=`"$tmp`" $Extra"
    $p = Start-Process -FilePath $exe -ArgumentList $args_ -WorkingDirectory $src -NoNewWindow -PassThru -RedirectStandardOutput (Join-Path $dst "${name}_console.txt")
    $null = $p.Handle
    $peak = 0; $best = -1.0; $tbest = Get-Date; $stopped = $false
    $lg = Join-Path $src "$name.LOG"
    while (-not $p.HasExited) {
        Start-Sleep 15
        try { $p.Refresh(); if ($p.PeakWorkingSet64 -gt $peak) { $peak = $p.PeakWorkingSet64 } } catch {}
        $lv = Select-String -Path $lg -Pattern "LOAD LEVEL FOR SUBCASE\s+(\d+)\s+AT\s+([\d.]+)\s+PERCENT" -ErrorAction SilentlyContinue | Select-Object -Last 1
        if ($lv) {
            $prog = [double]$lv.Matches[0].Groups[1].Value * 1000 + [double]$lv.Matches[0].Groups[2].Value
            if ($prog -gt $best) { $best = $prog; $tbest = Get-Date }
            elseif (((Get-Date) - $tbest).TotalMinutes -gt $StallMin) {
                Log "watchdog: $name no load-level progress for $StallMin min (last $($lv.Line.Trim())) - stopped"
                AddErr "run $name" "watchdog: no load-level progress for $StallMin min; last: $($lv.Line.Trim())" "non-convergence / stall in this subcase" "run stopped, converged subcases kept and post-processed" $lg
                Stop-Process -Id $p.Id -Force; $stopped = $true; break
            }
        }
    }
    $sec = [int]((Get-Date) - $t0).TotalSeconds
    $mb = [int]($peak / 1MB)
    Start-Sleep 3
    foreach ($ext in @(".OUT", ".LOG", ".FNO", ".RSF", "_err.json", "_adp.json", ".PCH")) {
        $f = Join-Path $src "$name$ext"
        if ((Test-Path $f) -and ($src -ne $dst)) { Move-Item -Force $f $dst }
    }
    foreach ($ext in @(".nas", "_info.pkl", "_steps.csv", "_mesh.pkl")) {
        $f = Join-Path $src "$name$ext"
        if ((Test-Path $f) -and ($src -ne $dst)) { Copy-Item -Force $f $dst }
    }
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
    "$name exit=$($p.ExitCode) seconds=$sec peakMB=$mb stopped=$stopped start=$($t0.ToString('s'))" | Out-File -Append -Encoding utf8 (Join-Path $dst "runtime.txt")
    Log "done $name exit=$($p.ExitCode) seconds=$sec peakMB=$mb"
    $log2 = Join-Path $dst "$name.LOG"
    if (Test-Path $log2) {
        $fat = Select-String -Path $log2 -Pattern "FATAL ERROR [A-Z]?\d+:.*" | Where-Object { $_.Line -notmatch "\(\d+\)\s*$" } | Select-Object -First 3
        foreach ($m in $fat) { AddErr "run $name" $m.Line.Trim() "solver" "see the .LOG file" $log2 }
        $bis = (Select-String -Path $log2 -Pattern "BISECTING CURRENT LOAD INCREMENT" | Measure-Object).Count
        if ($bis -gt 0) { AddErr "run $name" "WARNING E5075: BISECTING CURRENT LOAD INCREMENT x $bis" "load increment too large for convergence at that point" "automatic bisection (NLPARM MAXBIS 10) - informational" $log2 }
    } else { AddErr "run $name" "no .LOG produced (exit $($p.ExitCode))" "solver start failure" "check console" (Join-Path $dst "${name}_console.txt") }
    if (-not $NoPost) {
        & $py -P (Join-Path $PSScriptRoot "post_process.py") (Join-Path $dst "$name.OUT") 2>&1 | Out-File -Encoding utf8 (Join-Path $dst "${name}_post_log.txt")
        Log "post-processed $name"
    }
}
Log "queue finished"
