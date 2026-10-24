$ErrorActionPreference = 'Stop'
$project = 'E:\bridge-Agent-T28\projects\sar-adc-t28'
$outputRoot = (Resolve-Path -LiteralPath "$project\output").Path + '\'
$manifestPath = "$project\verification\cache_cleanup_20261024.json"
$receiptPath = "$project\verification\cache_cleanup_20261024_deleted.json"
if (Test-Path -LiteralPath $receiptPath) { throw 'Receipt exists; inspect before resuming' }
$audit = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($audit.status -ne 'audited') { throw 'Audit not complete' }
$deleted = [System.Collections.Generic.List[object]]::new()
$protected = @{}
foreach ($folder in @('docs','verification','Obsidian_docs')) {
    Get-ChildItem -LiteralPath "$project\$folder" -File -Recurse | ForEach-Object {
        $protected[$_.FullName] = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
    }
}
$before = (Get-PSDrive E).Free
# Preflight the entire exact list before any removal. No directories or globs.
foreach ($item in $audit.verified) {
    $target = (Resolve-Path -LiteralPath $item.path).Path
    $raw = (Resolve-Path -LiteralPath $item.raw).Path
    if (-not $target.StartsWith($outputRoot,[StringComparison]::OrdinalIgnoreCase) -or
        -not $raw.StartsWith($outputRoot,[StringComparison]::OrdinalIgnoreCase)) { throw 'Out-of-scope path' }
    if ($target -eq $raw) { throw 'Target equals original' }
    $file = Get-Item -LiteralPath $target
    if ($file.PSIsContainer -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Unsafe file' }
    if ($file.Extension -notin @('.pickle','.gz')) { throw 'Unexpected type' }
    $tracked = git -C $project ls-files -- $target
    if ($LASTEXITCODE -ne 0 -or $tracked) { throw 'Tracked or git failure' }
    if ($file.Length -ne $item.bytes -or (Get-FileHash -LiteralPath $target).Hash -ne $item.sha256) { throw 'Candidate changed' }
    if ((Get-FileHash -LiteralPath $raw).Hash -ne $item.raw_sha256) { throw 'Original changed' }
}
foreach ($item in $audit.verified) {
    Remove-Item -LiteralPath $item.path -ErrorAction Stop
    if (Test-Path -LiteralPath $item.path) { throw 'Removal failed' }
    $deleted.Add([pscustomobject]@{path=$item.path;bytes=$item.bytes;kind=$item.kind;raw=$item.raw})
    [pscustomobject]@{status='deleting';deleted=$deleted;free_before=$before} |
        ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding utf8
    Write-Output "Deleted verified duplicate: $($item.path)"
}
foreach ($path in $protected.Keys) {
    if ((Get-FileHash -LiteralPath $path).Hash -ne $protected[$path]) { throw "Protected file changed: $path" }
}
foreach ($item in $audit.verified) {
    if (-not (Test-Path -LiteralPath $item.raw)) { throw 'Original missing' }
}
$after = (Get-PSDrive E).Free
$total = ($deleted | Measure-Object bytes -Sum).Sum
[pscustomobject]@{status='complete';deleted=$deleted;deleted_bytes=$total;free_before=$before;
    free_after=$after;free_space_delta=$after-$before;protected_files_verified=$protected.Count} |
    ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding utf8
Write-Output "REMOVED_BYTES=$total FREE_DELTA=$($after-$before) FREE_AFTER=$after"
