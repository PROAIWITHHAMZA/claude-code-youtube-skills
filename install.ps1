# Install the pro-* skills into ~/.claude/skills and the Python packages they use.
#   powershell -ExecutionPolicy Bypass -File install.ps1
$dest = Join-Path $env:USERPROFILE ".claude\skills"
New-Item -ItemType Directory -Force $dest | Out-Null
Get-ChildItem $PSScriptRoot -Directory -Filter "pro-*" | ForEach-Object {
  $target = Join-Path $dest $_.Name
  if (Test-Path $target) { Remove-Item $target -Recurse -Force }
  Copy-Item $_.FullName $target -Recurse
  Get-ChildItem $target -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
  "installed $($_.Name)"
}
python -m pip install --quiet edge-tts pillow imageio-ffmpeg faster-whisper numpy
"done: start a new Claude Code session and type /pro-"
