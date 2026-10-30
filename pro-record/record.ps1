# pro-record: real screen footage for videos, with privacy built in (Windows).
#
#   record.ps1 -Url <url> -Out <mp4> [-Seconds 20] [-Steps "wait:4;keys:{DOWN 6};wait:3;keys:{DOWN 6}"]
#   record.ps1 -Window "<part of a window title>" -Out <mp4> [-Seconds 20] [-Steps ...]
#   options:  -Crop "w:h:x:y"   keep only this part of the capture (physical pixels)
#             -Blur "x:y:w:h,x:y:w:h"   blur boxes (names, emails, paths, other tabs)
#
# -Url opens the page in a fresh Edge InPrivate window (no account, no history, no extensions), records,
# then closes only that window. -Window records just that window's area, so the rest of the desktop
# (notifications, other apps) never lands in the file. -Steps plays scripted input while recording:
#   wait:<seconds>   keys:<SendKeys text>   type:<text>   (separate steps with ;)
# Ends by checking the footage isn't black (a locked or sleeping screen records black).
param([string]$Url, [string]$Window, [Parameter(Mandatory = $true)][string]$Out, [int]$Seconds = 20,
      [string]$Steps = "", [string]$Crop = "", [string]$Blur = "", [int]$Fps = 30)

Add-Type @"
using System; using System.Runtime.InteropServices; using System.Text;
public class ProRec {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  public static IntPtr Find(string part) {
    IntPtr found = IntPtr.Zero;
    EnumWindows((h, l) => { if (!IsWindowVisible(h)) return true; var sb = new StringBuilder(512);
      GetWindowText(h, sb, 512); if (sb.ToString().Contains(part)) { found = h; return false; } return true; }, IntPtr.Zero);
    return found;
  }
}
"@
[ProRec]::SetProcessDPIAware() | Out-Null  # window rectangles in physical pixels, same as the capture

$ff = & python -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"
if (-not $Url -and -not $Window) { "give -Url or -Window"; exit 1 }
$Out = [IO.Path]::GetFullPath($Out)
New-Item -ItemType Directory -Force (Split-Path $Out) | Out-Null
$raw = [IO.Path]::ChangeExtension($Out, ".raw.mp4")

$h = [IntPtr]::Zero
if ($Url) {
  $edge = @("${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe", "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe") |
    Where-Object { Test-Path $_ } | Select-Object -First 1
  if (-not $edge) { "Microsoft Edge not found"; exit 1 }
  Start-Process $edge -ArgumentList '-inprivate', '--start-maximized', '--no-first-run', $Url
  for ($i = 0; $i -lt 20 -and $h -eq [IntPtr]::Zero; $i++) { Start-Sleep -Milliseconds 300; $h = [ProRec]::Find('InPrivate') }
  if ($h -eq [IntPtr]::Zero) { "InPrivate window not found"; exit 1 }
  [ProRec]::ShowWindow($h, 3) | Out-Null
} else {
  $h = [ProRec]::Find($Window)
  if ($h -eq [IntPtr]::Zero) { "no visible window title contains '$Window'"; exit 1 }
}
[ProRec]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 600

$grab = @('-f', 'gdigrab', '-framerate', "$Fps", '-draw_mouse', '1')
if ($Window) {
  $r = New-Object ProRec+RECT
  [ProRec]::GetWindowRect($h, [ref]$r) | Out-Null
  $x = [Math]::Max(0, $r.L + 8); $y = [Math]::Max(0, $r.T)
  $w = ($r.R - 8 - $x) - (($r.R - 8 - $x) % 2); $hh = ($r.B - 8 - $y) - (($r.B - 8 - $y) % 2)  # trim the invisible resize border
  $grab += @('-offset_x', "$x", '-offset_y', "$y", '-video_size', "${w}x${hh}")
}
$rec = Start-Process $ff -ArgumentList (@('-hide_banner', '-loglevel', 'error', '-y') + $grab +
  @('-i', 'desktop', '-t', "$Seconds", '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '16', '-pix_fmt', 'yuv420p', "`"$raw`"")) -PassThru -NoNewWindow

$ws = New-Object -ComObject WScript.Shell
foreach ($step in ($Steps -split ';' | Where-Object { $_.Trim() })) {
  $kind, $arg = $step.Trim() -split ':', 2
  switch ($kind) {
    'wait' { Start-Sleep -Milliseconds ([double]$arg * 1000) }
    'keys' { [ProRec]::SetForegroundWindow($h) | Out-Null; $ws.SendKeys($arg) }
    'type' { [ProRec]::SetForegroundWindow($h) | Out-Null; $ws.SendKeys(($arg -replace '([+^%~(){}\[\]])', '{$1}')) }
  }
}
$rec.WaitForExit()
if ($Url) { [ProRec]::SetForegroundWindow($h) | Out-Null; Start-Sleep -Milliseconds 300; $ws.SendKeys('%{F4}') }

# privacy pass: crop, then blur boxes
$chain = "[0:v]"
if ($Crop) { $c = $Crop -split ':'; $chain += "crop=$($c[0]):$($c[1]):$($c[2]):$($c[3])," }
$chain += "null[base]"
$fc = $chain; $last = "base"; $n = 0
foreach ($b in ($Blur -split ',' | Where-Object { $_.Trim() })) {
  $p = $b.Trim() -split ':'
  $fc += ";[$last]split[s$n][t$n];[t$n]crop=$($p[2]):$($p[3]):$($p[0]):$($p[1]),boxblur=25:3[b$n];[s$n][b$n]overlay=$($p[0]):$($p[1])[o$n]"
  $last = "o$n"; $n++
}
$fc += ";[$last]format=yuv420p[v]"
& $ff -hide_banner -loglevel error -y -i $raw -filter_complex $fc -map '[v]' -c:v libx264 -preset veryfast -crf 18 $Out
if ($LASTEXITCODE -ne 0) { "post-processing failed; raw capture kept at $raw"; exit 1 }
Remove-Item $raw

# black-frame check (a locked or sleeping screen records black)
$mid = [Math]::Max(1, [int]($Seconds / 2))
$lum = & python -c "import subprocess,sys;from PIL import Image,ImageStat;import io;b=subprocess.run([sys.argv[1],'-loglevel','error','-ss',sys.argv[3],'-i',sys.argv[2],'-frames:v','1','-f','image2pipe','-vcodec','png','-'],capture_output=True).stdout;print(round(ImageStat.Stat(Image.open(io.BytesIO(b)).convert('L')).mean[0],1))" $ff $Out $mid
if ([double]$lum -lt 3) { "WARNING: footage is black (mean brightness $lum). Keep the screen awake and unlocked, then record again." }
"recorded $Out (brightness $lum)"
