import os
import sys
import subprocess
import time
from colorama import Fore, Style, init

init(autoreset=True)

def clear_screen():
    os.system('cls' if sys.platform == 'win32' else 'clear')

def get_terminal_width():
    try:
        import shutil
        return shutil.get_terminal_size().columns
    except:
        return 80

def print_banner():
    banner = f"""
{Fore.LIGHTBLUE_EX}██╗   ██╗██████╗ ██████╗ ██╗  ██╗
{Fore.LIGHTBLUE_EX}██║   ██║██╔══██╗██╔══██╗██║  ██║
{Fore.LIGHTBLUE_EX}██║   ██║██████╔╝██║  ██║███████║
{Fore.LIGHTBLUE_EX}██║   ██║██╔═══╝ ██║  ██║██╔══██║
{Fore.LIGHTBLUE_EX}╚██████╔╝██║     ██████╔╝██║  ██║
{Fore.LIGHTBLUE_EX} ╚═════╝ ╚═╝     ╚═════╝ ╚═╝  ╚═╝
{Fore.LIGHTBLUE_EX}         Telegram - @updh1
{Style.RESET_ALL}
"""
    width = get_terminal_width()
    lines = banner.split('\n')
    centered_lines = []
    for line in lines:
        if line.strip():
            clean_line = line
            padding = (width - len(clean_line)) // 2
            centered_lines.append(' ' * max(0, padding) + line)
        else:
            centered_lines.append(line)
    
    print('\n'.join(centered_lines))

def print_menu():
    print()
    print(f"  [1] Hotmail Inboxer")
    print(f"  [2] Mix Mail Checker")
    print(f"  [3] Exit")
    print()

def run_hotmail_checker():
    try:
        print(f"\n{Fore.YELLOW}[*] Starting Hotmail Checker...{Style.RESET_ALL}\n")
        time.sleep(1)
        subprocess.run([sys.executable, "hotmail_checker.py"])
    except FileNotFoundError:
        print(f"\n{Fore.RED}[!] hotmail_checker.py not found{Style.RESET_ALL}")
        input(f"{Fore.YELLOW}[*] Press Enter to continue...{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}[!] Error: {e}{Style.RESET_ALL}")
        input(f"{Fore.YELLOW}[*] Press Enter to continue...{Style.RESET_ALL}")

def run_mix_checker():
    try:
        print(f"\n{Fore.YELLOW}[*] Starting Mix Mail Checker...{Style.RESET_ALL}\n")
        time.sleep(1)
        subprocess.run([sys.executable, "imap.py"])
    except FileNotFoundError:
        print(f"\n{Fore.RED}[!] imap.py not found{Style.RESET_ALL}")
        input(f"{Fore.YELLOW}[*] Press Enter to continue...{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}[!] Error: {e}{Style.RESET_ALL}")
        input(f"{Fore.YELLOW}[*] Press Enter to continue...{Style.RESET_ALL}")

def main():
    while True:
        clear_screen()
        print_banner()
        print_menu()
        
        try:
            choice = input(f"{Fore.CYAN}Select option [1-3]: {Style.RESET_ALL}").strip()
            
            if choice == "1":
                clear_screen()
                run_hotmail_checker()
            elif choice == "2":
                clear_screen()
                run_mix_checker()
            elif choice == "3":
                print(f"\n{Fore.GREEN}[*] Goodbye!{Style.RESET_ALL}")
                sys.exit(0)
            else:
                print(f"{Fore.RED}[!] Invalid option!{Style.RESET_ALL}")
                time.sleep(1)
                
        except KeyboardInterrupt:
            print(f"\n{Fore.RED}[!] Interrupted by user{Style.RESET_ALL}")
            sys.exit(0)
        except Exception as e:
            print(f"{Fore.RED}[!] Error: {e}{Style.RESET_ALL}")
            time.sleep(2)

if __name__ == "__main__":
    main()