# 📺 IPTV-CHECK v3.0

[![Python](https://img.shields.io/badge/Language-Python%203-3776AB?style=flat-square&logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey?style=flat-square)](#)

**IPTV-CHECK** is an advanced, high-performance Python application designed to automatically test and clean IPTV playlists (`.m3u` / `.m3u8`). It filters out dead, offline, or broken streams and generates a brand new, fully working playlist. 

It features both a robust **Graphical User Interface (GUI)** and a fast **Command-Line Interface (CLI)**, making it perfect for both casual users and server automation.

---
## Checking url with m3u
<img width="1024" height="741" alt="image" src="https://github.com/user-attachments/assets/827745f4-6237-4404-beb3-4a87af7412ce" />

## Checking current iptv lists in urls database 
<img width="908" height="741" alt="image" src="https://github.com/user-attachments/assets/cc0c768e-bc1b-4b1a-8096-168db10a7cbb" />

## CLI mode
<img width="1024" height="741" alt="image" src="https://github.com/user-attachments/assets/0794bb3f-29ba-41a5-a901-858065e261d8" />

## 🌟 Key Features

* **🖥️ Dual Mode:** Run via an intuitive Graphical Interface (GUI) or a powerful Command-Line Interface (CLI).
* **🧠 Smart OCR Error Detection:** Uses Tesseract OCR to read video frames and detect "fake" active streams (e.g., Geo-blocked screens, "Login Required", or "Access Denied" video loops).
* **⚡ Multi-threaded Workers:** Checks multiple streams simultaneously for lightning-fast processing.
* **▶️ YouTube Support:** Built-in `yt-dlp` integration to resolve and check YouTube-based IPTV streams.
* **⏭️ Smart Skipping:** Automatically skips URLs that have already been verified in your output file, saving massive amounts of time on re-checks.
* **🌐 Website M3U Scraper:** Built-in tool to scrape web pages for M3U links and save them to a local database.
* **🌍 Multi-Language Support:** GUI translated into English, Portuguese, Spanish, French, Italian, German, Russian, and Chinese.
* **🔄 Auto-Update:** Built-in Git updater straight from the GUI.

---

## 🛠️ Prerequisites & Installation

Because IPTV-CHECK interacts with video streams and images, it relies on standard system media tools as well as Python libraries.

### 1. Install System Dependencies
Ensure you have the following installed on your operating system:
* `ffmpeg` & `ffprobe` (Essential for stream testing)
* `yt-dlp` (Essential for YouTube links)
* `tesseract-ocr` (Optional, but required if you want to use the OCR Smart Check feature)
* `git` (For in-app updating)

**For Debian / Ubuntu / Linux Mint:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-tk ffmpeg tesseract-ocr git -y
sudo wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O /usr/local/bin/yt-dlp
sudo chmod a+rx /usr/local/bin/yt-dlp

2. Install Python Dependencies

Clone the repository and install the required Python libraries.
code Bash

git clone https://github.com/peterpt/IPTV-CHECK.git
cd IPTV-CHECK
pip3 install requests Pillow pytesseract colorama

🚀 Usage
Graphical User Interface (GUI)

To launch the visual application, simply run:
code Bash

python3 iptv_check.py --gui

From the GUI, you can browse for your M3U files, configure timeouts, manage your database of default links, scrape websites, and watch the live log.
Command-Line Interface (CLI)

For headless servers or automation, use the CLI.

Basic check of a local file:
code Bash

python3 iptv_check.py -f my_playlist.m3u -o working_streams.m3u

Check a URL directly with 15 parallel workers:
code Bash

python3 iptv_check.py -f "http://example.com/playlist.m3u" -w 15

Re-check an existing output file and use OCR to detect error screens:
code Bash

python3 iptv_check.py -r working_streams.m3u --ocr

CLI Help Menu:
code Bash

python3 iptv_check.py --help

🏆 Credits

    Project Leader & Creator: peterpt

    Code Assistance by: Gemini Pro Model

📄 License

This project is licensed under the MIT License.

## Old versions can be downloaded in :

    https://github.com/peterpt/IPTV-CHECK/releases

