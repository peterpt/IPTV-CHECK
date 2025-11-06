#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import re
import subprocess
import tempfile
import threading
import signal
import shutil
from urllib.parse import urlparse, urljoin
import argparse
import logging
import configparser
from pathlib import Path
import time
import json

# --- Third-party libraries ---
import requests
try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow library not found. Please install it: pip install Pillow")
try:
    import pytesseract
except ImportError:
    sys.exit("pytesseract library not found. Please install it: pip install pytesseract")
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class Fore: RED = ''; GREEN = ''; YELLOW = ''; BLUE = ''; CYAN = ''; RESET = ''
    class Style: BRIGHT = ''; RESET_ALL = ''

# --- GUI Components ---
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, scrolledtext, messagebox, simpledialog
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

# --- Configuration & Constants ---
VERSION = "3.0" # Add granular UI lock during processing
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
AUDIO_USER_AGENT = "iTunes/9.1.1"
MIN_FILE_SIZE_BYTES = 100
DEFAULT_CAPTURE_DURATION = 4
OCR_FRAME_EXTRACTION_TIMEOUT = 20
WORKER_PROCESS_TIMEOUT_SECONDS = 30
UNCHECKABLE_URL_LENGTH_THRESHOLD = 250
UNCHECKABLE_KEYWORDS = ['token', 'auth', 'login', 'key', 'signature']
TEMP_FILE_PREFIX = "iptv-check-temp-"
YT_DLP_TIMEOUT_SECONDS = 20

# --- Portable File Paths ---
APP_DIR = Path(__file__).resolve().parent
CONFIG_FILE_PATH = APP_DIR / "iptv_checker_config.ini"
LINKS_DB_PATH = APP_DIR / "iptv_checker_links.ini"
DEBUG_LOG_PATH = APP_DIR / "debug.log"

# --- Language/Internationalization ---
LANGUAGES = {}
DEFAULT_LANG = "en"

def load_languages():
    global LANGUAGES
    LANGUAGES = {
        "en": {
            "title": "IPTV-Check", "file": "File", "recheck_output": "Recheck Output File", "exit": "Exit",
            "tools": "Tools", "website_finder": "Website M3U Finder...", "database": "Database",
            "manage_links": "Manage Default Links...", "check_all_links": "Check All Default Links", "settings": "Settings",
            "configure": "Configure...", "language": "Language", "debug": "Debug", "view_log": "View Debug Log",
            "about_menu": "About", "creators": "Creators...", "update": "Update...", "m3u_input_label": "M3U File or URL:",
            "output_file_label": "Output File:", "browse": "Browse...", "start_check": "Start Check",
            "stop_save": "Stop & Save", "timeout_label": "Timeout (s):", "workers_label": "Workers:",
            "remaining_label": "Remaining:", "log_display_label": "Log Display", "channel_name_radio": "Channel Name",
            "channel_url_radio": "Channel URL", "options_label": "Options", "use_ocr_check": "Use OCR",
            "skip_known_check": "Skip Known Good URLs", "search_label": "Search in Output File...",
            "no_internet": "No Internet Connection. Waiting for connection...",
            "tooltip_ocr": "If checked, uses OCR (Tesseract) to analyze a frame from video streams.\nThis helps detect error screens (e.g., 'Login required', geo-blocked).\nThis check is slower.",
            "tooltip_timeout": "Network timeout in seconds for each stream check.", "tooltip_workers": "Number of parallel checks to run at once.",
            "tooltip_log_display": "Changes the display format in the log view during a check.",
            "tooltip_skip_known": "If checked, the app will read your output file first.\nAny stream URL from the new source that already exists in the output file will be skipped.\nThis prevents duplicates and speeds up checking large lists.",
            "tooltip_channel_name": "In the log window, display the channel's name from the M3U file.",
            "tooltip_channel_url": "In the log window, display the full URL of the channel's stream."
        },
        "pt": {
            "title": "IPTV-Check", "file": "Arquivo", "recheck_output": "Verificar Novamente Arquivo de Saída", "exit": "Sair",
            "tools": "Ferramentas", "website_finder": "Localizador de M3U em Websites...", "database": "Base de Dados",
            "manage_links": "Gerir Links Padrão...", "check_all_links": "Verificar Todos os Links Padrão", "settings": "Definições",
            "configure": "Configurar...", "language": "Idioma", "debug": "Depuração", "view_log": "Ver Registo de Depuração",
            "about_menu": "Sobre", "creators": "Criadores...", "update": "Atualizar...", "m3u_input_label": "Arquivo M3U ou URL:",
            "output_file_label": "Arquivo de Saída:", "browse": "Procurar...", "start_check": "Iniciar Verificação",
            "stop_save": "Parar e Salvar", "timeout_label": "Timeout (s):", "workers_label": "Workers:",
            "remaining_label": "Restantes:", "log_display_label": "Exibição do Registo", "channel_name_radio": "Nome do Canal",
            "channel_url_radio": "URL do Canal", "options_label": "Opções", "use_ocr_check": "Usar OCR",
            "skip_known_check": "Ignorar URLs já existentes", "search_label": "Pesquisar no Arquivo de Saída...",
            "no_internet": "Sem Conexão à Internet. Aguardando conexão...",
            "tooltip_ocr": "Se marcado, usa OCR (Tesseract) para analisar um frame dos streams de vídeo.\nAjuda a detetar ecrãs de erro (ex: 'Login necessário', bloqueio geográfico).\nEsta verificação é mais lenta.",
            "tooltip_timeout": "Tempo limite de rede em segundos para cada verificação de stream.", "tooltip_workers": "Número de verificações paralelas a serem executadas de uma vez.",
            "tooltip_log_display": "Altera o formato de exibição na vista de registo durante uma verificação.",
            "tooltip_skip_known": "Se marcado, a aplicação lerá primeiro o seu arquivo de saída.\nQualquer URL de stream da nova fonte que já exista no arquivo de saída será ignorado.\nIsto evita duplicados e acelera a verificação de listas grandes.",
            "tooltip_channel_name": "Na janela de registo, exibir o nome do canal do arquivo M3U.",
            "tooltip_channel_url": "Na janela de registo, exibir o URL completo do stream do canal."
        },
        "es": {
            "title": "IPTV-Check", "file": "Archivo", "recheck_output": "Revisar Archivo de Salida", "exit": "Salir",
            "tools": "Herramientas", "website_finder": "Buscador de M3U en Sitios Web...", "database": "Base de Datos",
            "manage_links": "Gestionar Enlaces Predeterminados...", "check_all_links": "Revisar Todos los Enlaces Predeterminados", "settings": "Ajustes",
            "configure": "Configurar...", "language": "Idioma", "debug": "Depuración", "view_log": "Ver Registro de Depuración",
            "about_menu": "Acerca de", "creators": "Creadores...", "update": "Actualizar...", "m3u_input_label": "Archivo M3U o URL:",
            "output_file_label": "Archivo de Salida:", "browse": "Explorar...", "start_check": "Iniciar Revisión",
            "stop_save": "Detener y Guardar", "timeout_label": "Timeout (s):", "workers_label": "Workers:",
            "remaining_label": "Restantes:", "log_display_label": "Visualización del Registro", "channel_name_radio": "Nombre del Canal",
            "channel_url_radio": "URL del Canal", "options_label": "Opciones", "use_ocr_check": "Usar OCR",
            "skip_known_check": "Omitir URLs conocidas", "search_label": "Buscar en Archivo de Salida...",
            "no_internet": "Sin Conexión a Internet. Esperando conexión...",
            "tooltip_ocr": "Si está marcado, usa OCR (Tesseract) para analizar un fotograma de los flujos de video.\nAyuda a detectar pantallas de error (ej: 'Se requiere inicio de sesión', geobloqueado).\nEsta revisión es más lenta.",
            "tooltip_timeout": "Tiempo de espera de red en segundos para cada revisión de flujo.", "tooltip_workers": "Número de revisiones paralelas para ejecutar a la vez.",
            "tooltip_log_display": "Cambia el formato de visualización en la vista de registro durante una revisión.",
            "tooltip_skip_known": "Si está marcado, la aplicación leerá primero su archivo de salida.\nCualquier URL de flujo de la nueva fuente que ya exista en el archivo de salida será omitida.\nEsto evita duplicados y acelera la revisión de listas grandes.",
            "tooltip_channel_name": "En la ventana de registro, mostrar el nombre del canal del archivo M3U.",
            "tooltip_channel_url": "En la ventana de registro, mostrar la URL completa del flujo del canal."
        },
        "fr": {
            "title": "IPTV-Check", "file": "Fichier", "recheck_output": "Revérifier le Fichier de Sortie", "exit": "Quitter",
            "tools": "Outils", "website_finder": "Chercheur de M3U sur Site Web...", "database": "Base de Données",
            "manage_links": "Gérer les Liens par Défaut...", "check_all_links": "Vérifier Tous les Liens par Défaut", "settings": "Paramètres",
            "configure": "Configurer...", "language": "Langue", "debug": "Débogage", "view_log": "Voir le Journal de Débogage",
            "about_menu": "À propos", "creators": "Créateurs...", "update": "Mettre à jour...", "m3u_input_label": "Fichier M3U ou URL :",
            "output_file_label": "Fichier de Sortie :", "browse": "Parcourir...", "start_check": "Démarrer la Vérification",
            "stop_save": "Arrêter et Enregistrer", "timeout_label": "Timeout (s) :", "workers_label": "Workers :",
            "remaining_label": "Restants :", "log_display_label": "Affichage du Journal", "channel_name_radio": "Nom de la Chaîne",
            "channel_url_radio": "URL de la Chaîne", "options_label": "Options", "use_ocr_check": "Utiliser l'OCR",
            "skip_known_check": "Ignorer les URL connues", "search_label": "Rechercher dans le Fichier de Sortie...",
            "no_internet": "Pas de Connexion Internet. En attente de connexion...",
            "tooltip_ocr": "Si coché, utilise l'OCR (Tesseract) pour analyser une image des flux vidéo.\nCela aide à détecter les écrans d'erreur (ex: 'Connexion requise', géo-bloqué).\nCette vérification est plus lente.",
            "tooltip_timeout": "Délai d'attente réseau en secondes pour chaque vérification de flux.", "tooltip_workers": "Nombre de vérifications parallèles à exécuter en même temps.",
            "tooltip_log_display": "Change le format d'affichage dans la vue du journal pendant une vérification.",
            "tooltip_skip_known": "Si coché, l'application lira d'abord votre fichier de sortie.\nToute URL de flux de la nouvelle source qui existe déjà dans le fichier de sortie sera ignorée.\nCela évite les doublons et accélère la vérification des grandes listes.",
            "tooltip_channel_name": "Dans la fenêtre du journal, afficher le nom de la chaîne du fichier M3U.",
            "tooltip_channel_url": "Dans la fenêtre du journal, afficher l'URL complète du flux de la chaîne."
        },
        "it": {
            "title": "IPTV-Check", "file": "File", "recheck_output": "Ricontrolla File di Output", "exit": "Esci",
            "tools": "Strumenti", "website_finder": "Trova M3U su Sito Web...", "database": "Database",
            "manage_links": "Gestisci Link Predefiniti...", "check_all_links": "Controlla Tutti i Link Predefiniti", "settings": "Impostazioni",
            "configure": "Configura...", "language": "Lingua", "debug": "Debug", "view_log": "Visualizza Log di Debug",
            "about_menu": "Informazioni", "creators": "Creatori...", "update": "Aggiorna...", "m3u_input_label": "File M3U o URL:",
            "output_file_label": "File di Output:", "browse": "Sfoglia...", "start_check": "Avvia Controllo",
            "stop_save": "Ferma e Salva", "timeout_label": "Timeout (s):", "workers_label": "Workers:",
            "remaining_label": "Rimanenti:", "log_display_label": "Visualizzazione Log", "channel_name_radio": "Nome Canale",
            "channel_url_radio": "URL Canale", "options_label": "Opzioni", "use_ocr_check": "Usa OCR",
            "skip_known_check": "Salta URL conosciuti", "search_label": "Cerca nel File di Output...",
            "no_internet": "Nessuna Connessione Internet. In attesa di connessione...",
            "tooltip_ocr": "Se selezionato, utilizza l'OCR (Tesseract) per analizzare un frame dai flussi video.\nAiuta a rilevare schermate di errore (es. 'Login richiesto', geo-bloccato).\nQuesto controllo è più lento.",
            "tooltip_timeout": "Timeout di rete in secondi per ogni controllo del flusso.", "tooltip_workers": "Numero di controlli paralleli da eseguire contemporaneamente.",
            "tooltip_log_display": "Modifica il formato di visualizzazione nel log durante un controllo.",
            "tooltip_skip_known": "Se selezionato, l'app leggerà prima il tuo file di output.\nQualsiasi URL di flusso dalla nuova fonte che esiste già nel file di output verrà saltato.\nCiò previene i duplicati e accelera il controllo di grandi liste.",
            "tooltip_channel_name": "Nella finestra di log, visualizza il nome del canale dal file M3U.",
            "tooltip_channel_url": "Nella finestra di log, visualizza l'URL completo del flusso del canale."
        },
        "de": {
            "title": "IPTV-Check", "file": "Datei", "recheck_output": "Ausgabedatei erneut prüfen", "exit": "Beenden",
            "tools": "Werkzeuge", "website_finder": "Website-M3U-Finder...", "database": "Datenbank",
            "manage_links": "Standard-Links verwalten...", "check_all_links": "Alle Standard-Links prüfen", "settings": "Einstellungen",
            "configure": "Konfigurieren...", "language": "Sprache", "debug": "Debug", "view_log": "Debug-Protokoll anzeigen",
            "about_menu": "Über", "creators": "Entwickler...", "update": "Aktualisieren...", "m3u_input_label": "M3U-Datei oder URL:",
            "output_file_label": "Ausgabedatei:", "browse": "Durchsuchen...", "start_check": "Prüfung starten",
            "stop_save": "Stoppen & Speichern", "timeout_label": "Timeout (s):", "workers_label": "Workers:",
            "remaining_label": "Verbleibend:", "log_display_label": "Protokollanzeige", "channel_name_radio": "Kanalname",
            "channel_url_radio": "Kanal-URL", "options_label": "Optionen", "use_ocr_check": "OCR verwenden",
            "skip_known_check": "Bekannte URLs überspringen", "search_label": "In Ausgabedatei suchen...",
            "no_internet": "Keine Internetverbindung. Warte auf Verbindung...",
            "tooltip_ocr": "Wenn aktiviert, wird OCR (Tesseract) verwendet, um einen Frame aus Videostreams zu analysieren.\nHilft bei der Erkennung von Fehlerbildschirmen (z.B. 'Login erforderlich', geo-geblockt).\nDiese Prüfung ist langsamer.",
            "tooltip_timeout": "Netzwerk-Timeout in Sekunden für jede Stream-Prüfung.", "tooltip_workers": "Anzahl der gleichzeitig auszuführenden parallelen Prüfungen.",
            "tooltip_log_display": "Ändert das Anzeigeformat in der Protokollansicht während einer Prüfung.",
            "tooltip_skip_known": "Wenn aktiviert, liest die App zuerst Ihre Ausgabedatei.\nJede Stream-URL aus der neuen Quelle, die bereits in der Ausgabedatei vorhanden ist, wird übersprungen.\nDies verhindert Duplikate und beschleunigt die Prüfung großer Listen.",
            "tooltip_channel_name": "Zeigt im Protokollfenster den Namen des Kanals aus der M3U-Datei an.",
            "tooltip_channel_url": "Zeigt im Protokollfenster die vollständige URL des Kanal-Streams an."
        },
        "ru": {
            "title": "IPTV-Check", "file": "Файл", "recheck_output": "Перепроверить выходной файл", "exit": "Выход",
            "tools": "Инструменты", "website_finder": "Поиск M3U на сайтах...", "database": "База данных",
            "manage_links": "Управление ссылками по умолчанию...", "check_all_links": "Проверить все ссылки по умолчанию", "settings": "Настройки",
            "configure": "Настроить...", "language": "Язык", "debug": "Отладка", "view_log": "Просмотр журнала отладки",
            "about_menu": "О программе", "creators": "Создатели...", "update": "Обновить...", "m3u_input_label": "Файл M3U или URL:",
            "output_file_label": "Выходной файл:", "browse": "Обзор...", "start_check": "Начать проверку",
            "stop_save": "Остановить и сохранить", "timeout_label": "Тайм-аут (с):", "workers_label": "Потоки:",
            "remaining_label": "Осталось:", "log_display_label": "Отображение журнала", "channel_name_radio": "Имя канала",
            "channel_url_radio": "URL канала", "options_label": "Опции", "use_ocr_check": "Использовать OCR",
            "skip_known_check": "Пропускать известные URL", "search_label": "Поиск в выходном файле...",
            "no_internet": "Нет подключения к Интернету. Ожидание подключения...",
            "tooltip_ocr": "Если отмечено, используется OCR (Tesseract) для анализа кадра из видеопотоков.\nЭто помогает обнаруживать экраны ошибок (например, 'Требуется вход', геоблокировка).\nЭта проверка медленнее.",
            "tooltip_timeout": "Тайм-аут сети в секундах для каждой проверки потока.", "tooltip_workers": "Количество одновременных параллельных проверок.",
            "tooltip_log_display": "Изменяет формат отображения в журнале во время проверки.",
            "tooltip_skip_known": "Если отмечено, приложение сначала прочитает ваш выходной файл.\nЛюбой URL потока из нового источника, который уже существует в выходном файле, будет пропущен.\nЭто предотвращает дубликаты и ускоряет проверку больших списков.",
            "tooltip_channel_name": "В окне журнала отображать имя канала из файла M3U.",
            "tooltip_channel_url": "В окне журнала отображать полный URL потока канала."
        },
        "zh": {
            "title": "IPTV-Check", "file": "文件", "recheck_output": "重新检查输出文件", "exit": "退出",
            "tools": "工具", "website_finder": "网站 M3U 查找器...", "database": "数据库",
            "manage_links": "管理默认链接...", "check_all_links": "检查所有默认链接", "settings": "设置",
            "configure": "配置...", "language": "语言", "debug": "调试", "view_log": "查看调试日志",
            "about_menu": "关于", "creators": "创作者...", "update": "更新...", "m3u_input_label": "M3U 文件或 URL:",
            "output_file_label": "输出文件:", "browse": "浏览...", "start_check": "开始检查",
            "stop_save": "停止并保存", "timeout_label": "超时 (秒):", "workers_label": "线程数:",
            "remaining_label": "剩余:", "log_display_label": "日志显示", "channel_name_radio": "频道名称",
            "channel_url_radio": "频道 URL", "options_label": "选项", "use_ocr_check": "使用 OCR",
            "skip_known_check": "跳过已知良好的URL", "search_label": "在输出文件中搜索...",
            "no_internet": "无网络连接。正在等待连接...",
            "tooltip_ocr": "如果选中，将使用 OCR (Tesseract) 分析视频流中的一帧。\n这有助于检测错误屏幕（例如“需要登录”、“地理封锁”）。\n此检查速度较慢。",
            "tooltip_timeout": "每次流检查的网络超时时间（秒）。", "tooltip_workers": "一次运行的并行检查数。",
            "tooltip_log_display": "在检查期间更改日志视图中的显示格式。",
            "tooltip_skip_known": "如果选中，应用程序将首先读取您的输出文件。\n新源中任何已存在于输出文件中的流 URL 都将被跳过。\n这样可以防止重复并加快检查大型列表的速度。",
            "tooltip_channel_name": "在日志窗口中，显示 M3U 文件中的频道名称。",
            "tooltip_channel_url": "在日志窗口中，显示频道的完整流 URL。"
        }
    }

