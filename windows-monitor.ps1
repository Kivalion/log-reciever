# ===== Config =====
$Url = "http://localhost:8000/api/logs"
$Drive = "C:"            # change if you want a different drive
$PostEverySeconds = 5

# ===== Helpers =====

function Get-CPUPercent {
    # Average of two 1-sec samples: smoother & more accurate than WMI
    try {
        $samples = Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 2
        $vals = $samples.CounterSamples | Select-Object -ExpandProperty CookedValue
        # Some returns include multiple counters per sample; average them all
        $avg = [math]::Round(($vals | Measure-Object -Average).Average, 2)
        if ($avg -lt 0) { $avg = 0 } elseif ($avg -gt 100) { $avg = 100 }
        return $avg
    } catch {
        # Fallback if perf counters are unavailable
        $fallback = (Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
        return [math]::Round([double]$fallback, 2)
    }
}

function Get-MemoryPercent {
    # Very reliable: % Committed Bytes In Use (what Task Manager shows)
    try {
        $val = (Get-Counter '\Memory\% Committed Bytes In Use').CounterSamples[0].CookedValue
        return [math]::Round([double]$val, 2)
    } catch {
        # Fallback via OS totals
        $os = Get-CimInstance Win32_OperatingSystem
        $totalMB = [double]($os.TotalVisibleMemorySize / 1024)
        $freeMB  = [double]($os.FreePhysicalMemory / 1024)
        $usedMB  = $totalMB - $freeMB
        return [math]::Round(($usedMB / $totalMB) * 100, 2)
    }
}

function Get-DiskUsage {
    param([string]$DeviceId = "C:")
    $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$DeviceId'"
    if (-not $disk) { throw "Drive $DeviceId not found." }
    $totalMB = [math]::Round($disk.Size / 1MB, 0)
    $freeMB  = [math]::Round($disk.FreeSpace / 1MB, 0)
    $usedMB  = $totalMB - $freeMB
    $pct     = if ($totalMB -gt 0) { [math]::Round(($usedMB / $totalMB) * 100, 2) } else { 0 }
    [pscustomobject]@{
        TotalMB     = $totalMB
        FreeMB      = $freeMB
        UsedMB      = $usedMB
        UsedPct     = $pct
    }
}

# ===== Static: MAC (first active adapter) =====
$mac = (Get-NetAdapter | Where-Object Status -eq "Up" | Select-Object -First 1).MacAddress

# ===== Loop =====
while ($true) {
    try {
        $cpu = Get-CPUPercent
        $mem = Get-MemoryPercent
        $d   = Get-DiskUsage -DeviceId $Drive

        $bodyObj = @{
            mac_address       = $mac
            message           = "Heartbeat"
            cpu_usage_pct     = $cpu
            memory_usage_pct  = $mem
            disk_usage_pct    = $d.UsedPct
            free_disk_mb      = $d.FreeMB
        }

        $json = $bodyObj | ConvertTo-Json -Depth 4

        $null = Invoke-RestMethod -Uri $Url -Method Post -ContentType "application/json" -Body $json
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] OK | CPU $cpu% | MEM $mem% | DISK $($d.UsedPct)% | Free $($d.FreeMB) MB"
    }
    catch {
        Write-Warning "[$(Get-Date -Format 'HH:mm:ss')] Send failed: $($_.Exception.Message)"
    }

    Start-Sleep -Seconds $PostEverySeconds
}
