param([ValidateSet('Validate','Delete')][string]$Mode='Validate')
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$cleanupRoot='E:\bridge-Agent-T28\projects\sar-adc-t28'
$cleanupDest=Join-Path $cleanupRoot 'verification\storage\2026-10-25-approved-cleanup'
$cleanupPython=Join-Path $cleanupRoot '.venv\Scripts\python.exe'
$cleanupController=Join-Path $cleanupRoot 'scripts\management\cleanup_execute.py'
$cleanupAllowed=@((Join-Path $cleanupRoot 'output\sar8_r4_staged'),(Join-Path $cleanupRoot 'output\sar8_r4_idle'))

function Read-Json([string]$path) { Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json }
function Save-Json([string]$name,$data) {
    $path=Join-Path $cleanupDest $name
    $temp=$path+'.tmp.'+$PID
    [IO.File]::WriteAllText($temp,($data | ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temp -Destination $path -Force
}
function Fingerprint([string]$path) {
    $data=& $cleanupPython $cleanupController local-fingerprint $path
    if ($LASTEXITCODE -ne 0) { throw "Local path/link guard failed: $path" }
    $data | ConvertFrom-Json
}
function Assert-LiteralFile([string]$path) {
    $full=[IO.Path]::GetFullPath($path)
    $inside=$false
    foreach ($root in $cleanupAllowed) {
        if ($full.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) { $inside=$true }
    }
    if (-not $inside) { throw "Outside exact approved cleanup roots: $full" }
    $item=Get-Item -LiteralPath $full -Force
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Not a literal regular file: $full" }
    return $full
}
function Assert-Unchanged($current,$expected) {
    foreach ($key in @('bytes','mtime_ns','ctime_ns','inode','device','nlink')) {
        if ($current.$key -ne $expected.$key) { throw "Changed fingerprint $key : $($current.path)" }
    }
}
function Assert-Unused([string]$path) {
    $stream=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::None)
    $stream.Dispose()
}

$cleanupSpec=Read-Json (Join-Path $cleanupDest 'input.json')
$cleanupAuth=Read-Json (Join-Path $cleanupDest 'authorization.json')
$cleanupReviewPath=Join-Path $cleanupRoot 'management\cleanup\2026-10-25\review_manifest.json'
$cleanupReview=Read-Json $cleanupReviewPath
$cleanupReviewText=[IO.File]::ReadAllText($cleanupReviewPath,[Text.Encoding]::UTF8).Replace("`r`n","`n")
$cleanupReviewAlgorithm=[Security.Cryptography.SHA256]::Create()
try { $cleanupReviewHash=[BitConverter]::ToString($cleanupReviewAlgorithm.ComputeHash([Text.Encoding]::UTF8.GetBytes($cleanupReviewText))).Replace('-','').ToLowerInvariant() }
finally { $cleanupReviewAlgorithm.Dispose() }
if ($cleanupReviewHash -ne $cleanupSpec.review_sha256 -or $cleanupAuth.review_sha256 -ne $cleanupReviewHash) { throw 'Approved source digest mismatch' }
if ($cleanupSpec.local_targets.Count -ne 21) { throw 'Unexpected local target count' }
$cleanupReviewTargets=@{}
foreach ($p in $cleanupReview.proposals) { if ($p.side -eq 'local') { foreach ($f in $p.files) { $cleanupReviewTargets[$f.path]=$f } } }
foreach ($row in $cleanupSpec.local_targets) {
    if (-not $cleanupReviewTargets.ContainsKey($row.path) -or $cleanupReviewTargets[$row.path].bytes -ne $row.bytes) { throw 'Unreviewed local target' }
}
try { [Diagnostics.Process]::GetCurrentProcess().PriorityClass=[Diagnostics.ProcessPriorityClass]::BelowNormal } catch { }

if ($Mode -eq 'Validate') {
    $cleanupValidationPath=Join-Path $cleanupDest 'local_validation.json'
    if (Test-Path -LiteralPath $cleanupValidationPath) { throw 'Validation already exists; preserve it, do not blindly repeat' }
    $cleanupResult=@{status='validating';review_sha256=$cleanupReviewHash;files=@();started_at_utc=[DateTime]::UtcNow.ToString('o')}
    Save-Json 'local_validation.state.json' @{status='running';completed=0}
    try {
        foreach ($row in $cleanupSpec.local_targets) {
            $full=Assert-LiteralFile $row.path
            $before=Fingerprint $full
            if ($before.bytes -ne $row.bytes -or $before.mtime_ns -ne $row.mtime_ns) { throw "Changed since review: $full" }
            Save-Json 'local_validation.state.json' @{status='running';completed=$cleanupResult.files.Count;current_path=$row.path}
            $stream=[IO.File]::Open($full,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::None)
            $algorithm=[Security.Cryptography.SHA256]::Create()
            try { $digest=[BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-','').ToLowerInvariant() }
            finally { $algorithm.Dispose();$stream.Dispose() }
            $after=Fingerprint $full
            Assert-Unchanged $after $before
            if ($row.category -eq 'transfer_parts') {
                $part=[IO.Path]::GetFileName($full)
                if ($digest -ne $cleanupSpec.historical_parts.$part) { throw "Historical part SHA mismatch: $full" }
            }
            $cleanupResult.files+=@{path=$row.path;bytes=$row.bytes;sha256=$digest;fingerprint=$after}
            Write-Output ('LOCAL_HASH_OK '+$cleanupResult.files.Count+'/21 '+$row.path)
        }
        $cleanupResult.status='validated';$cleanupResult.completed_at_utc=[DateTime]::UtcNow.ToString('o')
        Save-Json 'local_validation.json' $cleanupResult
        Save-Json 'local_validation.state.json' @{status='complete';completed=21}
    } catch {
        Save-Json 'local_validation.state.json' @{status='failed';completed=$cleanupResult.files.Count;message=$_.Exception.Message}
        throw
    }
    return
}

$cleanupReceiptPath=Join-Path $cleanupDest 'local_receipt.json'
if (Test-Path -LiteralPath $cleanupReceiptPath) { throw 'Local deletion receipt exists: reconcile it before any retry' }
$cleanupValidated=Read-Json (Join-Path $cleanupDest 'local_validation.json')
$cleanupReconciled=Read-Json (Join-Path $cleanupDest 'reconciliation.json')
$cleanupRemote=Read-Json (Join-Path $cleanupDest 'remote_receipt.json')
$cleanupRetained=Read-Json (Join-Path $cleanupDest 'retained_check.json')
if ($cleanupValidated.status -ne 'validated' -or $cleanupReconciled.status -ne 'reconciled' -or $cleanupRemote.status -ne 'complete' -or $cleanupRetained.status -ne 'retained_unchanged') { throw 'Incomplete cross-domain validation' }
if ($cleanupReconciled.review_sha256 -ne $cleanupReviewHash -or $cleanupRemote.review_sha256 -ne $cleanupReviewHash -or $cleanupRetained.review_sha256 -ne $cleanupReviewHash) { throw 'Cross-domain approval mismatch' }
if (([DateTime]::UtcNow-[DateTime]::Parse($cleanupRetained.received_at_utc).ToUniversalTime()).TotalMinutes -gt 10) { throw 'Retained remote check stale; refresh read-only check' }
$cleanupHashes=@{}
foreach ($f in $cleanupValidated.files) { $cleanupHashes[$f.path]=$f }
foreach ($row in $cleanupSpec.local_targets) {
    $full=Assert-LiteralFile $row.path
    Assert-Unchanged (Fingerprint $full) $cleanupHashes[$row.path].fingerprint
    Assert-Unused $full
}
$cleanupReceipt=@{status='deleting';review_sha256=$cleanupReviewHash;files=@();permanent=$true;started_at_utc=[DateTime]::UtcNow.ToString('o');free_before=[IO.DriveInfo]::new('E:\').AvailableFreeSpace}
Save-Json 'local_receipt.json' $cleanupReceipt
try {
    foreach ($row in $cleanupSpec.local_targets) {
        $full=Assert-LiteralFile $row.path
        Assert-Unchanged (Fingerprint $full) $cleanupHashes[$row.path].fingerprint
        Assert-Unused $full
        $entry=@{path=$row.path;bytes=$row.bytes;sha256=$cleanupHashes[$row.path].sha256;status='intent'}
        $cleanupReceipt.files+=,$entry
        Save-Json 'local_receipt.json' $cleanupReceipt
        Remove-Item -LiteralPath $full -Force
        if (Test-Path -LiteralPath $full) { throw "Removal readback failed: $full" }
        $entry.status='deleted_verified';Save-Json 'local_receipt.json' $cleanupReceipt
        Write-Output ('LOCAL_DELETED '+$cleanupReceipt.files.Count+'/21 '+$row.path)
    }
    $cleanupReceipt.status='complete'
    $cleanupReceipt.deleted_bytes=($cleanupReceipt.files | Measure-Object -Property bytes -Sum).Sum
    $cleanupReceipt.free_after=[IO.DriveInfo]::new('E:\').AvailableFreeSpace
    $cleanupReceipt.completed_at_utc=[DateTime]::UtcNow.ToString('o')
    Save-Json 'local_receipt.json' $cleanupReceipt
} catch {
    $cleanupReceipt.status='partial_failure';$cleanupReceipt.message=$_.Exception.Message
    Save-Json 'local_receipt.json' $cleanupReceipt
    throw
}