# --- Setup Debug Logging ---
def setup_logging():
    logging.basicConfig(filename=DEBUG_LOG_PATH, filemode='w', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.info(f"IPTV-Check v{VERSION} started.")

# --- Dependency Checks ---
FFMPEG_PATH = shutil.which('ffmpeg')
FFPROBE_PATH = shutil.which('ffprobe')
YT_DLP_PATH = shutil.which('yt-dlp')
GIT_PATH = shutil.which('git')

def find_and_set_tesseract_path():
    path = shutil.which('tesseract');
    if path: pytesseract.tesseract_cmd = path; return True
    return False

TESSERACT_INSTALLED = find_and_set_tesseract_path()
OCR_FAILED_ONCE = False

def check_dependencies():
    essential_deps = {'ffmpeg': FFMPEG_PATH, 'ffprobe': FFPROBE_PATH, 'yt-dlp': YT_DLP_PATH}
    optional_deps = {'tesseract': TESSERACT_INSTALLED}
    
    missing_essential = [name for name, path in essential_deps.items() if not path]
    missing_optional = [name for name, found in optional_deps.items() if not found]
    
    return missing_essential, missing_optional

# --- "The Janitor": Cleanup on Start ---
def cleanup_stale_temp_files():
    try:
        temp_dir = tempfile.gettempdir()
        for f_name in [f for f in os.listdir(temp_dir) if f.startswith(TEMP_FILE_PREFIX)]:
            try: os.remove(os.path.join(temp_dir, f_name))
            except OSError as e: logging.warning(f"Could not remove stale temp file: {f_name}. Reason: {e}")
    except Exception as e:
        logging.error(f"Error during initial temp file cleanup: {e}", exc_info=True)

# --- Configuration & Database Management ---
class IniManager:
    def __init__(self, path):
        self.path = path
    
    def load(self, defaults_map=None):
        config = configparser.ConfigParser()
        if self.path.exists():
            try:
                config.read(self.path, encoding='utf-8')
            except configparser.Error as e:
                logging.error(f"Error reading config file {self.path}: {e}. A new one will be created.")
                config = configparser.ConfigParser()

        needs_save = False
        if defaults_map:
            for section, defaults in defaults_map.items():
                if not config.has_section(section):
                    config.add_section(section)
                    for key, value in defaults.items():
                        config.set(section, key, value)
                    needs_save = True
        
        if needs_save: self.save(config)
        
        return {section.lower(): dict(config.items(section)) for section in config.sections()}

    def save(self, config_obj):
        try:
            with open(self.path, 'w', encoding='utf-8') as configfile:
                config_obj.write(configfile)
        except Exception as e:
            logging.error(f"Failed to save INI file at {self.path}: {e}", exc_info=True)
            if GUI_AVAILABLE: messagebox.showerror("File Error", f"Could not save settings to {self.path}.\nPlease check permissions.")

# --- Core Logic ---
def sanitize_url_aggressively(url):
    try:
        m3u8_query_index = url.find('.m3u8?')
        if m3u8_query_index != -1 and 'ads.' in url[m3u8_query_index:]:
            sanitized_url = url[:m3u8_query_index + len('.m3u8')]; logging.info(f"Aggressively sanitized URL: '{url}' -> '{sanitized_url}'"); return sanitized_url
    except Exception as e: logging.warning(f"Error during aggressive URL sanitization: {e}", exc_info=True)
    return url

def parse_m3u(content):
    pattern = re.compile(r'#EXTINF:-1.*?group-title="([^"]*)"[^,]*?,([^\n]+)\n(?:#EXT[^\n]+\n)*(https?://[^\s]+)', re.IGNORECASE)
    matches = pattern.findall(content)
    streams = []
    
    if not matches:
        pattern = re.compile(r'#EXTINF:-1.*?,([^\n]+)\n(?:#EXT[^\n]+\n)*(https?://[^\s]+)')
        matches = pattern.findall(content)
        for title, url in matches:
            streams.append({'title': title.strip(), 'url': url.strip(), 'group': 'General'})
    else:
        for group, title, url in matches:
            streams.append({'title': title.strip(), 'url': url.strip(), 'group': group.strip() or "General"})

    return streams

def write_m3u_header(file_handle):
    if file_handle: file_handle.write("#EXTM3U\n\n"); file_handle.flush()

def write_m3u_entry(file_handle, stream_info):
    if file_handle:
        group = stream_info.get('group', 'General'); title = stream_info.get('title', 'Unknown'); url = stream_info.get('url', '')
        file_handle.write(f"#EXTINF:-1 group-title=\"{group}\",{title}\n{url}\n\n"); file_handle.flush()

def build_timeout_config(network_timeout_s):
    return {"network_timeout_us": str(network_timeout_s * 1000000), "ffmpeg_flags": ['-analyzeduration', '5M', '-probesize', '5M'] if network_timeout_s >= 20 else []}

# --- TOOLTIP CLASS (GUI ONLY) ---
if GUI_AVAILABLE:
    class ToolTip:
        def __init__(self, widget, text):
            self.widget = widget
            self.text = text
            self.tooltip_window = None
            self.widget.bind("<Enter>", self.show_tooltip)
            self.widget.bind("<Leave>", self.hide_tooltip)

        def show_tooltip(self, event=None):
            x, y, _, _ = self.widget.bbox("insert")
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + 25

            self.tooltip_window = tk.Toplevel(self.widget)
            self.tooltip_window.wm_overrideredirect(True)
            self.tooltip_window.wm_geometry(f"+{x}+{y}")

            label = tk.Label(self.tooltip_window, text=self.text, justify='left',
                             background="#ffffe0", relief='solid', borderwidth=1,
                             font=("tahoma", "8", "normal"))
            label.pack(ipadx=1)

        def hide_tooltip(self, event=None):
            if self.tooltip_window:
                self.tooltip_window.destroy()
            self.tooltip_window = None

# --- GUI APPLICATION CLASSES (GUI ONLY) ---
if GUI_AVAILABLE:
    class BaseToplevel(tk.Toplevel):
        def __init__(self, parent):
            super().__init__(parent); self.transient(parent); self._create_context_menu()
        def _create_context_menu(self):
            self.entry_context_menu = tk.Menu(self, tearoff=0)
            self.entry_context_menu.add_command(label="Cut", command=lambda: self.focus_get().event_generate("<<Cut>>"))
            self.entry_context_menu.add_command(label="Copy", command=lambda: self.focus_get().event_generate("<<Copy>>"))
            self.entry_context_menu.add_command(label="Paste", command=lambda: self.focus_get().event_generate("<<Paste>>"))
        def _show_context_menu(self, event):
            widget = event.widget
            try:
                if self.clipboard_get(): self.entry_context_menu.entryconfig("Paste", state="normal")
                else: self.entry_context_menu.entryconfig("Paste", state="disabled")
            except tk.TclError: self.entry_context_menu.entryconfig("Paste", state="disabled")
            if widget.selection_present(): self.entry_context_menu.entryconfig("Cut", state="normal"); self.entry_context_menu.entryconfig("Copy", state="normal")
            else: self.entry_context_menu.entryconfig("Cut", state="disabled"); self.entry_context_menu.entryconfig("Copy", state="disabled")
            self.entry_context_menu.tk_popup(event.x_root, event.y_root)

    class AddPatternDialog(simpledialog.Dialog):
        def body(self, master):
            self.title("Add Stream Pattern")
            ttk.Label(master, text="URL Pattern (e.g., .m3u8, /stream):").grid(row=0, sticky="w")
            self.pattern_entry = ttk.Entry(master, width=30)
            self.pattern_entry.grid(row=1, padx=5, pady=5)
            
            ttk.Label(master, text="Stream Type:").grid(row=2, sticky="w")
            self.type_var = tk.StringVar(value="video")
            self.type_combo = ttk.Combobox(master, textvariable=self.type_var, values=["video", "audio"], state="readonly")
            self.type_combo.grid(row=3, padx=5, pady=5)
            
            return self.pattern_entry

        def apply(self):
            self.result = (self.pattern_entry.get().strip(), self.type_var.get())

    class SettingsWindow(BaseToplevel):
        def __init__(self, parent):
            super().__init__(parent); self.title("Configure Settings"); self.parent = parent; self.config_manager = parent.config_manager
            
            all_configs = self.config_manager.load({})
            self.settings = all_configs.get('settings', {})
            self.stream_patterns = all_configs.get('streampatterns', {})

            self.notebook = ttk.Notebook(self); self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            player_frame = ttk.Frame(self.notebook, padding="10"); self.notebook.add(player_frame, text='Player')
            self.media_player_path = tk.StringVar(value=self.settings.get('mediaplayerpath', ''))
            mp_frame = ttk.LabelFrame(player_frame, text="Media Player Executable Path", padding="5"); mp_frame.pack(fill=tk.X, expand=True, pady=5)
            mp_entry = ttk.Entry(mp_frame, textvariable=self.media_player_path); mp_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
            mp_entry.bind("<Button-3>", self._show_context_menu); ttk.Button(mp_frame, text="Browse...", command=self._browse_player).pack(side=tk.LEFT)
            types_frame = ttk.Frame(self.notebook, padding="10"); self.notebook.add(types_frame, text='Stream Patterns')
            self.listbox = tk.Listbox(types_frame, height=10); self.listbox.pack(fill=tk.BOTH, expand=True, pady=5); self.populate_list()
            btn_frame = ttk.Frame(types_frame); btn_frame.pack(fill=tk.X, pady=5)
            ttk.Button(btn_frame, text="Add...", command=self.add_type).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
            ttk.Button(btn_frame, text="Edit...", command=self.edit_type).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
            ttk.Button(btn_frame, text="Remove", command=self.remove_type).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
            button_frame = ttk.Frame(self); button_frame.pack(fill=tk.X, expand=True, padx=10, pady=(0, 10))
            ttk.Button(button_frame, text="Save & Close", command=self.on_save).pack(side=tk.RIGHT)
            self.grab_set()
        def _browse_player(self):
            path = filedialog.askopenfilename(title="Select Media Player Executable");
            if path: self.media_player_path.set(path)
        def populate_list(self):
            self.listbox.delete(0, tk.END)
            for ext, type_ in sorted(self.stream_patterns.items()): self.listbox.insert(tk.END, f"{ext}: {type_}")
        
        def add_type(self):
            dialog = AddPatternDialog(self)
            if dialog.result:
                pattern, type_ = dialog.result
                if pattern:
                    self.stream_patterns[pattern] = type_
                    self.populate_list()

        def edit_type(self):
            selected_idx = self.listbox.curselection()
            if not selected_idx: return
            pattern, type_ = self.listbox.get(selected_idx[0]).split(': ', 1)
            new_type = simpledialog.askstring("Edit Type", f"Enter new type for '{pattern}':", initialvalue=type_, parent=self)
            if new_type and new_type.lower() in ['video', 'audio']:
                self.stream_patterns[pattern] = new_type.lower(); self.populate_list()
            else: messagebox.showerror("Invalid Type", "Type must be 'video' or 'audio'.", parent=self)
        def remove_type(self):
            selected_idx = self.listbox.curselection()
            if not selected_idx: return
            pattern, _ = self.listbox.get(selected_idx[0]).split(': ', 1)
            if messagebox.askyesno("Confirm Remove", f"Remove pattern '{pattern}'?"): del self.stream_patterns[pattern]; self.populate_list()
        def on_save(self):
            self.settings['mediaplayerpath'] = self.media_player_path.get()
            new_config = configparser.ConfigParser()
            new_config['Settings'] = self.settings
            new_config['StreamPatterns'] = self.stream_patterns
            self.config_manager.save(new_config)
            self.parent.load_settings(); self.destroy()

    class WebsiteFinderWindow(BaseToplevel):
        def __init__(self, parent):
            super().__init__(parent); self.title("Website M3U Finder"); self.parent = parent; self.geometry("600x400")
            body = ttk.Frame(self, padding="10"); body.pack(fill=tk.BOTH, expand=True)
            top_frame = ttk.Frame(body); top_frame.pack(fill=tk.X, pady=(0, 10))
            ttk.Label(top_frame, text="URL:").pack(side=tk.LEFT, padx=(0, 5)); self.url_var = tk.StringVar()
            url_entry = ttk.Entry(top_frame, textvariable=self.url_var); url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            url_entry.bind("<Button-3>", self._show_context_menu)
            self.find_btn = ttk.Button(top_frame, text="Find M3Us", command=self.start_find); self.find_btn.pack(side=tk.LEFT, padx=(5, 0))
            self.results_box = tk.Listbox(body); self.results_box.pack(fill=tk.BOTH, expand=True)
            bottom_frame = ttk.Frame(body); bottom_frame.pack(fill=tk.X, pady=(10, 0))
            self.status_var = tk.StringVar(value="Ready."); ttk.Label(bottom_frame, textvariable=self.status_var, anchor="w").pack(side=tk.LEFT)
            self.add_to_db_btn = ttk.Button(bottom_frame, text="Add Selected to DB", state=tk.DISABLED, command=self.add_to_db); self.add_to_db_btn.pack(side=tk.RIGHT)
            self.grab_set()
        def start_find(self):
            url = self.url_var.get().strip();
            if not url: return
            self.find_btn.config(state=tk.DISABLED); self.add_to_db_btn.config(state=tk.DISABLED)
            self.results_box.delete(0, tk.END); self.status_var.set("Searching..."); self.update_idletasks()
            threading.Thread(target=self._find_thread, args=(url,), daemon=True).start()
        def _find_thread(self, url):
            try:
                self.parent.log(f"[*] Website Finder: Fetching {url}", "info")
                r = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=15); r.raise_for_status()
                valid_links = set()
                if r.url.lower().endswith(('.m3u', '.m3u8')):
                    self.status_var.set("Found direct redirect to M3U file.")
                    self.results_box.insert(tk.END, r.url); valid_links.add(r.url)
                else:
                    self.status_var.set("Scanning page for M3U links...")
                    pattern = re.compile(r'["\'](https?://[^\'" >]+?\.(?:m3u8?)|[^\'" >]+?\.(?:m3u8?))["\']'); found_links = pattern.findall(r.text)
                    for link in found_links:
                        full_url = urljoin(url, link); self.status_var.set(f"Validating: {full_url[:50]}...")
                        try:
                            head_r = requests.head(full_url, headers={'User-Agent': USER_AGENT}, timeout=5, allow_redirects=True)
                            if head_r.status_code == 200: valid_links.add(full_url); self.results_box.insert(tk.END, full_url)
                        except requests.RequestException: continue
                if valid_links: self.status_var.set(f"Found {len(valid_links)} valid M3U link(s)."); self.add_to_db_btn.config(state=tk.NORMAL)
                else: self.status_var.set("No valid M3U links found on page or via redirect.")
            except Exception as e:
                self.status_var.set(f"Error: {e}"); self.parent.log(f"[!] Website Finder Error: {e}", "red")
            finally:
                self.find_btn.config(state=tk.NORMAL)
        def add_to_db(self):
            selected_indices = self.results_box.curselection()
            if not selected_indices: messagebox.showwarning("No Selection", "Please select one or more links to add.", parent=self); return
            db_config = configparser.ConfigParser(); db_config.read(self.parent.links_db_manager.path)
            if not db_config.has_section('DefaultLinks'): db_config.add_section('DefaultLinks')
            links = dict(db_config.items('DefaultLinks')); added_count = 0
            for idx in selected_indices:
                url = self.results_box.get(idx)
                try: name = Path(urlparse(url).path).stem.replace('-', ' ').replace('_', ' ').title()
                except: name = f"link_{int(time.time())}"
                if url not in links.values(): links[name.lower().replace(' ', '_')] = url; added_count += 1
            db_config['DefaultLinks'] = links
            self.parent.links_db_manager.save(db_config)
            messagebox.showinfo("Success", f"Added {added_count} new link(s) to the database.", parent=self)

    class LinksManagerWindow(BaseToplevel):
        def __init__(self, parent):
            super().__init__(parent); self.title("Default Links Database"); self.links_db_manager = parent.links_db_manager
            body = ttk.Frame(self, padding="10"); body.pack(fill=tk.BOTH, expand=True)
            self.listbox = tk.Listbox(body, height=15); self.listbox.pack(fill=tk.BOTH, expand=True, pady=5); self.populate_list()
            btn_frame = ttk.Frame(body); btn_frame.pack(fill=tk.X, pady=5)
            ttk.Button(btn_frame, text="Add...", command=self.add_link).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
            ttk.Button(btn_frame, text="Edit...", command=self.edit_link).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
            ttk.Button(btn_frame, text="Remove", command=self.remove_link).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
            self.grab_set()
        def populate_list(self):
            self.listbox.delete(0, tk.END); self.links = self.links_db_manager.load({'DefaultLinks': {}}).get('defaultlinks', {})
            for name, url in sorted(self.links.items()): self.listbox.insert(tk.END, f"{name}: {url}")
        
        def add_link(self):
            url = simpledialog.askstring("Add Link", "Enter the M3U URL:", parent=self)
            if not url or not url.strip():
                return

            url = url.strip()

            if url in self.links.values():
                messagebox.showinfo("Duplicate", "This URL already exists in the database.", parent=self)
                return

            try:
                parsed_url = urlparse(url)
                path_stem = Path(parsed_url.path).stem
                base_name = path_stem if path_stem and path_stem != '/' else parsed_url.hostname
                if not base_name:
                    base_name = f"link_{int(time.time())}"
            except Exception:
                base_name = f"link_{int(time.time())}"

            key = base_name.strip().lower().replace(' ', '_').replace('-', '_')
            key = re.sub(r'\W+', '', key)

            final_key = key
            counter = 2
            while final_key in self.links.keys():
                final_key = f"{key}_{counter}"
                counter += 1

            self.links[final_key] = url
            self.save_and_repopulate()
            messagebox.showinfo("Success", f"Added link to database with name: {final_key}", parent=self)

        def edit_link(self):
            selected_idx = self.listbox.curselection();
            if not selected_idx: return
            name, url = self.listbox.get(selected_idx[0]).split(': ', 1); key = name
            
            if key not in self.links:
                key = name.lower().replace(' ', '_')
                if key not in self.links:
                     messagebox.showerror("Error", "Could not find the selected link key in the database.", parent=self)
                     return
            
            new_name = simpledialog.askstring("Edit Link", "Enter new name:", initialvalue=name, parent=self)
            if not new_name or not new_name.strip(): return
            new_url = simpledialog.askstring("Edit Link", "Enter new URL:", initialvalue=url, parent=self)
            if not new_url or not new_url.strip(): return
            
            del self.links[key]
            self.links[new_name.strip().lower().replace(' ', '_')] = new_url.strip()
            self.save_and_repopulate()

        def remove_link(self):
            selected_idx = self.listbox.curselection()
            if not selected_idx: return
            if not messagebox.askyesno("Confirm Remove", "Are you sure?"): return
            name, _ = self.listbox.get(selected_idx[0]).split(': ', 1); key = name
            
            if key not in self.links:
                key = name.lower().replace(' ', '_')
                if key not in self.links:
                     messagebox.showerror("Error", "Could not find the selected link key in the database.", parent=self)
                     return
                     
            del self.links[key]; self.save_and_repopulate()
        def save_and_repopulate(self):
            config = configparser.ConfigParser(); config['DefaultLinks'] = self.links
            self.links_db_manager.save(config); self.populate_list()

