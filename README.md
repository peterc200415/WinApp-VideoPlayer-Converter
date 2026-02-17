# Video Converter

A full-featured video conversion tool with hardware acceleration support and modern GUI.

## Features

- **Hardware Acceleration**
  - NVIDIA NVENC (CUDA) - H.264 & H.265/HEVC
  - Intel Quick Sync Video (QSV) - H.264 & H.265/HEVC
  - AMD AMF - H.264 & H.265/HEVC
  - Software encoding fallback (libx264, libx265)

- **Smart Detection**
  - Auto-detect available hardware encoders
  - Auto-check NVIDIA driver compatibility
  - Intelligent encoder selection

- **Modern UI**
  - Dual progress bars (overall + per-file)
  - Real-time progress: percent, elapsed, speed, ETA
  - Source video info (container, codec, resolution, duration)
  - Live log output
  - CPU / GPU / RAM live utilization (Windows best-effort)
  - Batch conversion statistics

- **Flexible Settings**
  - Resolution presets (4K, 1080p, 900p, 720p, 480p, 360p)
  - Custom width/height input
  - Bitrate or CRF quality mode
  - Preset speed (ultrafast to veryslow)
  - Thread count adjustment
  - Settings persistence

- **Output**
  - Filename format: `av-{height}p-{seq}.mp4` (e.g., av-720p-0001.mp4)
  - Auto-increment sequence number

## Requirements

- **Python**: 3.7 or higher
- **FFmpeg**: Required (built-in support for this app)
  - Download: https://ffmpeg.org/download.html
  - Windows: Recommended [FFmpeg Windows builds](https://www.gyan.dev/ffmpeg/builds/)

## Installation

1. Clone or download this project
2. Ensure Python 3.7+ is installed
3. FFmpeg is included with this app

## Usage

```bash
python main.py
```

### Feature Guide

1. **Select Files**
   - Click "Select Files" to choose one or multiple video files
   - Click "Select Folder" to batch process all videos in a folder

2. **Output Folder**
   - Set output folder in the **Input Files** section (Choose...)

3. **Conversion Settings**
   - **Resolution**: Choose from presets (4K, 1080p, 900p, 720p, 480p, 360p) or enter custom WxH
   - **Bitrate**: Set video bitrate (e.g., 1000k, 2000k)
   - **Use CRF Quality Mode**: Enable for quality-based encoding (0-51, lower = better quality)
   - **Encoder**: Select encoder (auto for automatic best selection)
     - HEVC (H.265): ~50% smaller than H.264
     - H.264: Best compatibility
   - **Preset**: Encoding speed (ultrafast to veryslow)
   - **Threads**: FFmpeg thread count
   - **Delete original**: Option to delete source file after successful conversion

4. **Start Conversion**
   - Click "Start Conversion" to begin processing
   - Click "Stop" to interrupt at any time

## Project Structure

```
WinApp-VideoPlayer-Converter/
├── video_converter/          # Main package
│   ├── core/                 # Core modules
│   │   ├── converter.py      # Converter core
│   │   ├── encoder_detector.py  # Encoder detection
│   │   ├── sequence_manager.py  # Sequence management
│   │   └── config.py         # Config management
│   ├── ui/                   # UI module
│   │   └── main_window.py   # Main window
│   └── utils/                # Utilities
│       ├── logger.py         # Logger
│       └── file_utils.py     # File utilities
├── main.py                   # Program entry
├── requirements.txt          # Dependencies
└── README.md                 # Documentation
```

## Configuration File

The app automatically creates `config.json` to store settings:

```json
{
  "width": 1280,
  "height": 720,
  "bitrate": "1000k",
  "encoder": "auto",
  "threads": 1,
  "timeout": 300,
  "delete_original": true,
  "preset": "medium",
  "use_crf": false,
  "crf": 23,
  "sequence_file": "sequence_number.txt"
}
```

## Hardware Acceleration Guide

### HEVC (H.265) vs H.264

| Codec | Size | Quality | Speed | Compatibility |
|-------|------|---------|-------|---------------|
| H.264 | Standard | Good | Fast | Best |
| HEVC | ~50% smaller | Good | Fast | Good (requires HEVC support) |

### NVIDIA NVENC
- Requires NVIDIA GPU with NVENC support
- Encoders: `h264_nvenc`, `hevc_nvenc`
- Minimum driver: 570.0+

### Intel Quick Sync Video
- Requires Intel CPU with integrated graphics
- Encoders: `h264_qsv`, `hevc_qsv`

### AMD AMF
- Requires AMD GPU
- Encoders: `h264_amf`, `hevc_amf`

### Software Encoding
- Encoders: `libx264`, `libx265`
- Fallback option, works on all systems
- Slower but maximum compatibility

## Troubleshooting

### FFmpeg Not Found
- FFmpeg is included with this app
- If issues persist, ensure FFmpeg is in system PATH

### Encoder Not Available
- Check if hardware supports the encoder
- Try using "auto" for automatic selection

### Conversion Failed
- Check input file is not corrupted
- Verify output folder has write permissions
- Check error details in log area

### Progress Looks Stuck
- The per-file bar switches to an indeterminate state until FFmpeg reports progress.
- If the input duration cannot be detected, ETA/percent may be unavailable.

### CPU/GPU Utilization Seems Wrong
- RAM is read from Windows API.
- CPU/GPU are best-effort and depend on Windows performance counters / drivers.
- NVIDIA GPUs use `nvidia-smi` when available.

### NVIDIA Driver Issue
- If NVENC fails, update NVIDIA driver to 570.0 or newer
- Or use AMD/Intel hardware acceleration instead

## License

Open source project - free to use and modify.

## Contributing

Issues and Pull Requests are welcome!

## Changelog

### v1.1.0
- Added HEVC (H.265) encoder support
- Added preset speed options (ultrafast to veryslow)
- Added CRF quality mode
- Added resolution presets dropdown
- Added progress percentage display
- Added source video format display
- Changed output filename format to include height (av-720p-0001.mp4)
- UI language: English

### v1.2.0
- UI redesign (compact, professional layout)
- Output folder moved into Input Files section
- Dual progress bars (overall + per-file) with real-time speed/ETA
- Source file selection info now includes duration
- Live CPU/GPU/RAM utilization in the header
- Added 900p (1600x900) preset

### v1.0.0
- Initial release
- Multi-hardware acceleration support (NVENC, QSV, AMF)
- Modern GUI interface
- Batch processing
- Settings management system
