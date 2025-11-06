# IPTV-Check v3.0

## Checking url with m3u
<img width="1024" height="741" alt="image" src="https://github.com/user-attachments/assets/827745f4-6237-4404-beb3-4a87af7412ce" />

## Checking current iptv lists in urls database 
<img width="908" height="741" alt="image" src="https://github.com/user-attachments/assets/cc0c768e-bc1b-4b1a-8096-168db10a7cbb" />

## CLI mode
<img width="1024" height="741" alt="image" src="https://github.com/user-attachments/assets/0794bb3f-29ba-41a5-a901-858065e261d8" />

## Description
IPTV-Check is a powerful, cross-platform tool for validating M3U playlists. Originally a popular Bash script, v3.0 is a complete architectural rewrite in Python, offering a full Graphical User Interface (GUI), high-performance parallel stream checking, and advanced validation features.

It reads an M3U playlist from a local file or URL, checks each stream to see if it's online, and saves the working streams to a new, clean M3U file.

* Key Features

This is a major upgrade from the previous Bash version, designed for speed, accuracy, and user-friendliness.

    Dual Mode Operation

        GUI Mode: A user-friendly graphical interface for easy, intuitive operation.

        CLI Mode: A powerful command-line interface perfect for automation and scripting.

* High-Performance Concurrency

Utilizes multiple workers to check dozens of streams in parallel, dramatically reducing the time it takes to validate large playlists from hours to minutes.

    Advanced OCR Validation

        (Optional) Uses Tesseract OCR to analyze a video frame from each stream. This unique feature detects "soft" errors like login prompts, geo-blocks, or on-screen error messages that a simple connection check would miss, ensuring a higher quality final playlist.

    Built-in GUI Tools

        Website M3U Finder: Scans any website URL to automatically discover and validate direct links to .m3u and .m3u8 playlists.

        Links Database Manager: Create, save, and manage a personal database of your favorite M3U playlist URLs for quick access and checking.

    Efficient & Smart Checking

        Skip Duplicates: To speed up processing new lists, the app can read your existing output file and skip checking any streams that are already known to be good.

        YouTube Support: Automatically resolves youtube.com links to their direct, playable stream URLs using yt-dlp.

        Uncheckable Filter: Intelligently isolates streams with temporary tokens, signatures, or authentication keys into a separate uncheckable.m3u file for manual review.

    Cross-Platform & Multilingual

        Fully compatible with Windows, macOS, and Linux.

        The GUI is available in 8 languages (EN, PT, ES, FR, IT, DE, RU, ZH), with a simple structure to support more translations.

Requirements
## 1. External Dependencies

The following command-line tools must be installed on your system and accessible in your system's PATH for the application to function.

 apt install git ffmpeg yt-dlp python3-tk tesseract-ocr libtesseract-dev tesseract-ocr-en

 Git: (Optional) Required for using the self-updating feature from the GUI's "About" menu.

2. Python Dependencies

The script requires Python 3.7+ and several third-party libraries. You can install them using the provided requirements.txt file. The required libraries are:

    requests
    Pillow
    pytesseract
    colorama

## Installation

    Clone the repository to your local machine:
    code Bash

    
git clone https://github.com/peterpt/iptv-check.git
cd iptv-check

  

 - Install the required Python3 libraries using pip:

        
    pip install -r requirements.txt

   Ensure all External Dependencies are installed correctly and that their locations are in your system's PATH.

Usage
GUI Mode (Recommended)

For the best and most user-friendly experience, run the application with the --gui flag.
code Bash

    
python3 iptv_check.py --gui

  

The graphical interface provides easy access to all features, including the Website Finder and Links Database. Tooltips are available for all major options to guide you.
Command-Line (CLI) Mode

For automation, scripting, or use in a server environment, the CLI provides full access to the core checking functionality.

Basic Examples:
code Bash

    
# Check a remote URL and save working streams to updated.m3u
python3 iptv_check.py -f "http://example.com/playlist.m3u"

# Check a local file and specify a different output file
python3 iptv_check.py -f "/path/to/your/playlist.m3u" -o "my_checked_list.m3u"

# Re-check an existing output file to clean out any links that have gone offline
python3 iptv_check.py -r "my_checked_list.m3u"

# Check all playlists stored in your personal links database
python3 iptv_check.py -d

  

Advanced Example:
    
# Use 20 workers, a 10-second timeout, and enable OCR checking for the highest quality results
python3 iptv_check.py -f "playlist.m3u" -w 20 -t 10 --ocr

  

All CLI Arguments:
code Code

    
-h, --help            Show the help message and exit.
  -gui, --gui           Launch the graphical user interface.

CLI Input Options (choose one):
  -f FILE, --file FILE  Path or URL to the M3U playlist file.
  -d, --database        Use the default links database as input.
  -r RECHECK, --recheck RECHECK
                        Re-check an existing output file (e.g., updated.m3u).

CLI General Options:
  -o OUTPUT, --output OUTPUT
                        Output file for working streams (default: updated.m3u).
  -w WORKERS, --workers WORKERS
                        Number of parallel workers (1-20) (default: 10).
  -t TIMEOUT, --timeout TIMEOUT
                        Network timeout in seconds for each stream (default: 5).
  --log-format {name,url}
                        Log output format for the CLI (default: name).
  --ocr                 Enable OCR checking for video streams.
  --no-skip             Disable skipping of known good URLs.

  

Configuration

The application will automatically create the following configuration files in its directory on the first run:

    iptv_checker_config.ini: Stores your settings, such as language preference, the path to an external media player (for the GUI), and stream pattern definitions.

    iptv_checker_links.ini: Stores the URLs for the Links Database feature.

License

This project is licensed under the MIT License.
Credits

    Project Leader & Creator: peterpt

    Code Assistance by: Gemini Pro Model