# --- BASE CLASS FOR CHECKING LOGIC ---
class CheckerBase:
    def __init__(self):
        self.streams_to_check = []
        self.active_processes = {}
        self.is_running = False
        self.processed_count = 0
        self.online_count = 0
        self.uncheckable_count = 0
        self.journal_file = None
        self.uncheckable_file = None
        self.current_check_id = None
        self.lock = threading.RLock() # FIX: Use a Re-entrant Lock to prevent deadlocks
        
        self.config_manager = IniManager(CONFIG_FILE_PATH)
        defaults = {'Settings': {}, 'StreamPatterns': {'.m3u8': 'video', '.m3u': 'video', '.ts': 'video', '.mp3': 'audio', '.aac': 'audio', '/stream': 'audio'}}
        all_configs = self.config_manager.load(defaults)
        self.stream_patterns = all_configs.get('streampatterns', {})

    def _get_stream_type(self, url):
        if not FFPROBE_PATH: return 'unknown'
        try:
            cmd = [FFPROBE_PATH, '-v', 'quiet', '-user_agent', AUDIO_USER_AGENT, '-i', url]
            result = subprocess.run(cmd, capture_output=True, text=True, errors='ignore', timeout=10)
            output = result.stderr
            if "Stream #" in output and "Video:" in output: return 'video'
            if "Stream #" in output and "Audio:" in output: return 'audio'
            return 'unknown'
        except (subprocess.TimeoutExpired, Exception):
            return 'unknown'

    def _perform_ocr_check(self, video_file_path):
        temp_image_file = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", prefix=TEMP_FILE_PREFIX, delete=False) as tf: temp_image_file = tf.name
            subprocess.run([FFMPEG_PATH, '-y', '-hide_banner', '-loglevel', 'error', '-ss', '00:00:01', '-i', video_file_path, '-vframes', '1', temp_image_file], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=OCR_FRAME_EXTRACTION_TIMEOUT)
            if os.path.exists(temp_image_file) and os.path.getsize(temp_image_file) > 0:
                text = pytesseract.image_to_string(Image.open(temp_image_file)).lower()
                if any(keyword in text for keyword in ["error", "login", "failed", "access denied", "unavailable", "not found"]): return "OFF (OCR: Error Screen)"
            return "ON"
        except Exception as ocr_error:
            global OCR_FAILED_ONCE; logging.warning(f"OCR check failed: {ocr_error}", exc_info=True)
            if not OCR_FAILED_ONCE: self.log(f"[!] OCR check failed. Assuming 'ON'.", "yellow"); OCR_FAILED_ONCE = True
            return "ON (OCR Failed)"
        finally:
            if temp_image_file and os.path.exists(temp_image_file):
                try: os.remove(temp_image_file)
                except OSError: pass

    def _force_kill_worker(self, pid, data):
        try:
            if os.name == 'posix':
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            else:
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)], capture_output=True, check=False)
            data['proc'].wait(timeout=2)
        except (ProcessLookupError, OSError, subprocess.TimeoutExpired): pass
        finally:
            if data and data.get('temp_file') and os.path.exists(data['temp_file']): 
                try: os.remove(data['temp_file'])
                except OSError: pass

    def log(self, message, tag=None, stream_id=None):
        pass

