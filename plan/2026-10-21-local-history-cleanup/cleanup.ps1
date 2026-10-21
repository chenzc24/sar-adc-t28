[CmdletBinding()]
param([switch]$Execute)

$ErrorActionPreference = 'Stop'
$taskRepo = 'E:\bridge-Agent-T28\projects\sar-adc-t28'
$taskOutput = Join-Path $taskRepo 'output'
$taskReceipt = Join-Path $taskRepo 'verification\storage\2026-10-21-history-cleanup.json'
$taskExpectedBytes = [long]42877383874
$taskExpectedCount = 202
$taskGroups = [ordered]@{
    old10bit = @('veriloga_baseline_spectre', 'veriloga_allocated_noise_spectre')
    oldBootstrap = @(
        'bootstrap_driver_error_reduction', 'bootstrap_hold_ablation',
        'bootstrap_driver_design', 'bootstrap_netlist_fast_ab',
        'bootstrap_isolate_before_reset', 'bootstrap_turnoff_charge_screen',
        'bootstrap_t28_hold_pulldown'
    )
    oldHandshake = @('sar8_async_impl')
    oldIntegration = @(
        'sar8_join_r1', 'sar8_join_r2', 'sar8_reference_alignment',
        'sar8_restore_guard', 'sar8_restore_cross_input'
    )
    unselectedWidth = @(
        'b_hf_main_w\w2', 'b_hf_main_w\w3',
        'b_sine_main_w\w2', 'b_sine_main_w\w3'
    )
}

function Assert-PlainPath([string]$Path, [string]$Boundary) {
    $taskResolved = (Resolve-Path -LiteralPath $Path).Path
    if (-not $taskResolved.StartsWith($Boundary + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Outside allowed boundary: $taskResolved"
    }
    $taskWalk = Get-Item -LiteralPath $taskResolved -Force
    while ($taskWalk.FullName -ne $taskRepo) {
        if ($taskWalk.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Reparse point refused: $($taskWalk.FullName)"
        }
        $taskWalk = Get-Item -LiteralPath (Split-Path -Parent $taskWalk.FullName) -Force
    }
    return $taskResolved
}

function Get-TreeFiles {
    foreach ($taskRoot in $taskRoots) {
        Get-ChildItem -LiteralPath $taskRoot -Recurse -Force | ForEach-Object {
            if ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Reparse point refused: $($_.FullName)"
            }
            if (-not $_.PSIsContainer) { $_ }
        }
    }
}

function Get-Metadata($File) {
    [ordered]@{
        path = $File.FullName
        bytes = [long]$File.Length
        last_write_utc = $File.LastWriteTimeUtc.ToString('o')
    }
}

function Get-RetainedDigest($Files) {
    $taskLines = foreach ($taskFile in ($Files | Sort-Object FullName)) {
        $taskHash = (Get-FileHash -LiteralPath $taskFile.FullName -Algorithm SHA256).Hash
        "$($taskFile.FullName)|$($taskFile.Length)|$($taskFile.LastWriteTimeUtc.Ticks)|$taskHash"
    }
    $taskSha = [Security.Cryptography.SHA256]::Create()
    try {
        $taskDigest = $taskSha.ComputeHash([Text.Encoding]::UTF8.GetBytes(($taskLines -join "`n")))
        return [BitConverter]::ToString($taskDigest).Replace('-', '').ToLowerInvariant()
    } finally { $taskSha.Dispose() }
}

function Save-Receipt {
    $taskParent = Split-Path -Parent $taskReceipt
    if (-not (Test-Path -LiteralPath $taskParent)) {
        New-Item -ItemType Directory -Path $taskParent | Out-Null
    }
    $taskRecord | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $taskReceipt -Encoding utf8
}

