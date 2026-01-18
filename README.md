# 影片轉換器 (Video Converter)

一個功能完整的影片轉換工具，支援多種硬體加速編碼器，提供現代化的圖形使用者介面。

## 功能特色

- 🚀 **多種硬體加速支援**
  - NVIDIA NVENC (CUDA)
  - Intel Quick Sync Video (QSV)
  - AMD AMF
  - 軟體編碼備援 (libx264)

- 🎯 **自動硬體偵測**
  - 自動偵測系統可用的硬體加速編碼器
  - 智慧選擇最佳編碼器

- 📊 **現代化 UI**
  - 清晰的進度顯示
  - 即時日誌輸出
  - 轉換統計資訊

- ⚙️ **靈活設定**
  - 可自訂解析度、位元率
  - 執行緒數調整
  - 設定儲存/載入

- 🔒 **執行緒安全**
  - 安全的序列號管理
  - 支援多執行緒批次處理

- 📁 **批次處理**
  - 支援多檔案批次轉換
  - 支援資料夾批次處理
  - 可選刪除原始檔案

## 系統需求

- **Python**: 3.7 或更高版本
- **FFmpeg**: 需要安裝 FFmpeg 並在系統 PATH 中
  - 下載: https://ffmpeg.org/download.html
  - Windows: 建議使用 [FFmpeg Windows builds](https://www.gyan.dev/ffmpeg/builds/)

## 安裝

1. 克隆或下載此專案
2. 確保已安裝 Python 3.7+
3. 確保已安裝 FFmpeg 並在系統 PATH 中

```bash
# 檢查 FFmpeg 是否可用
ffmpeg -version
```

## 使用方法

### 基本使用

```bash
python main.py
```

### 功能說明

1. **選擇檔案**
   - 點擊「選擇影片檔案」選擇單個或多個檔案
   - 點擊「選擇資料夾」批次處理資料夾中的所有影片

2. **設定輸出**
   - 點擊「選擇輸出資料夾」指定轉換後的檔案存放位置

3. **調整設定**
   - **寬度/高度**: 設定輸出影片的解析度
   - **位元率**: 設定影片位元率（如: 1000k, 2000k）
   - **編碼器**: 選擇編碼器（auto 為自動選擇最佳編碼器）
   - **執行緒數**: 設定 FFmpeg 使用的執行緒數
   - **刪除原始檔案**: 轉換成功後是否刪除原始檔案

4. **開始轉換**
   - 點擊「開始轉換」開始處理
   - 可隨時點擊「停止轉換」中斷處理

## 專案結構

```
WinApp-VideoPlayer-Converter/
├── video_converter/          # 主套件
│   ├── core/                 # 核心模組
│   │   ├── converter.py      # 轉換器核心
│   │   ├── encoder_detector.py  # 編碼器偵測
│   │   ├── sequence_manager.py  # 序列號管理
│   │   └── config.py         # 配置管理
│   ├── ui/                   # UI 模組
│   │   └── main_window.py    # 主視窗
│   └── utils/                # 工具模組
│       ├── logger.py         # 日誌工具
│       └── file_utils.py    # 檔案工具
├── main.py                   # 程式入口
├── requirements.txt          # 依賴清單
└── README.md                 # 說明文件
```

## 配置檔案

應用程式會自動建立 `config.json` 儲存設定：

```json
{
  "width": 1280,
  "height": 720,
  "bitrate": "1000k",
  "encoder": "auto",
  "threads": 1,
  "timeout": 300,
  "delete_original": true,
  "output_prefix": "av",
  "sequence_file": "sequence_number.txt"
}
```

## 序列號管理

轉換後的檔案會自動命名為 `av0001.mp4`, `av0002.mp4` 等格式。
序列號會儲存在 `sequence_number.txt` 中，確保每次轉換使用連續的序號。

## 硬體加速說明

### NVIDIA NVENC
- 需要 NVIDIA GPU 並支援 NVENC
- 編碼器: `h264_nvenc`
- 通常提供最佳效能

### Intel Quick Sync Video
- 需要 Intel CPU 內建顯示晶片
- 編碼器: `h264_qsv`
- 適合 Intel 處理器使用者

### AMD AMF
- 需要 AMD GPU
- 編碼器: `h264_amf`
- 適合 AMD 顯示卡使用者

### 軟體編碼
- 編碼器: `libx264`
- 作為備援選項，所有系統都支援
- 速度較慢但相容性最佳

## 疑難排解

### FFmpeg 未找到
- 確保 FFmpeg 已正確安裝
- 檢查 FFmpeg 是否在系統 PATH 中
- Windows: 重新啟動命令提示字元或 IDE

### 編碼器不可用
- 檢查硬體是否支援對應的硬體加速
- 確認 FFmpeg 編譯時包含對應的編碼器支援
- 嘗試使用「auto」讓系統自動選擇

### 轉換失敗
- 檢查輸入檔案是否損壞
- 確認輸出資料夾有寫入權限
- 查看日誌區域的錯誤訊息

## 授權

此專案為開源專案，可自由使用和修改。

## 貢獻

歡迎提交 Issue 和 Pull Request！

## 更新日誌

### v1.0.0
- 初始版本
- 支援多種硬體加速編碼器
- 現代化 GUI 介面
- 批次處理功能
- 設定管理系統