# --- GUI APPLICATION CLASS ---
if GUI_AVAILABLE:
    class AppGUI(tk.Tk, CheckerBase):
        def __init__(self, cli_args, missing_optional_deps=None):
            tk.Tk.__init__(self)
            CheckerBase.__init__(self)
            self.cli_args = cli_args
            self.links_db_manager = IniManager(LINKS_DB_PATH)
            
            self.lang_code = self.config_manager.load({'Settings': {'language': DEFAULT_LANG}}).get('settings', {}).get('language', DEFAULT_LANG)
            if self.lang_code not in LANGUAGES:
                self.lang_code = DEFAULT_LANG
            self.i18n = LANGUAGES[self.lang_code]

            self.title(f"{self.i18n.get('title')} {VERSION}")
            self.geometry("900x700")
            
            self.log_url_map = {}
            self.is_rechecking = False
            self.known_good_urls = set()
            
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            self._create_main_menu()
            self._create_context_menu()
            self.main_frame = ttk.Frame(self, padding="10")
            self.main_frame.pack(fill=tk.BOTH, expand=True)
            self._create_widgets()
            
            if missing_optional_deps and 'tesseract' in missing_optional_deps:
                messagebox.showwarning("Optional Dependency Missing", 
                                     "Tesseract OCR not found.\nThe OCR feature will be disabled.\n\nTo enable it, please install Tesseract for your OS (e.g., 'sudo apt install tesseract-ocr').")
                self.ocr_check.config(state=tk.DISABLED)

            self.load_settings()
            self.after(500, self._periodic_internet_check)

        def log(self, message, tag=None, stream_id=None):
            # This is the GUI-specific implementation of the log method
            if stream_id: self.log_view.insert(tk.END, message + "\n", (tag, stream_id))
            else: self.log_view.insert(tk.END, message + "\n", tag)
            self.log_view.see(tk.END); self.update_idletasks()
            
        def load_settings(self):
            defaults = {'Settings': {'mediaplayerpath': '', 'useocr': 'yes' if TESSERACT_INSTALLED else 'no', 
                                     'skipknowngoodurls': 'no', 'language': 'en'},
                        'StreamPatterns': {'.m3u8': 'video', '.m3u': 'video', '.ts': 'video', '.mp3': 'audio', '.aac': 'audio', '/stream': 'audio'}}
            all_configs = self.config_manager.load(defaults)
            self.settings = all_configs.get('settings', {})
            self.stream_patterns = all_configs.get('streampatterns', {})
            if hasattr(self, 'use_ocr_var'):
                self.use_ocr_var.set(self.settings.get('useocr') == 'yes')
                self.skip_knowngood_urls_var.set(self.settings.get('skipknowngoodurls') == 'yes')

        def _check_internet_connection(self):
            try:
                requests.get("https://www.google.com", timeout=5, headers={'User-Agent': USER_AGENT})
                return True
            except requests.ConnectionError:
                return False

        def _periodic_internet_check(self):
            has_internet = self._check_internet_connection()
            if has_internet:
                self.internet_status_label.pack_forget()
                if self.start_button['state'] == tk.DISABLED and not self.is_running:
                    self._set_ui_state(True)
            else:
                self.internet_status_label.pack(side=tk.TOP, fill=tk.X)
                if self.start_button['state'] == tk.NORMAL:
                    self._set_ui_state(False)
            self.after(30000, self._periodic_internet_check)

        def _set_ui_state(self, enabled):
            state = tk.NORMAL if enabled else tk.DISABLED
            self.start_button.config(state=state)
            self.browse_button.config(state=state)
            self.input_entry.config(state='normal' if enabled else 'disabled')
            self.output_entry.config(state='normal' if enabled else 'disabled')
            self.timeout_menu.config(state='readonly' if enabled else 'disabled')
            self.workers_menu.config(state='readonly' if enabled else 'disabled')
            search_file_exists = os.path.exists(self.output_var.get()) and os.path.getsize(self.output_var.get()) > 0
            self.search_entry.config(state='normal' if enabled and search_file_exists else 'disabled')
            for menu_name in ["File", "Tools", "Database", "Settings", "Debug", "About", "Language"]:
                try: self.menu_bar.entryconfig(menu_name, state=state)
                except tk.TclError: pass

        def on_closing(self):
            if self.is_running and messagebox.askyesno("Confirm Exit", "A check is running. Stop and exit?"): self.stop_processing(); self.destroy()
            elif not self.is_running: self.destroy()

        def _create_main_menu(self):
            self.menu_bar = tk.Menu(self)
            self.config(menu=self.menu_bar)

            self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
            self.file_menu.add_command(label=self.i18n.get("recheck_output"), command=self.recheck_output_file)
            self.file_menu.add_separator()
            self.file_menu.add_command(label=self.i18n.get("exit"), command=self.on_closing)
            self.menu_bar.add_cascade(label=self.i18n.get("file"), menu=self.file_menu)

            self.tools_menu = tk.Menu(self.menu_bar, tearoff=0)
            self.tools_menu.add_command(label=self.i18n.get("website_finder"), command=self.open_website_finder)
            self.menu_bar.add_cascade(label=self.i18n.get("tools"), menu=self.tools_menu)

            self.db_menu = tk.Menu(self.menu_bar, tearoff=0)
            self.db_menu.add_command(label=self.i18n.get("manage_links"), command=self.open_links_manager)
            self.db_menu.add_separator()
            self.db_menu.add_command(label=self.i18n.get("check_all_links"), command=self.start_database_check)
            self.menu_bar.add_cascade(label=self.i18n.get("database"), menu=self.db_menu)

            settings_menu = tk.Menu(self.menu_bar, tearoff=0)
            settings_menu.add_command(label=self.i18n.get("configure"), command=lambda: SettingsWindow(self))
            self.menu_bar.add_cascade(label=self.i18n.get("settings"), menu=settings_menu)

            self.lang_menu = tk.Menu(self.menu_bar, tearoff=0)
            self.selected_lang = tk.StringVar(value=self.lang_code)
            for lang_code in sorted(LANGUAGES.keys()):
                self.lang_menu.add_radiobutton(label=lang_code.upper(), variable=self.selected_lang, value=lang_code, command=self.change_language)
            self.menu_bar.add_cascade(label=self.i18n.get("language"), menu=self.lang_menu)

            debug_menu = tk.Menu(self.menu_bar, tearoff=0)
            debug_menu.add_command(label=self.i18n.get("view_log"), command=self._view_debug_log)
            self.menu_bar.add_cascade(label=self.i18n.get("debug"), menu=debug_menu)

            self.about_menu = tk.Menu(self.menu_bar, tearoff=0)
            self.about_menu.add_command(label=self.i18n.get("creators"), command=self.show_creators)
            self.about_menu.add_command(label=self.i18n.get("update"), command=self.update_app)
            self.menu_bar.add_cascade(label=self.i18n.get("about_menu"), menu=self.about_menu)

        def change_language(self):
            new_lang = self.selected_lang.get()
            if new_lang != self.lang_code:
                if messagebox.askyesno("Change Language", "The application needs to restart to apply the language change. Restart now?"):
                    config = configparser.ConfigParser(); config.read(CONFIG_FILE_PATH, encoding='utf-8')
                    if not config.has_section('Settings'): config.add_section('Settings')
                    config.set('Settings', 'language', new_lang)
                    self.config_manager.save(config)
                    os.execl(sys.executable, sys.executable, *sys.argv)

        def show_creators(self):
            messagebox.showinfo("Creators", "Project Leader: peterpt\nCode Assistance by Gemini Pro Model\n\nhttps://github.com/peterpt/")
            
        def update_app(self):
            if not GIT_PATH:
                messagebox.showerror("Update Error", "'git' command not found. Please update manually.")
                return
            if messagebox.askyesno("Confirm Update", "This will attempt to update the application from GitHub. Are you sure?"):
                try:
                    self.log(">>> Attempting to update via git...", "info")
                    result = subprocess.run([GIT_PATH, 'pull'], capture_output=True, text=True, check=True, cwd=APP_DIR)
                    if "Already up to date." in result.stdout:
                        messagebox.showinfo("Update", "You are already using the latest version.")
                        self.log(">>> Already up to date.", "info")
                    else:
                        messagebox.showinfo("Update Successful", "Update complete. Please restart the application.")
                        self.log(">>> Update successful. Please restart.", "green")
                except subprocess.CalledProcessError as e:
                    messagebox.showerror("Update Failed", f"An error occurred during update:\n\n{e.stderr}")
                    self.log(f"[!] Update failed: {e.stderr}", "red")

        def _view_debug_log(self):
            try:
                if sys.platform == "win32": os.startfile(DEBUG_LOG_PATH)
                elif sys.platform == "darwin": subprocess.run(["open", DEBUG_LOG_PATH])
                else: subprocess.run(["xdg-open", DEBUG_LOG_PATH])
            except Exception as e: self.log(f"[!] Could not open debug log: {e}", "red")

        def _create_context_menu(self):
            self.entry_context_menu = tk.Menu(self, tearoff=0); self.entry_context_menu.add_command(label="Cut", command=lambda: self.focus_get().event_generate("<<Cut>>")); self.entry_context_menu.add_command(label="Copy", command=lambda: self.focus_get().event_generate("<<Copy>>")); self.entry_context_menu.add_command(label="Paste", command=lambda: self.focus_get().event_generate("<<Paste>>"))
            self.log_context_menu = tk.Menu(self, tearoff=0); self.log_context_menu.add_command(label="Open in Player", command=self._open_in_player); self.log_context_menu.add_separator(); self.log_context_menu.add_command(label="Copy URL", command=self._copy_log_url)
        
        def _show_context_menu(self, event):
            widget = event.widget
            try:
                if self.clipboard_get(): self.entry_context_menu.entryconfig("Paste", state="normal")
                else: self.entry_context_menu.entryconfig("Paste", state="disabled")
            except tk.TclError:
                self.entry_context_menu.entryconfig("Paste", state="disabled")
            if widget.selection_present():
                self.entry_context_menu.entryconfig("Cut", state="normal")
                self.entry_context_menu.entryconfig("Copy", state="normal")
            else:
                self.entry_context_menu.entryconfig("Cut", state="disabled")
                self.entry_context_menu.entryconfig("Copy", state="disabled")
            self.entry_context_menu.tk_popup(event.x_root, event.y_root)

        def _show_log_context_menu(self, event):
            self.log_view.tag_remove("sel", "1.0", "end"); clicked_index = self.log_view.index(f"@{event.x},{event.y}")
            line_tags = self.log_view.tag_names(clicked_index); stream_tag = next((tag for tag in line_tags if tag.startswith("stream_")), None)
            if stream_tag and stream_tag in self.log_url_map:
                line_start = self.log_view.index(f"{clicked_index} linestart"); line_end = self.log_view.index(f"{clicked_index} lineend")
                self.log_view.tag_add("sel", line_start, line_end); self.log_context_menu.entryconfig("Open in Player", state="normal"); self.log_context_menu.entryconfig("Copy URL", state="normal")
            else: self.log_context_menu.entryconfig("Open in Player", state="disabled"); self.log_context_menu.entryconfig("Copy URL", state="disabled")
            self.log_context_menu.tk_popup(event.x_root, event.y_root)

        def _get_url_from_selected_log(self):
            sel_ranges = self.log_view.tag_ranges("sel")
            if not sel_ranges: return None
            tags = self.log_view.tag_names(sel_ranges[0]); stream_tag = next((tag for tag in tags if tag.startswith("stream_")), None)
            return self.log_url_map.get(stream_tag)

        def _open_in_player(self):
            url = self._get_url_from_selected_log(); player_path = self.settings.get('mediaplayerpath')
            if not player_path: self.log("[!] Media player path not configured in Settings.", "red"); return
            if url:
                try: self.log(f"[*] Opening in external player...", "info"); subprocess.Popen([player_path, url])
                except Exception as e: self.log(f"[!] Failed to open media player: {e}", "red")

        def _copy_log_url(self):
            url = self._get_url_from_selected_log()
            if url: self.clipboard_clear(); self.clipboard_append(url); self.log("[*] URL copied to clipboard.", "info")
        
        def _create_widgets(self):
            self.internet_status_label = ttk.Label(self, text=self.i18n.get("no_internet"), 
                                                   foreground="white", background="red", anchor="center", padding=5)
            io_frame = ttk.Frame(self.main_frame); io_frame.pack(fill=tk.X, pady=5); io_frame.columnconfigure(1, weight=1)
            ttk.Label(io_frame, text=self.i18n.get("m3u_input_label")).grid(row=0, column=0, sticky="w", padx=5)
            self.input_var = tk.StringVar(value=self.cli_args.file or ''); self.input_entry = ttk.Entry(io_frame, textvariable=self.input_var)
            self.input_entry.grid(row=0, column=1, sticky="we")
            self.input_entry.bind("<Button-3>", self._show_context_menu)
            self.browse_button = ttk.Button(io_frame, text=self.i18n.get("browse"), command=self.browse_file); self.browse_button.grid(row=0, column=2, padx=5)
            ttk.Label(io_frame, text=self.i18n.get("output_file_label")).grid(row=1, column=0, sticky="w", padx=5, pady=5)
            self.output_var = tk.StringVar(value=self.cli_args.output); self.output_entry = ttk.Entry(io_frame, textvariable=self.output_var)
            self.output_entry.grid(row=1, column=1, sticky="we", pady=5); self.output_entry.bind("<Button-3>", self._show_context_menu)
            control_frame = ttk.Frame(self.main_frame); control_frame.pack(fill=tk.X, pady=5)
            self.start_button = ttk.Button(control_frame, text=self.i18n.get("start_check"), command=self.start_processing); self.start_button.pack(side="left", padx=5)
            self.stop_button = ttk.Button(control_frame, text=self.i18n.get("stop_save"), command=self.stop_processing, state=tk.DISABLED); self.stop_button.pack(side="left", padx=5)
            ttk.Label(control_frame, text=self.i18n.get("timeout_label")).pack(side="left", padx=(15, 5))
            self.timeout_var = tk.StringVar(value=str(self.cli_args.timeout)); self.timeout_menu = ttk.Combobox(control_frame, textvariable=self.timeout_var, values=[str(i) for i in range(2, 31)], state="readonly", width=4); self.timeout_menu.pack(side="left")
            ToolTip(self.timeout_menu, self.i18n.get("tooltip_timeout"))
            ttk.Label(control_frame, text=self.i18n.get("workers_label")).pack(side="left", padx=(10, 5))
            self.workers_var = tk.StringVar(value=str(self.cli_args.workers)); self.workers_menu = ttk.Combobox(control_frame, textvariable=self.workers_var, values=[str(i) for i in range(1, 21)], state="readonly", width=4); self.workers_menu.pack(side="left")
            ToolTip(self.workers_menu, self.i18n.get("tooltip_workers"))
            self.search_var = tk.StringVar(); self.search_var.trace_add("write", self._on_search_change)
            self.search_entry = ttk.Entry(control_frame, textvariable=self.search_var, width=20)
            self.search_entry.pack(side="left", padx=(10,0)); self.search_entry.insert(0, self.i18n.get("search_label")); self.search_entry.config(foreground="grey")
            self.search_entry.bind("<FocusIn>", self._on_search_focus_in); self.search_entry.bind("<FocusOut>", self._on_search_focus_out)
            self.search_entry.config(state=tk.DISABLED)
            self.remaining_label = ttk.Label(control_frame, text=f"{self.i18n.get('remaining_label')} 0"); self.remaining_label.pack(side="right", padx=10)
            options_frame = ttk.Frame(self.main_frame); options_frame.pack(fill=tk.X, pady=5)
            log_display_frame = ttk.LabelFrame(options_frame, text=self.i18n.get("log_display_label"))
            log_display_frame.pack(side="left", fill="x", expand=True, padx=(0,5))
            self.log_display_var = tk.StringVar(value="name")
            self.channel_name_radio = ttk.Radiobutton(log_display_frame, text=self.i18n.get("channel_name_radio"), variable=self.log_display_var, value="name")
            self.channel_name_radio.pack(side="left", padx=10)
            ToolTip(self.channel_name_radio, self.i18n.get("tooltip_channel_name"))
            self.channel_url_radio = ttk.Radiobutton(log_display_frame, text=self.i18n.get("channel_url_radio"), variable=self.log_display_var, value="url")
            self.channel_url_radio.pack(side="left", padx=10)
            ToolTip(self.channel_url_radio, self.i18n.get("tooltip_channel_url"))
            adv_frame = ttk.LabelFrame(options_frame, text=self.i18n.get("options_label")); adv_frame.pack(side="left", fill="x", expand=True, padx=(5,0))
            self.use_ocr_var = tk.BooleanVar(); self.ocr_check = ttk.Checkbutton(adv_frame, text=self.i18n.get("use_ocr_check"), variable=self.use_ocr_var, command=self.save_checkbox_settings)
            self.ocr_check.pack(side="left", padx=10)
            if not TESSERACT_INSTALLED: self.ocr_check.config(state=tk.DISABLED)
            ToolTip(self.ocr_check, self.i18n.get("tooltip_ocr"))
            self.skip_knowngood_urls_var = tk.BooleanVar(); self.skip_check = ttk.Checkbutton(adv_frame, text=self.i18n.get("skip_known_check"), variable=self.skip_knowngood_urls_var, command=self.save_checkbox_settings)
            self.skip_check.pack(side="left", padx=10)
            ToolTip(self.skip_check, self.i18n.get("tooltip_skip_known"))
            self.progress = ttk.Progressbar(self.main_frame, orient="horizontal", mode="determinate"); self.progress.pack(fill=tk.X, pady=5)
            self.log_view = scrolledtext.ScrolledText(self.main_frame, wrap=tk.WORD, height=12); self.log_view.pack(fill=tk.BOTH, expand=True)
            self.log_view.tag_config("green", foreground="#009900"); self.log_view.tag_config("red", foreground="#CC0000"); self.log_view.tag_config("yellow", foreground="#E69B00"); self.log_view.tag_config("info", foreground="#0073B7")
            self.log_view.bind("<Button-3>", self._show_log_context_menu)

        def _on_search_focus_in(self, event):
            if self.search_var.get() == self.i18n.get("search_label"):
                self.search_entry.delete(0, "end")
                self.search_entry.config(foreground="black")
        
        def _on_search_focus_out(self, event):
            if not self.search_var.get():
                self.search_entry.insert(0, self.i18n.get("search_label"))
                self.search_entry.config(foreground="grey")
        
        def _on_search_change(self, *args):
            query = self.search_var.get().lower()
            if self.is_running or not query or query == self.i18n.get("search_label").lower(): return
            output_file = self.output_var.get()
            if not os.path.exists(output_file): return
            self.log_view.delete('1.0', tk.END)
            try:
                with open(output_file, 'r', encoding='utf-8', errors='ignore') as f: content = f.read()
                found_streams = parse_m3u(content)
                results = [s for s in found_streams if query in s['title'].lower()]
                if results:
                    self.log(f"--- Found {len(results)} matches for '{query}' in {os.path.basename(output_file)} ---", "info")
                    for stream in results: self.log(f"[FOUND] {stream['title']}", "green")
                else:
                    self.log(f"--- No matches found for '{query}' ---", "yellow")
            except Exception as e:
                self.log(f"[!] Error reading or parsing output file for search: {e}", "red")

        def save_checkbox_settings(self):
            config = configparser.ConfigParser(); config.read(self.config_manager.path, encoding='utf-8')
            if not config.has_section('Settings'): config.add_section('Settings')
            config.set('Settings', 'useocr', 'yes' if self.use_ocr_var.get() else 'no')
            config.set('Settings', 'skipknowngoodurls', 'yes' if self.skip_knowngood_urls_var.get() else 'no')
            self.config_manager.save(config); self.load_settings()

        def browse_file(self):
            filename = filedialog.askopenfilename(title="Select M3U File", filetypes=(("M3U files", "*.m3u*"),("All files", "*.*")))
            if filename: self.input_var.set(filename)

        def recheck_output_file(self):
            self.start_processing(is_recheck=True)

        def open_website_finder(self): WebsiteFinderWindow(self)
        def open_links_manager(self): LinksManagerWindow(self)

        def _set_ui_state_for_checking(self, is_starting):
            """Locks or unlocks the UI elements based on whether a check is running."""
            # Determine the new state for most widgets
            state = tk.DISABLED if is_starting else tk.NORMAL
            readonly_state = tk.DISABLED if is_starting else 'readonly'

            # --- Control main window widgets ---
            self.start_button.config(state=state)
            self.browse_button.config(state=state)
            self.input_entry.config(state='normal' if not is_starting else 'disabled')
            self.output_entry.config(state='normal' if not is_starting else 'disabled')
            self.timeout_menu.config(state=readonly_state)
            self.workers_menu.config(state=readonly_state)
            self.channel_name_radio.config(state=state)
            self.channel_url_radio.config(state=state)
            self.skip_check.config(state=state)
            
            # Special handling for OCR check to respect Tesseract installation status
            if is_starting:
                self.ocr_check.config(state=tk.DISABLED)
            else:
                self.ocr_check.config(state=tk.NORMAL if TESSERACT_INSTALLED else tk.DISABLED)

            # Control the Stop button (it has the opposite logic)
            self.stop_button.config(state=tk.NORMAL if is_starting else tk.DISABLED)

            # --- Control specific, disruptive menu items ---
            self.file_menu.entryconfig(self.i18n.get("recheck_output"), state=state)
            self.tools_menu.entryconfig(self.i18n.get("website_finder"), state=state)
            self.db_menu.entryconfig(self.i18n.get("check_all_links"), state=state)
            self.about_menu.entryconfig(self.i18n.get("update"), state=state)

            # Control the entire language menu cascade, as changing language restarts the app
            self.menu_bar.entryconfig(self.i18n.get("language"), state=state)

        def start_database_check(self):
            if self.is_running: return
            self.log_view.delete('1.0', tk.END)
            self._set_ui_state_for_checking(True)
            self.log("--- Starting Database Check ---", "info")
            
            def do_db_check():
                self.log("[*] Loading all playlists from the database...", "info")
                links = self.links_db_manager.load().get('defaultlinks', {})
                if not links:
                    self.log("[!] No links found in the database.", "yellow")
                    self.after(0, self.stop_processing)
                    return
                all_content = ""
                for name, url in links.items():
                    try:
                        self.log(f"    -> Downloading '{name}'...", "info")
                        r = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=20)
                        r.raise_for_status()
                        all_content += r.content.decode('utf-8', errors='ignore') + "\n"
                    except Exception as e:
                        self.log(f"[!] Failed to download '{name}': {e}", "red")
                if all_content:
                    self.input_var.set("[Database Check]") 
                    all_streams = parse_m3u(all_content)
                    self.after(0, self._start_check_internal, all_streams, False)
                else:
                    self.log("[!] Database check failed: No valid playlists could be downloaded.", "red")
                    self.after(0, self.stop_processing)
            
            threading.Thread(target=do_db_check, daemon=True).start()

        def start_processing(self, is_recheck=False):
            if self.is_running: return
            input_path = self.output_var.get() if is_recheck else self.input_var.get()
            if not input_path or input_path == "[Database Check]":
                self.log("[!] Please provide a valid M3U file or URL.", "red")
                return
            self.log_view.delete('1.0', tk.END)
            self._set_ui_state_for_checking(True)
            if is_recheck:
                self.log(f"--- Starting Recheck of: {os.path.basename(input_path)} ---", "info")
            else:
                self.log("--- Starting Manual Check ---", "info")

            def do_start_check():
                try:
                    if urlparse(input_path).scheme in ('http', 'https'):
                        self.log(f"[*] Downloading: {input_path}", "info")
                        r = requests.get(input_path, headers={'User-Agent': USER_AGENT}, timeout=20)
                        r.raise_for_status()
                        content = r.content.decode('utf-8', errors='ignore')
                    else:
                        if not os.path.exists(input_path):
                            self.after(0, lambda: messagebox.showerror("File Not Found", f"The file '{input_path}' does not exist."))
                            self.after(0, self.stop_processing)
                            return
                        self.log(f"[*] Reading local file: {input_path}", "info")
                        with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                    
                    all_streams = parse_m3u(content)
                    self.after(0, self._start_check_internal, all_streams, is_recheck)

                except requests.RequestException as e:
                    self.log(f"\n[!] Error downloading playlist: {e}", "red")
                    self.after(0, self.stop_processing)
                except Exception as e:
                    self.log(f"\n[!] Error loading playlist: {e}", "red")
                    self.after(0, self.stop_processing)

            threading.Thread(target=do_start_check, daemon=True).start()

        def _start_check_internal(self, all_streams, is_recheck):
            self.is_running = True
            self.current_check_id = time.time() 
            self.is_rechecking = is_recheck
            self.search_entry.config(state=tk.DISABLED)
            output_path = self.output_var.get().strip()

            if not output_path:
                self.log("[!] Please provide an Output File name.", "red")
                self.stop_processing()
                return

            self.progress['value'] = 0
            self.processed_count = 0
            self.uncheckable_count = 0
            self.online_count = 0
            self.log_url_map.clear()
            self.known_good_urls.clear()
            global OCR_FAILED_ONCE
            OCR_FAILED_ONCE = False
            
            logging.info(f"--- Starting new check with ID: {self.current_check_id} ---")

            if self.skip_knowngood_urls_var.get() and not self.is_rechecking:
                if os.path.exists(output_path):
                    output_filename = os.path.basename(output_path)
                    self.log(f"[*] Comparing against output file ('{output_filename}') to skip duplicates...", "info")
                    try:
                        with open(output_path, 'r', encoding='utf-8', errors='ignore') as f: content = f.read()
                        self.known_good_urls = {s['url'] for s in parse_m3u(content)}
                        self.log(f"    -> Found {len(self.known_good_urls)} URLs in the output file to be skipped.", "info")
                    except Exception as e:
                        self.log(f"[!] Could not read existing output file to check for duplicates: {e}", "yellow")

            self.streams_to_check = [s for s in all_streams if s['url'] not in self.known_good_urls]
            
            if self.known_good_urls:
                skipped_count = len(all_streams) - len(self.streams_to_check)
                if skipped_count > 0:
                    self.log(f"[*] Skipped {skipped_count} streams that are already in the output file.", "info")

            if not self.streams_to_check:
                log_msg = "[!] No new streams to check." if not self.is_rechecking else "[!] No streams found in file to recheck."
                self.log(log_msg, "yellow")
                self.stop_processing()
                return
            
            part_file_path = f"{output_path}.part"; uncheckable_file_path = "uncheckable.m3u"
            self.journal_file = open(part_file_path, "w", encoding='utf-8-sig'); self.uncheckable_file = open(uncheckable_file_path, "w", encoding='utf-8-sig')
            write_m3u_header(self.journal_file); write_m3u_header(self.uncheckable_file)
            
            self.total_stream_count = len(self.streams_to_check)
            self.progress['maximum'] = self.total_stream_count
            self.remaining_label.config(text=f"{self.i18n.get('remaining_label')} {self.total_stream_count}");
            self.log(f"[*] Found {self.total_stream_count} new streams to check. Starting...", "info")
            self._monitor_workers()
        
        def stop_processing(self):
            self.is_running = False
            self.current_check_id = None 
            self.log(">>> Sending stop signal and cleaning up...", "yellow")
            
            active_procs = list(self.active_processes.items())
            self.active_processes.clear()
            for pid, data in active_procs:
                self._force_kill_worker(pid, data)
            self.log(">>> All workers terminated.", "yellow")

            if self.journal_file:
                self.journal_file.close()
                self.journal_file = None
            if self.uncheckable_file:
                self.uncheckable_file.close()
                self.uncheckable_file = None
            
            output_path = self.output_var.get().strip(); part_file_path = f"{output_path}.part"
            
            if self.is_rechecking:
                if os.path.exists(part_file_path) and os.path.getsize(part_file_path) > 15:
                    shutil.move(part_file_path, output_path)
                    self.log(f"[+] Playlist cleaned and saved to: {output_path}", "green")
                else: 
                    if os.path.exists(output_path): os.remove(output_path)
                    if os.path.exists(part_file_path): os.remove(part_file_path)
                    self.log(f"[!] No working streams found. Output file '{output_path}' removed.", "yellow")
            else:
                if os.path.exists(part_file_path) and os.path.getsize(part_file_path) > 15:
                    with open(part_file_path, 'r', encoding='utf-8-sig') as part_f:
                        new_content = part_f.read()
                    
                    new_streams_count = len(re.findall(r'#EXTINF', new_content))
                    output_needs_header = not os.path.exists(output_path) or os.path.getsize(output_path) == 0
                    
                    with open(output_path, 'a', encoding='utf-8-sig') as main_f:
                        if output_needs_header:
                            main_f.write("#EXTM3U\n\n")
                        part_content_no_header = new_content.replace("#EXTM3U\n\n", "", 1)
                        main_f.write(part_content_no_header)
                    
                    self.log(f"[+] Appended {new_streams_count} new working streams to: {output_path}", "green")
                
                if os.path.exists(part_file_path):
                    os.remove(part_file_path)

            if self.uncheckable_count > 0: self.log(f"[!] {self.uncheckable_count} streams were saved to 'uncheckable.m3u'", "yellow")
            
            self.remaining_label.config(text=f"{self.i18n.get('remaining_label')} 0")
            self._set_ui_state_for_checking(False)
            
            search_file_exists = os.path.exists(self.output_var.get()) and os.path.getsize(self.output_var.get()) > 0
            self.search_entry.config(state='normal' if search_file_exists else 'disabled')

            if self.input_var.get() == "[Database Check]":
                self.input_var.set("")

        def _monitor_workers(self):
            if not self.is_running:
                return
                
            pids_to_remove = []
            now = time.time()
            for pid, data in self.active_processes.items():
                if data['proc'].poll() is not None:
                    self._process_result(data)
                    pids_to_remove.append(pid)
                elif (now - data['start_time']) > WORKER_PROCESS_TIMEOUT_SECONDS:
                    logging.warning(f"Worker PID {pid} for URL {data['stream_info']['url']} timed out. Forcing termination.")
                    self._force_kill_worker(pid, data)
                    self.after(0, self._handle_worker_failure, data['stream_info'], "(Timeout)", data['check_id'])
                    pids_to_remove.append(pid)
            
            for pid in pids_to_remove:
                if pid in self.active_processes:
                    del self.active_processes[pid]
                    
            max_workers = int(self.workers_var.get())
            if len(self.active_processes) < max_workers and self.streams_to_check:
                self._launch_worker(self.streams_to_check.pop(0), self.current_check_id)
                
            if not self.streams_to_check and not self.active_processes:
                self.log("\n--- Check Complete ---", "info")
                self.stop_processing()
                return
                
            self.after(100, self._monitor_workers)

        def _handle_worker_failure(self, stream_info, reason, check_id):
            if check_id != self.current_check_id:
                logging.warning(f"Discarding stale worker failure from a previous check ({check_id}).")
                return

            self.processed_count += 1
            self.progress['value'] = self.processed_count
            self.remaining_label.config(text=f"{self.i18n.get('remaining_label')} {self.total_stream_count - self.processed_count}")
            display_text = stream_info['title'] if self.log_display_var.get() == 'name' else stream_info['url']
            stream_id_tag = f"stream_{self.processed_count}"
            self.log_url_map[stream_id_tag] = stream_info['url']
            self.log(f"[{'OFF ' + reason:^15}] {display_text}", "red", stream_id=stream_id_tag)
            logging.info(f"Stream offline: [{reason}] {stream_info['title']} ({stream_info['url']})")

        def _launch_worker(self, stream_info, check_id):
            def run_in_thread():
                try:
                    if check_id != self.current_check_id: return

                    final_url = sanitize_url_aggressively(stream_info['url']) if stream_info.get('is_retry') else stream_info['url']
                    
                    if 'youtube.com/' in final_url or 'youtu.be/' in final_url:
                        try:
                            yt_cmd = [YT_DLP_PATH, '--get-url', final_url]
                            logging.debug(f"Executing yt-dlp command: {' '.join(yt_cmd)}")
                            result = subprocess.run(yt_cmd, capture_output=True, text=True, timeout=YT_DLP_TIMEOUT_SECONDS)
                            if result.returncode == 0 and result.stdout.strip():
                                final_url = result.stdout.strip().splitlines()[0]
                                logging.debug(f"yt-dlp found direct URL: {final_url}")
                            else:
                                raise RuntimeError(f"yt-dlp failed: {result.stderr.strip()}")
                        except Exception as e:
                            logging.error(f"yt-dlp failed for {stream_info['url']}: {e}")
                            self.after(0, self._handle_worker_failure, stream_info, "(YouTube Error)", check_id)
                            return
                    
                    check_type = None
                    for pattern, type_ in self.stream_patterns.items():
                        if pattern in final_url: 
                            check_type = type_
                            break
                    
                    if check_type is None and re.search(r':\d+(?:/[^.]*)?$', final_url):
                        check_type = 'audio'

                    if check_type is None:
                        probe_result = self._get_stream_type(final_url)
                        check_type = 'video' if probe_result == 'video' else 'audio'
                    
                    self.after(0, self._schedule_process, stream_info, final_url, check_type, check_id)
                
                except Exception as e:
                    logging.error(f"Error in worker thread for {stream_info['url']}: {e}", exc_info=True)
                    self.after(0, self._handle_worker_failure, stream_info, "(Launch Error)", check_id)
            
            threading.Thread(target=run_in_thread, daemon=True).start()

        def _schedule_process(self, stream_info, final_url, check_type, check_id):
            if check_id != self.current_check_id:
                logging.warning(f"Discarding stale process schedule from a previous check ({check_id}).")
                return

            temp_file = None
            try:
                proc = None; probe_type = 'ffprobe'
                use_ffmpeg = check_type == 'video' and self.use_ocr_var.get()
                
                popen_kwargs = {'stdin': subprocess.DEVNULL, 'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE, 'text': True, 'errors': 'ignore'}
                if os.name == 'posix': popen_kwargs['start_new_session'] = True
                else: popen_kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

                if use_ffmpeg:
                    probe_type = 'ffmpeg'
                    with tempfile.NamedTemporaryFile(suffix=".mp4", prefix=TEMP_FILE_PREFIX, delete=False) as tf: temp_file = tf.name
                    
                    ffmpeg_cmd = [FFMPEG_PATH, '-y', '-hide_banner'] + ['-user_agent', USER_AGENT, '-timeout', str(build_timeout_config(int(self.timeout_var.get()))['network_timeout_us'])] + build_timeout_config(int(self.timeout_var.get()))['ffmpeg_flags'] + ['-t', str(DEFAULT_CAPTURE_DURATION), '-i', final_url] + ['-c', 'copy', '-bsf:a', 'aac_adtstoasc', temp_file]
                    proc = subprocess.Popen(ffmpeg_cmd, **popen_kwargs)
                else:
                    user_agent = AUDIO_USER_AGENT if check_type == 'audio' else USER_AGENT
                    ffprobe_cmd = [FFPROBE_PATH, '-v', 'error', '-user_agent', user_agent, '-timeout', str(build_timeout_config(int(self.timeout_var.get()))['network_timeout_us']), '-i', final_url]
                    proc = subprocess.Popen(ffprobe_cmd, **popen_kwargs)
                
                self.active_processes[proc.pid] = {"proc": proc, "stream_info": stream_info, "temp_file": temp_file, "start_time": time.time(), "check_type": check_type, "probe_type": probe_type, "check_id": check_id}
            
            except Exception as e:
                logging.error(f"Error scheduling process for {stream_info['url']}: {e}", exc_info=True)
                if temp_file and os.path.exists(temp_file):
                    try: os.remove(temp_file)
                    except OSError: pass
                self.after(0, self._handle_worker_failure, stream_info, "(Schedule Error)", check_id)

        def _process_result(self, data):
            check_id = data['check_id']
            if check_id != self.current_check_id:
                logging.warning(f"Discarding stale process result from a previous check ({check_id}).")
                if data['temp_file'] and os.path.exists(data['temp_file']):
                    try: os.remove(data['temp_file'])
                    except OSError: pass
                return

            proc = data['proc']; stream_info = data['stream_info']; temp_file = data['temp_file']
            display_text = stream_info['title'] if self.log_display_var.get() == 'name' else stream_info['url']
            tag = "red"; detailed_status = "OFF"
            
            try:
                stdout, stderr = proc.communicate()
                logging.debug(f"[{data['probe_type'].upper()}] stdout for {stream_info['url']}:\n{stdout}")
                logging.debug(f"[{data['probe_type'].upper()}] stderr for {stream_info['url']}:\n{stderr}")

                if data['probe_type'] == 'ffprobe':
                    if proc.returncode == 0: detailed_status = "ON"
                    else: detailed_status = "OFF (Probe Error)"
                else: # ffmpeg
                    if proc.returncode == 0 and os.path.exists(temp_file) and os.path.getsize(temp_file) >= MIN_FILE_SIZE_BYTES:
                        if data['check_type'] == 'video' and self.use_ocr_var.get(): 
                            detailed_status = self._perform_ocr_check(temp_file)
                        else: 
                            detailed_status = "ON"
                    else: 
                        detailed_status = "OFF (Capture Error)"
            except Exception as e: 
                detailed_status = "OFF (Processing Error)"
                logging.error(f"Error processing result for {stream_info['url']}: {e}", exc_info=True)
                
            self.processed_count += 1
            self.progress['value'] = self.processed_count
            self.remaining_label.config(text=f"{self.i18n.get('remaining_label')} {self.total_stream_count - self.processed_count}")
            
            gui_status_text = "OFF"
            if "ON" in detailed_status:
                self.online_count += 1
                if data['check_type'] == 'audio': stream_info['group'] = 'Radios'
                write_m3u_entry(self.journal_file, stream_info)
                tag = "green"; gui_status_text = "ON"
            else:
                url = stream_info['url']
                if len(url) > UNCHECKABLE_URL_LENGTH_THRESHOLD or any(kw in url.lower() for kw in UNCHECKABLE_KEYWORDS):
                    write_m3u_entry(self.uncheckable_file, stream_info)
                    self.uncheckable_count += 1
                    
            stream_id_tag = f"stream_{self.processed_count}"
            self.log_url_map[stream_id_tag] = stream_info['url']
            self.log(f"[{gui_status_text:^15}] {display_text}", tag, stream_id=stream_id_tag)
            
            if temp_file and os.path.exists(temp_file):
                try: os.remove(temp_file)
                except OSError as e: logging.warning(f"Could not remove temp file {temp_file}: {e}")
                
# --- CLI APPLICATION CLASS ---
class AppCLI(CheckerBase):
    def __init__(self, args):
        super().__init__()
        self.args = args
        self.links_db_manager = IniManager(LINKS_DB_PATH)
        self.total_streams = 0

    def log(self, message, tag=None):
        color_map = {"green": Fore.GREEN, "red": Fore.RED, "yellow": Fore.YELLOW, "info": Fore.CYAN}
        color = color_map.get(tag, "")
        with self.lock:
            print(f"{color}{message}{Style.RESET_ALL}")

    def run(self):
        print(f"{Style.BRIGHT}{Fore.CYAN}--- IPTV-Check v{VERSION} (CLI Mode) ---{Style.RESET_ALL}")
        signal.signal(signal.SIGINT, self._signal_handler)
        content = self._get_content()
        if not content: return
        all_streams = parse_m3u(content)
        if not all_streams:
            self.log("[!] No streams found in the provided source.", "yellow")
            return
        is_recheck = bool(self.args.recheck)
        output_path = self.args.recheck if is_recheck else self.args.output
        known_good_urls = set()
        if not is_recheck and not self.args.no_skip:
            if os.path.exists(output_path):
                self.log(f"[*] Comparing against output file ('{os.path.basename(output_path)}') to skip duplicates...", "yellow")
                try:
                    with open(output_path, 'r', encoding='utf-8', errors='ignore') as f: existing_content = f.read()
                    known_good_urls = {s['url'] for s in parse_m3u(existing_content)}
                    self.log(f"    -> Found {len(known_good_urls)} URLs in the output file to be skipped.", "info")
                except Exception as e:
                    self.log(f"[!] Could not read existing output file: {e}", "red")
        self.streams_to_check = [s for s in all_streams if s['url'] not in known_good_urls]
        if known_good_urls:
            skipped_count = len(all_streams) - len(self.streams_to_check)
            if skipped_count > 0:
                self.log(f"[*] Skipped {skipped_count} streams that are already in the output file.", "info")
        if not self.streams_to_check:
            self.log("[!] No new streams to check.", "yellow")
            return
        self.log(f"[*] Found {len(self.streams_to_check)} new streams to check. Starting...", "green")
        part_file_path = f"{output_path}.part"; uncheckable_file_path = "uncheckable.m3u"
        self.journal_file = open(part_file_path, "w", encoding='utf-8-sig')
        self.uncheckable_file = open(uncheckable_file_path, "w", encoding='utf-8-sig')
        write_m3u_header(self.journal_file); write_m3u_header(self.uncheckable_file)
        self.total_streams = len(self.streams_to_check)
        self.is_running = True
        self.current_check_id = time.time()
        
        queue = self.streams_to_check[:]
        threads = []
        for _ in range(self.args.workers):
            thread = threading.Thread(target=self._worker, args=(queue,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        while any(t.is_alive() for t in threads):
            time.sleep(0.5)
            # This loop allows Ctrl+C to be detected
        
        self.is_running = False # Ensure all threads stop after finishing their current item
        for t in threads:
            t.join()

        self._finalize_check(output_path, is_recheck)

    def _signal_handler(self, sig, frame):
        if self.is_running:
            print(f"\n{Style.BRIGHT}{Fore.YELLOW}>>> Ctrl+C detected. Stopping launch of new checks. Please wait for active checks to finish...{Style.RESET_ALL}")
            self.is_running = False

    def _get_content(self):
        content = ""
        input_path = self.args.file or self.args.recheck
        try:
            if input_path:
                if urlparse(input_path).scheme in ('http', 'https'):
                    print(f"[*] Downloading: {input_path}")
                    r = requests.get(input_path, headers={'User-Agent': USER_AGENT}, timeout=20); r.raise_for_status()
                    content = r.content.decode('utf-8', errors='ignore')
                else:
                    operation_message = "Re-checking file" if self.args.recheck else "Reading local file"
                    print(f"[*] {operation_message}: {input_path}")
                    with open(input_path, 'r', encoding='utf-8', errors='ignore') as f: content = f.read()
            elif self.args.database:
                print("[*] Loading all playlists from the database...")
                links = self.links_db_manager.load().get('defaultlinks', {})
                if not links:
                    print(f"{Fore.RED}[!] No links found in the database.{Style.RESET_ALL}"); return None
                for name, url in links.items():
                    try:
                        print(f"    -> Downloading '{name}'...")
                        r = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=20); r.raise_for_status()
                        content += r.content.decode('utf-8', errors='ignore') + "\n"
                    except Exception as e:
                        print(f"{Fore.RED}[!] Failed to download '{name}': {e}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Style.BRIGHT}{Fore.RED}\n[!] Error loading playlist: {e}{Style.RESET_ALL}"); return None
        return content

    def _worker(self, queue):
        while self.is_running:
            try:
                with self.lock:
                    if not queue: break
                    stream_info = queue.pop(0)
            except IndexError:
                break
            
            if not self.is_running: break

            final_url, check_type = self._prepare_stream(stream_info)
            if final_url is None: continue
            self._execute_check(stream_info, final_url, check_type)

    def _prepare_stream(self, stream_info):
        try:
            final_url = sanitize_url_aggressively(stream_info['url'])
            if 'youtube.com/' in final_url or 'youtu.be/' in final_url:
                yt_cmd = [YT_DLP_PATH, '--get-url', final_url]
                result = subprocess.run(yt_cmd, capture_output=True, text=True, timeout=YT_DLP_TIMEOUT_SECONDS)
                if result.returncode == 0 and result.stdout.strip():
                    final_url = result.stdout.strip().splitlines()[0]
                else: raise RuntimeError(f"yt-dlp failed: {result.stderr.strip()}")
            check_type = None
            for pattern, type_ in self.stream_patterns.items():
                if pattern in final_url: check_type = type_; break
            if check_type is None and re.search(r':\d+(?:/[^.]*)?$', final_url): check_type = 'audio'
            if check_type is None:
                probe_result = self._get_stream_type(final_url)
                check_type = 'video' if probe_result == 'video' else 'audio'
            return final_url, check_type
        except Exception as e:
            logging.error(f"Error preparing stream {stream_info['url']}: {e}")
            self._handle_cli_failure(stream_info, "(Prepare Error)")
            return None, None
            
    def _execute_check(self, stream_info, final_url, check_type):
        temp_file = None; detailed_status = "OFF"
        try:
            use_ffmpeg = check_type == 'video' and self.args.ocr
            popen_kwargs = {'stdin': subprocess.DEVNULL, 'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE, 'text': True, 'errors': 'ignore'}
            if os.name == 'posix': popen_kwargs['start_new_session'] = True
            else: popen_kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

            if use_ffmpeg:
                with tempfile.NamedTemporaryFile(suffix=".mp4", prefix=TEMP_FILE_PREFIX, delete=False) as tf: temp_file = tf.name
                ffmpeg_cmd = [FFMPEG_PATH, '-y', '-hide_banner'] + ['-user_agent', USER_AGENT, '-timeout', str(build_timeout_config(self.args.timeout)['network_timeout_us'])] + build_timeout_config(self.args.timeout)['ffmpeg_flags'] + ['-t', str(DEFAULT_CAPTURE_DURATION), '-i', final_url] + ['-c', 'copy', '-bsf:a', 'aac_adtstoasc', temp_file]
                proc = subprocess.Popen(ffmpeg_cmd, **popen_kwargs)
            else:
                user_agent = AUDIO_USER_AGENT if check_type == 'audio' else USER_AGENT
                ffprobe_cmd = [FFPROBE_PATH, '-v', 'error', '-user_agent', user_agent, '-timeout', str(build_timeout_config(self.args.timeout)['network_timeout_us']), '-i', final_url]
                proc = subprocess.Popen(ffprobe_cmd, **popen_kwargs)
            
            stdout, stderr = proc.communicate(timeout=WORKER_PROCESS_TIMEOUT_SECONDS)
            
            if proc.returncode == 0:
                if use_ffmpeg and os.path.exists(temp_file) and os.path.getsize(temp_file) >= MIN_FILE_SIZE_BYTES:
                    detailed_status = self._perform_ocr_check(temp_file)
                elif not use_ffmpeg:
                    detailed_status = "ON"
        except subprocess.TimeoutExpired:
            proc.kill()
            detailed_status = "OFF (Timeout)"
        except Exception as e:
            logging.error(f"Error executing check for {final_url}: {e}")
            detailed_status = "OFF (Execution Error)"
        finally:
            if temp_file and os.path.exists(temp_file):
                try: os.remove(temp_file)
                except OSError: pass
        
        self._handle_cli_result(stream_info, detailed_status, check_type)

    def _handle_cli_failure(self, stream_info, reason):
        with self.lock:
            self.processed_count += 1
            display_text = stream_info['title'] if self.args.log_format == 'name' else stream_info['url']
            self.log(f"[{Fore.RED}{reason:^15}{Fore.RESET}] {display_text}")

    def _handle_cli_result(self, stream_info, detailed_status, check_type):
        with self.lock:
            self.processed_count += 1
            display_text = stream_info['title'] if self.args.log_format == 'name' else stream_info['url']
            
            if "ON" in detailed_status:
                self.online_count += 1
                if check_type == 'audio': stream_info['group'] = 'Radios'
                write_m3u_entry(self.journal_file, stream_info)
                self.log(f"[{Fore.GREEN}{'ON':^15}{Fore.RESET}] {display_text}", tag="green")
            else:
                self.log(f"[{Fore.RED}{detailed_status:^15}{Fore.RESET}] {display_text}", tag="red")
                url = stream_info['url']
                if len(url) > UNCHECKABLE_URL_LENGTH_THRESHOLD or any(kw in url.lower() for kw in UNCHECKABLE_KEYWORDS):
                    write_m3u_entry(self.uncheckable_file, stream_info)
                    self.uncheckable_count += 1
    
    def _finalize_check(self, output_path, is_recheck):
        print(f"\n{Style.BRIGHT}{Fore.CYAN}--- Check Complete ---{Style.RESET_ALL}")
        
        if self.journal_file: self.journal_file.close()
        if self.uncheckable_file: self.uncheckable_file.close()
        
        part_file_path = f"{output_path}.part"
        
        if is_recheck:
            if os.path.exists(part_file_path) and os.path.getsize(part_file_path) > 15:
                shutil.move(part_file_path, output_path)
                print(f"{Fore.GREEN}[+] Playlist cleaned and saved to: {output_path}{Style.RESET_ALL}")
            else:
                if os.path.exists(output_path): os.remove(output_path)
                if os.path.exists(part_file_path): os.remove(part_file_path)
                print(f"{Fore.YELLOW}[!] No working streams found. Output file '{output_path}' removed.{Style.RESET_ALL}")
        else:
            if os.path.exists(part_file_path) and os.path.getsize(part_file_path) > 15:
                with open(part_file_path, 'r', encoding='utf-8-sig') as part_f: new_content = part_f.read()
                output_needs_header = not os.path.exists(output_path) or os.path.getsize(output_path) == 0
                with open(output_path, 'a', encoding='utf-8-sig') as main_f:
                    if output_needs_header: main_f.write("#EXTM3U\n\n")
                    part_content_no_header = new_content.replace("#EXTM3U\n\n", "", 1)
                    main_f.write(part_content_no_header)
                print(f"{Fore.GREEN}[+] Appended {self.online_count} new working streams to: {output_path}{Style.RESET_ALL}")
        
        if os.path.exists(part_file_path): os.remove(part_file_path)
        if self.uncheckable_count > 0: print(f"{Fore.YELLOW}[!] {self.uncheckable_count} streams were saved to 'uncheckable.m3u'{Style.RESET_ALL}")
        
        print(f"\n{Style.BRIGHT}Summary: {self.online_count} Online, {self.total_streams - self.online_count} Offline, {self.total_streams} Total.{Style.RESET_ALL}")

# --- MAIN APPLICATION ENTRY POINT ---
def main():
    setup_logging(); cleanup_stale_temp_files(); load_languages()
    missing_essential, missing_optional = check_dependencies()

    parser = argparse.ArgumentParser(description=f"IPTV-Check v{VERSION}.", add_help=False)
    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show this help message and exit.')
    parser.add_argument('-gui', '--gui', action='store_true', help='Launch the graphical user interface.')
    input_group = parser.add_argument_group('CLI Input Options (choose one)')
    input_group = input_group.add_mutually_exclusive_group()
    input_group.add_argument('-f', '--file', help='Path or URL to the M3U playlist file.')
    input_group.add_argument('-d', '--database', action='store_true', help='Use the default links database as input.')
    input_group.add_argument('-r', '--recheck', help='Re-check an existing output file (e.g., updated.m3u).')
    cli_opts = parser.add_argument_group('CLI General Options')
    cli_opts.add_argument('-o', '--output', default='updated.m3u', help='Output file for working streams.')
    cli_opts.add_argument('-w', '--workers', type=int, default=10, help='Number of parallel workers (1-20).')
    cli_opts.add_argument('-t', '--timeout', type=int, default=5, help='Network timeout in seconds for each stream.')
    cli_opts.add_argument('--log-format', choices=['name', 'url'], default='name', help='Log output format for the CLI progress bar.')
    cli_opts.add_argument('--ocr', action='store_true', help='Enable OCR checking for video streams.')
    cli_opts.add_argument('--no-skip', action='store_true', help='Disable skipping of known good URLs found in the output file.')
    args = parser.parse_args()

    is_cli_mode = args.file or args.database or args.recheck
    
    if args.gui:
        if not GUI_AVAILABLE: 
            print(f"{Fore.RED}{Style.BRIGHT}[!] GUI mode requires Tkinter, which could not be imported.{Style.RESET_ALL}"); sys.exit(1)
        if missing_essential:
            error_msg = (f"FATAL ERROR: The following required programs are not installed or not in your system's PATH:\n\n"
                         f"{', '.join(missing_essential)}\n\n"
                         "Please install them and ensure they are accessible to run the application.")
            logging.critical(f"Missing essential dependencies: {', '.join(missing_essential)}")
            root = tk.Tk(); root.withdraw(); messagebox.showerror("Fatal Dependency Error", error_msg)
            sys.exit(1)
        app = AppGUI(args, missing_optional)
        app.mainloop()
    elif is_cli_mode:
        if missing_essential:
            error_msg = (f"FATAL ERROR: The following required programs are not installed or not in your system's PATH:\n\n"
                         f"{', '.join(missing_essential)}\n\n"
                         "Please install them and ensure they are accessible to run the application.")
            logging.critical(f"Missing essential dependencies: {', '.join(missing_essential)}")
            print(f"{Fore.RED}{Style.BRIGHT}{error_msg}{Style.RESET_ALL}")
            sys.exit(1)
        if args.recheck and args.output != 'updated.m3u' and not any(arg in sys.argv for arg in ['-o', '--output']):
            args.output = args.recheck
        
        cli_app = AppCLI(args)
        cli_app.run()

    else:
        parser.print_help()
        print("\nTo start the graphical interface, run:\npython3 iptv_check.py --gui")
        sys.exit(0)

if __name__ == "__main__":
    main()
