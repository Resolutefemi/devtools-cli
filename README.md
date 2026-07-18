# Renance DevTools (renance-dt) v3.1

<div align="center">
  <h3><a href="https://devtools.pxxl.click">Official Website & Interactive Tutorial</a></h3>
  <p><b>Everything you need in one command.</b></p>

  [![PyPI version](https://img.shields.io/pypi/v/renance-dt.svg)](https://pypi.org/project/renance-dt/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux%20%7C%20Termux-lightgrey)](https://pypi.org/project/renance-dt/)
  [![Built By](https://img.shields.io/badge/Built%20By-Resolutefemi-blue.svg)](mailto:hello@renance.dev)
</div>

---

## What's New in v3.1

- **Live Speed Test** - `dt speed` now works without any external tools, with fast.com-style animated fluctuating display
- **12 New Media Commands** - trim audio, merge audio, audio speed change, video speed change, reverse video, add audio, mute video, watermark, thumbnail extraction, audio/video info
- **Live System Monitor** - `dt sysmon` for continuous real-time CPU/RAM/Disk/Network monitoring with sparklines
- **Animated System Health** - `dt health` now shows live animated bars with sparkline history
- **Enhanced Ping** - `dt ping` now shows animated per-packet results with min/avg/max
- **IP Location** - `dt ip-loc` to get your approximate location from IP
- **Real FFmpeg Progress** - All media commands now show actual conversion progress instead of just a spinner
- **Better Audio Extraction** - `dt music` now supports MP3, WAV, FLAC, AAC, OGG output formats

---

## Quick Start

### 1. Global Installation (Recommended)
```bash
pip install renance-dt
```

### 2. Automatic Setup
```bash
dt setup
```
> **Note:** Please restart your terminal after running setup.

---

## Local Installation (Source Code)

### Windows
1. Open the `dt-cli` directory.
2. Double-click `install.bat` or run: `.\install.bat`

### macOS / Linux / Termux
1. Navigate to the `dt-cli` directory.
2. Run: `chmod +x install.sh && ./install.sh`

---

## 14 Power Categories (220+ Commands)

Run `dt help` to see the full interactive dashboard.

### Files (`dt fcp`, `dt search`, `dt organize`)
- `dt fcp` - Multi-threaded copy engine (up to 5x faster)
- `dt search` - Recursive content search
- `dt clean` - Deep-clean build artifacts

### Media (`dt join`, `dt shrink`, `dt music`, `dt convert`, `dt dm`)
- `dt join` - Merge multiple videos
- `dt shrink` - Compress videos (WhatsApp/Web/HD)
- `dt music` - Extract audio (MP3/WAV/FLAC/AAC/OGG)
- `dt gif` - Video to optimized GIF
- `dt trim-audio` - Cut audio files
- `dt merge-audio` - Join audio files
- `dt audio-speed` - Speed up/slow down audio
- `dt video-speed` - Speed up/slow down video
- `dt reverse-video` - Play video in reverse
- `dt add-audio` - Add/replace audio on video
- `dt mute-video` - Remove audio from video
- `dt watermark` - Add text watermark to video
- `dt thumbnail` - Extract thumbnail from video
- `dt audio-info` / `dt video-info` - Media file details
- `dt convert` - Universal file converter (Audio/Video/Image/SVG/Documents)
- `dt dm` - Download from any social media platform

### Network (`dt speed`, `dt ping`, `dt myip`)
- `dt speed` - Live speed test with animated display (no external tools needed)
- `dt ping` - Animated ping with stats
- `dt sysmon` - Real-time system resource monitor

### Hacker (`dt matrix`, `dt vault`, `dt sniff`)
- `dt matrix` - Falling green code effect
- `dt vault` - Encrypt/Decrypt files
- `dt port-scan` - Network port scanner

### System (`dt health`, `dt sysmon`, `dt info`)
- `dt health` - Live animated health monitor
- `dt sysmon` - Continuous resource monitor with sparklines
- `dt info` - Detailed system information

### Phone (`dt serve-phone`, `dt torch`, `dt sms`)
- `dt serve-phone` - Serve files via QR code
- `dt torch` - Control flashlight (Termux)
- `dt sms` - Send SMS (Termux)

---

## Official Tutorial
For the full interactive command dashboard, visit:
**[devtools.pxxl.click](https://devtools.pxxl.click)**

---
Built with love by **Resolutefemi**
