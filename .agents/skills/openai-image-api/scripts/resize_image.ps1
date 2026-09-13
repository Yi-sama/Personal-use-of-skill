param(
  [Parameter(Mandatory = $true)]
  [string]$InputPath,

  [Parameter(Mandatory = $true)]
  [string]$OutputPath,

  [Parameter(Mandatory = $true)]
  [ValidateRange(1, 100000)]
  [int]$Width,

  [Parameter(Mandatory = $true)]
  [ValidateRange(1, 100000)]
  [int]$Height,

  [ValidateRange(1, 100)]
  [int]$Quality = 95
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Drawing

$inputFull = (Resolve-Path -LiteralPath $InputPath).Path
$outputFull = [System.IO.Path]::GetFullPath($OutputPath)
$outputDir = [System.IO.Path]::GetDirectoryName($outputFull)
if ($outputDir -and -not (Test-Path -LiteralPath $outputDir)) {
  New-Item -ItemType Directory -Path $outputDir | Out-Null
}

$source = [System.Drawing.Image]::FromFile($inputFull)
try {
  $target = [System.Drawing.Bitmap]::new($Width, $Height, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
  try {
    $graphics = [System.Drawing.Graphics]::FromImage($target)
    try {
      $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
      $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
      $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
      $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
      $graphics.DrawImage($source, 0, 0, $Width, $Height)
    } finally {
      $graphics.Dispose()
    }

    $extension = [System.IO.Path]::GetExtension($outputFull).ToLowerInvariant()
    if ($extension -in @('.jpg', '.jpeg')) {
      $encoder = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
      $encoderParams = [System.Drawing.Imaging.EncoderParameters]::new(1)
      $encoderParams.Param[0] = [System.Drawing.Imaging.EncoderParameter]::new([System.Drawing.Imaging.Encoder]::Quality, [int64]$Quality)
      $target.Save($outputFull, $encoder, $encoderParams)
    } elseif ($extension -eq '.png') {
      $target.Save($outputFull, [System.Drawing.Imaging.ImageFormat]::Png)
    } else {
      throw "Unsupported resize output extension: $extension"
    }
  } finally {
    if ($target) {
      $target.Dispose()
    }
  }
} finally {
  $source.Dispose()
}

Write-Output $outputFull
