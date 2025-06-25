# 🎤 Hassaniya Platform

A complete web platform for Hassaniya Arabic recording, normalization, and data collection with user authentication.

## ✨ Features

- **🔑 User Authentication**: Login system for authorized users (EMIN, ETHMAN, ZAIN, MOUHAMEDOU)
- **🎙️ Audio Recording**: Record Hassaniya Arabic speech with web interface
- **📝 Text Normalization**: Convert Hassaniya variants to standardized forms
- **📊 User Statistics**: Track individual progress and transcription minutes
- **📦 Data Export**: Export recordings and statistics for ML training
- **🔄 Text Management**: Upload and manage text corpus for recording
- **👥 Multi-user Support**: Individual progress tracking for each user

## 🚀 Quick Start

### Requirements
- Python 3.9+
- Modern web browser with microphone access

### Installation & Startup

1. **Clone or download the project**
2. **Install dependencies:**
   ```bash
   pip install fastapi uvicorn pydantic pathlib
   ```
3. **Start the server:**
   ```bash
   python server.py
   # OR use startup scripts
   start.bat        # Windows
   ./start.sh       # Linux/macOS
   ```
4. **Access the platform:**
   - Open your browser to `http://localhost:8002`
   - Login with one of the authorized usernames
   - Start recording!

## 👥 Authorized Users

- **EMIN**
- **ETHMAN**
- **ZAIN**
- **MOUHAMEDOU**

## 📁 Project Structure

```
hassaniya-platform/
├── server.py                     # Main unified server
├── start.bat / start.sh         # Startup scripts
├── data/
│   └── audio/                   # Recorded audio files
├── src/hassy_normalizer/        # Normalization engine
│   ├── normalizer.py           # Core normalization
│   ├── rules.py                # Normalization rules
│   ├── diff.py                 # Diff utilities
│   └── data/                   # Variant data files
├── tests/                      # Test suite
├── README.md                   # This file
└── pyproject.toml             # Python project config
```

## 🎯 How It Works

1. **Login**: Enter your username to access the platform
2. **Record**: Get assigned text segments to record
3. **Submit**: Upload your audio recording with optional text edits
4. **Track**: View your progress and statistics
5. **Export**: Download datasets for ML training (includes audio + metadata)

## 📊 Features Available

### 🎙️ Recorder Tab
- Load next text to record
- Start/stop audio recording
- Submit recordings with edited text
- Skip paragraphs if needed

### 📝 Normalizer Tab
- Input Hassaniya text for normalization
- View normalized output
- See word-level differences

### ⚙️ Admin Tab
- Upload text files for recording
- Export recordings as ZIP files
- Export statistics and user data
- Report text variants for improvement

### 📈 Statistics Tab
- View platform-wide statistics
- See individual user progress
- Track recording minutes and completion rates

## 🔧 API Endpoints

- `GET /` - Login page
- `GET /dashboard` - Main platform interface
- `GET /api/para/next` - Get next paragraph to record
- `POST /api/para/{id}/submit` - Submit recorded paragraph
- `POST /api/text/upload` - Upload text files
- `GET /api/export/recordings` - Export recordings dataset
- `GET /api/export/statistics` - Export statistics
- `GET /api/audio/{filename}` - Serve audio files

## 💾 Data Export

The platform exports data in ML-ready formats:

### Recordings Export
- `transcriptions.jsonl` - Metadata in JSONL format (Whisper-compatible)
- `recordings/` - Audio files in WebM format
- `README.md` - Usage documentation

### Statistics Export
- `statistics.json` - Complete system statistics
- `user_statistics.json` - Per-user activity data
- `variant_reports.json` - User-reported text variants

## 🎛️ Local Development

The platform uses in-memory storage for simplicity - no external database required. All data persists during the server session.

### Customization
- Edit authorized users in `server.py` (USERS list)
- Modify normalization rules in `src/hassy_normalizer/rules.py`
- Adjust UI styling in the HTML templates within `server.py`

## 📝 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

This is a self-contained platform designed for Hassaniya Arabic data collection. Contributions welcome for:
- Additional normalization rules
- UI improvements
- Export format enhancements
- User experience optimizations

---

**Built for the Hassaniya Arabic community** 🇲🇷
