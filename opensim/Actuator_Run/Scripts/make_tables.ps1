# Builds summary tables (CSV) and chart data (JSON) from the OpenSim run results.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$ResDir = Join-Path $root 'Results'
$T = Join-Path $root 'Tables'
New-Item -ItemType Directory -Force $T | Out-Null
$m = Import-Csv (Join-Path $ResDir 'ALL_conditions_metrics.csv')
function N($v, $d = 2) { [math]::Round([double]$v, $d) }
$alphas = @('0.05', '0.1', '0.125', '0.15', '0.169', '0.2', '0.5')
$base = $m | Where-Object { $_.cond_id -eq 'ACL2mo_Baseline' }

# Table 1: device / actuator
$t1 = foreach ($r in ($m | Where-Object { $_.profile -eq 'delivered' })) {
  [pscustomobject]@{
    Option = $(if ($r.option -eq 'O1') { 'Option 1 (8.43-44%)' } else { 'Option 2 (13-36%, capped)' })
    Bag_pressure_limit = $r.pressure_limit
    alpha = N $r.alpha 3
    Requested_peak_Nm = N $r.requested_peak_Nm
    Delivered_peak_Nm = N $r.peak_device_torque_Nm
    Peak_bag_pressure_kPa = N $r.peak_bag_pressure_kPa 1
    Pressure_needed_for_request_kPa = N $r.pressure_needed_for_request_kPa 1
    Frames_saturated = $r.frames_saturated_at_limit
    Onset_ms = N $r.onset_ms 0
    Onset_torque_Nm = N $r.onset_torque_Nm
    Offset_ms = N $r.offset_ms 0
    Offset_torque_Nm = N $r.offset_torque_Nm
    Torque_impulse_Nms = N $r.torque_impulse_Nms 3
    Device_work_pos_J = N $r.device_work_positive_J 3
    Device_work_neg_J = N $r.device_work_negative_J 3
  }
}
$t1 | Export-Csv (Join-Path $T 'T1_Actuator_delivered.csv') -NoTypeInformation -Encoding UTF8

# Table 2: knee moment (H1 / H2)
$t2 = foreach ($r in ($m | Where-Object { $_.profile -ne 'requested' })) {
  [pscustomobject]@{
    Condition = $r.cond_id; Option = $r.option; Bag_pressure_limit = $r.pressure_limit; alpha = N $r.alpha 3
    Device_at_21pct_Nm = N $r.device_torque_at_21pct_Nm
    Muscle_moment_needed_at_21pct_Nm = N $r.muscle_required_moment_at_21pct_Nm
    Muscle_share_left_H1_pct = N ([double]$r.muscle_share_left_at_21pct_H1 * 100) 1
    Frames_device_above_patient_moment = $r.frames_above_patient_moment
    Frames_muscle_moment_flexor = $r.frames_muscle_moment_flexor_H1
    Lowest_muscle_moment_in_window_Nm = N $r.min_muscle_required_moment_in_window_Nm
    H2_patient_plus_device_peak_Nm = N $r.H2_peak_patient_plus_device_Nm
    H2_pct_of_healthy = N $r.H2_pct_of_healthy 1
  }
}
$t2 | Export-Csv (Join-Path $T 'T2_Knee_moment_H1_H2.csv') -NoTypeInformation -Encoding UTF8

# Table 3: muscles
$t3 = foreach ($r in ($m | Where-Object { $_.profile -ne 'requested' })) {
  [pscustomobject]@{
    Condition = $r.cond_id; Option = $r.option; Bag_pressure_limit = $r.pressure_limit; alpha = N $r.alpha 3
    Quad_at_21pct_N = N $r.quad_force_at_21pct_N 1
    Quad_at_21pct_change_pct = N (-[double]$r.quad_at_21pct_reduction_pct) 1
    Quad_peak_in_window_N = N $r.quad_force_peak_in_window_N 1
    Quad_window_impulse_change_pct = N (-[double]$r.quad_window_impulse_reduction_pct) 1
    Quad_activation_window_change_pct = N (-[double]$r.quad_activation_window_reduction_pct) 1
    Hamstrings_peak_in_window_N = N $r.hamstring_force_peak_in_window_N 1
    Hamstrings_change_N = N $r.hamstring_change_in_window_N 1
    Gastrocnemius_peak_in_window_N = N $r.gastrocnemius_force_peak_in_window_N 1
    All_knee_muscles_peak_in_window_change_pct = N $r.all_knee_muscle_change_pct 1
    Max_reserve_Nm = N $r.max_abs_reserve_Nm 4
  }
}
$t3 | Export-Csv (Join-Path $T 'T3_Muscles_quadriceps_hamstrings.csv') -NoTypeInformation -Encoding UTF8

# Chart data
$conds = @('ACL2mo_Baseline') + ($m | Where-Object { $_.profile -ne 'no device' } | ForEach-Object { $_.cond_id })
$series = [ordered]@{}
foreach ($c in $conds) {
  $s = Import-Csv (Join-Path $ResDir "$($c)_SO_summary.csv")
  $series[$c] = [ordered]@{
    tau  = @($s | ForEach-Object { N $_.device_torque_Nm 3 })
    quad = @($s | ForEach-Object { N $_.F_quadriceps_N 1 })
    ham  = @($s | ForEach-Object { N $_.F_hamstrings_N 1 })
    gas  = @($s | ForEach-Object { N $_.F_gastrocnemius_N 1 })
    mbio = @($s | ForEach-Object { N $_.muscle_required_moment_H1_Nm 3 })
  }
}
$w = Import-Csv (Join-Path $ResDir 'input_waveforms_2months.csv')
$h = Import-Csv (Join-Path $ResDir 'Healthy_Baseline_SO_summary.csv')
$data = [ordered]@{
  pct = @($w | ForEach-Object { N $_.pct_stance 2 })
  patient = @($w | ForEach-Object { N $_.patient_moment_Nm 3 })
  healthy = @($w | ForEach-Object { N $_.healthy_moment_Nm 3 })
  deficit = @($w | ForEach-Object { N $_.deficit_Nm 3 })
  flex = @($w | ForEach-Object { N $_.knee_flexion_deg 2 })
  healthyQuad = @($h | ForEach-Object { N $_.F_quadriceps_N 1 })
  series = $series
  metrics = @($m | ForEach-Object { $o = [ordered]@{}; foreach ($p in $_.PSObject.Properties) { $v = 0.0; if ([double]::TryParse($p.Value, [ref]$v)) { $o[$p.Name] = [math]::Round($v, 4) } else { $o[$p.Name] = $p.Value } }; $o })
}
($data | ConvertTo-Json -Depth 6 -Compress) | Set-Content (Join-Path $T 'chart_data.json') -Encoding UTF8
"tables written: " + (Get-ChildItem $T | ForEach-Object { $_.Name + ' (' + $_.Length + ' B)' }) -join ', '

