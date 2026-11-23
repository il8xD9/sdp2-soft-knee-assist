# Inlines chart_data.json into the report template -> OpenSim_Actuator_Report.html
$root = $PSScriptRoot
$tpl = Get-Content (Join-Path $root 'report_template.html') -Raw -Encoding UTF8
$json = Get-Content (Join-Path $root 'Tables\chart_data.json') -Raw -Encoding UTF8
$out = $tpl.Replace('/*__DATA__*/null', $json.Trim())
[IO.File]::WriteAllText((Join-Path $root 'OpenSim_Actuator_Report.html'), $out, (New-Object Text.UTF8Encoding($false)))
"written " + (Get-Item (Join-Path $root 'OpenSim_Actuator_Report.html')).Length + " bytes"
