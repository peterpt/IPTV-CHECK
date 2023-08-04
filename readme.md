# IPTV-CHECK 2.1 Beta

Iptv-check allows you to input a valid iptv file (m3u) to be checked if the video streams are still working or not .
In case valid urls were found , then the script will create a new iptv (m3u) file with those urls .
Version 2 will check valid online streams if there is a bad login on that streaming channel , sometimes streaming is on
but if there is a bad login it will pop up a login message . OCR detection was added for double check valid streams .

# Screenshots
<img src="https://i.postimg.cc/q7yQ6LTz/iptv.png" width="55%"></img>

<img src="https://s14.postimg.cc/grelrf6gx/icheck2.png" width="40%"></img><img src="https://s14.postimg.cc/we5v4szoh/CHECK_034.png" width="40%"></img>

# Requirements

- wget ffmpeg tesseract-ocr libtesseract-dev tesseract-ocr-eng

# Install Requirements

- apt install wget ffmpeg tesseract-ocr libtesseract-dev tesseract-ocr-eng

# Tool Instalation

- git clone https://github.com/peterpt/IPTV-CHECK.git && cd IPTV-CHECK && ./iptv-check

# New Implementations
 - Iptv-check rellies now on ffmpeg to download streams instead wget , new filters added to clean some iptv lists 