Push-Location -LiteralPath $taskRepo
try {
    if (Test-Path -LiteralPath $taskReceipt) {
        throw 'Receipt already exists; never repeat a completed or partial deletion.'
    }
    if ((git diff --cached --name-only | Measure-Object).Count -ne 0) {
        throw 'Unexpected staged work; stop before deletion.'
    }
    $taskRoots = @(
        foreach ($taskGroup in $taskGroups.GetEnumerator()) {
            foreach ($taskDir in $taskGroup.Value) {
                Assert-PlainPath (Join-Path $taskOutput $taskDir) $taskOutput
            }
        }
    )
    $taskActive = @(Get-CimInstance Win32_Process -Filter (
        "Name = 'python.exe' OR Name = 'ssh.exe' OR Name = 'scp.exe' OR Name = 'spectre.exe'"
    ) | Where-Object {
        $taskCmd = $_.CommandLine
        $taskMatch = $false
        foreach ($taskGroup in $taskGroups.GetEnumerator()) {
            foreach ($taskDir in $taskGroup.Value) {
                $taskTop = ($taskDir -split '\\')[0]
                if ($taskCmd -match [regex]::Escape($taskTop)) { $taskMatch = $true }
            }
        }
        $taskMatch
    })
    if ($taskActive.Count) { throw 'An active process references an approved historical directory.' }

    $taskFiles = @(Get-TreeFiles | Sort-Object FullName)
    $taskTargets = @($taskFiles | Where-Object {
        $_.Length -ge 20MB -and ($_.Name -like '*.tran' -or $_.Extension -in @('.json', '.pickle', '.csv'))
    })
    $taskBytes = [long]($taskTargets | Measure-Object Length -Sum).Sum
    if ($taskTargets.Count -ne $taskExpectedCount -or $taskBytes -ne $taskExpectedBytes) {
        throw "Batch changed: $($taskTargets.Count) files / $taskBytes bytes; approved 202 / 42877383874."
    }
    $taskTracked = @(git ls-files -- output)
    if ($LASTEXITCODE -ne 0) { throw 'Cannot verify Git tracking.' }
    $taskTargetSet = @{}
    foreach ($taskFile in $taskTargets) {
        $null = Assert-PlainPath $taskFile.FullName $taskOutput
        $taskRelative = $taskFile.FullName.Substring($taskRepo.Length + 1).Replace('\', '/')
        if ($taskTracked -contains $taskRelative) { throw "Tracked target refused: $taskRelative" }
        $taskTargetSet[$taskFile.FullName] = $true
    }
    $taskRetained = @($taskFiles | Where-Object { -not $taskTargetSet.ContainsKey($_.FullName) })
    $taskGroupRows = @(
        foreach ($taskGroup in $taskGroups.GetEnumerator()) {
            $taskGroupFiles = @($taskTargets | Where-Object {
                $taskFilePath = $_.FullName
                $taskBelongs = $false
                foreach ($taskDir in $taskGroup.Value) {
                    if ($taskFilePath.StartsWith((Join-Path $taskOutput $taskDir) + '\')) {
                        $taskBelongs = $true
                    }
                }
                $taskBelongs
            })
            [ordered]@{
                group = $taskGroup.Key
                files = $taskGroupFiles.Count
                bytes = [long]($taskGroupFiles | Measure-Object Length -Sum).Sum
            }
        }
    )
    if (-not $Execute) {
        [ordered]@{
            mode = 'read_only_dry_run'
            files = $taskTargets.Count
            bytes = $taskBytes
            gib = $taskBytes / 1GB
            retained_files_in_allowed_roots = $taskRetained.Count
            groups = $taskGroupRows
        } | ConvertTo-Json -Depth 5
        return
    }

    # Only small receipts and hashes are persisted, never waveform backups.
    $taskSentinels = @(
        'b_short_acceptance\directed_a16\waveform.pickle',
        'b_short_acceptance\directed_b16\analysis.json',
        'b_short_acceptance\history12\analysis.json',
        'b_sine_period\waveform.pickle',
        'b_hf_main_w\w1\waveform.pickle',
        'b_dynamic_512\flow.json',
        'r3_refgate_events\comparison.json',
        'sar8_physical\cells.json'
    )
    $taskProtected = @(
        foreach ($taskSentinel in $taskSentinels) {
            $taskPath = Join-Path $taskOutput $taskSentinel
            if (Test-Path -LiteralPath $taskPath -PathType Leaf) {
                $taskItem = Get-Item -LiteralPath $taskPath
                $taskMeta = Get-Metadata $taskItem
                $taskMeta.sha256 = (Get-FileHash -LiteralPath $taskPath -Algorithm SHA256).Hash
                $taskMeta
            } else { throw "Protected sentinel missing: $taskPath" }
        }
    )
    $taskDigestBefore = Get-RetainedDigest $taskRetained
    $taskDiskBefore = [long](Get-PSDrive -Name E).Free
    $taskRecord = [ordered]@{
        schema = 1
        status = 'prepared'
        authorization = 'User explicitly confirmed permanent deletion with 删 after 39.93 GiB proposal.'
        started_utc = [DateTime]::UtcNow.ToString('o')
        project = $taskRepo
        deletion_mode = 'permanent_individual_literal_files_no_recursion_no_backup'
        approved_roots = $taskRoots
        target_count = $taskTargets.Count
        target_bytes = $taskBytes
        groups = $taskGroupRows
        targets = @($taskTargets | ForEach-Object { Get-Metadata $_ })
        retained_file_count = $taskRetained.Count
        retained_content_metadata_sha256_before = $taskDigestBefore
        protected_files = $taskProtected
        drive_free_bytes_before = $taskDiskBefore
        deleted_count = 0
        deleted_bytes = [long]0
    }
    Save-Receipt
    try {
        # Fail before the first removal if any frozen file has changed.
        foreach ($taskEntry in $taskRecord.targets) {
            $taskNow = Get-Item -LiteralPath $taskEntry.path -Force
            $null = Assert-PlainPath $taskEntry.path $taskOutput
            if ($taskNow.PSIsContainer -or $taskNow.Length -ne $taskEntry.bytes -or
                $taskNow.LastWriteTimeUtc.ToString('o') -ne $taskEntry.last_write_utc) {
                throw "Target changed before deletion: $($taskEntry.path)"
            }
        }
        $taskRecord.status = 'deleting'
        Save-Receipt
        foreach ($taskEntry in $taskRecord.targets) {
            $taskNow = Get-Item -LiteralPath $taskEntry.path -Force
            if ($taskNow.Length -ne $taskEntry.bytes -or
                $taskNow.LastWriteTimeUtc.ToString('o') -ne $taskEntry.last_write_utc) {
                throw "Target changed during deletion: $($taskEntry.path)"
            }
            Remove-Item -LiteralPath $taskEntry.path -ErrorAction Stop
            if (Test-Path -LiteralPath $taskEntry.path) { throw "Target remains: $($taskEntry.path)" }
            $taskRecord.deleted_count++
            $taskRecord.deleted_bytes += $taskEntry.bytes
        }
        $taskRemaining = @(Get-TreeFiles)
        if ($taskRemaining.Count -ne $taskRetained.Count) { throw 'Retained file count changed.' }
        $taskDigestAfter = Get-RetainedDigest $taskRemaining
        if ($taskDigestAfter -ne $taskDigestBefore) { throw 'Retained files changed.' }
        foreach ($taskEntry in $taskProtected) {
            if ((Get-FileHash -LiteralPath $taskEntry.path -Algorithm SHA256).Hash -ne $taskEntry.sha256) {
                throw "Protected baseline changed: $($taskEntry.path)"
            }
        }
        $taskRecord.retained_content_metadata_sha256_after = $taskDigestAfter
        $taskRecord.retained_files_verified = $true
        $taskRecord.protected_files_verified = $true
        $taskRecord.status = 'complete'
    } catch {
        $taskRecord.status = 'failed_requires_manual_review_no_automatic_retry'
        $taskRecord.error = $_.Exception.Message
        throw
    } finally {
        $taskRecord.finished_utc = [DateTime]::UtcNow.ToString('o')
        $taskRecord.drive_free_bytes_after = [long](Get-PSDrive -Name E).Free
        $taskRecord.drive_free_bytes_delta = $taskRecord.drive_free_bytes_after - $taskDiskBefore
        Save-Receipt
    }
    [ordered]@{
        status = $taskRecord.status
        deleted_count = $taskRecord.deleted_count
        deleted_bytes = $taskRecord.deleted_bytes
        deleted_gib = $taskRecord.deleted_bytes / 1GB
        free_gib = $taskRecord.drive_free_bytes_after / 1GB
        free_delta_gib = $taskRecord.drive_free_bytes_delta / 1GB
        retained_files_verified = $taskRecord.retained_files_verified
        protected_files_verified = $taskRecord.protected_files_verified
        receipt = $taskReceipt
    } | ConvertTo-Json
} finally { Pop-Location }
