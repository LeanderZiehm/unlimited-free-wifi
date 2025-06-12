import subprocess
import sys
import re
from datetime import datetime
from pathlib import Path

# === Paths ===
SCRIPT_DIR = Path(__file__).resolve().parent
LOG_FILE = SCRIPT_DIR / "mac_change_log.txt"

# === Utilities ===
def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode().strip()
    except subprocess.CalledProcessError:
        return ""

def get_wifi_interface():
    output = run_cmd("nmcli device status")
    for line in output.splitlines():
        if "wifi" in line and ("connected" in line or "disconnected" in line):
            return line.split()[0]
    print("[-] Could not find a Wi-Fi interface.")
    sys.exit(1)

def get_connected_ssid(interface):
    ssid = run_cmd("nmcli -t -f active,ssid dev wifi | grep '^yes' | cut -d: -f2")
    if not ssid:
        print("[-] Not connected to any Wi-Fi network.")
        sys.exit(1)
    return ssid

def get_current_mac(interface):
    return run_cmd(f"cat /sys/class/net/{interface}/address")

def change_mac(interface):
    old_mac = get_current_mac(interface)
    print(f"[+] Changing MAC for {interface}...")
    run_cmd(f"sudo ip link set {interface} down")
    run_cmd(f"sudo macchanger -r {interface}")
    run_cmd(f"sudo ip link set {interface} up")
    new_mac = get_current_mac(interface)
    return old_mac, new_mac

def reconnect_wifi(interface, ssid):
    print(f"[+] Reconnecting to open Wi-Fi: {ssid}")
    run_cmd("nmcli device wifi rescan")
    run_cmd(f"nmcli device wifi connect '{ssid}' ifname {interface}")

def get_local_ip(interface):
    output = run_cmd(f"ip -4 addr show {interface}")
    match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', output)
    return match.group(1) if match else "Unknown"

def get_signal_strength(ssid):
    output = run_cmd("nmcli -f SSID,SIGNAL dev wifi")
    for line in output.splitlines():
        if ssid in line:
            try:
                return int(line.strip().split()[-1])
            except:
                break
    return "Unknown"

def get_public_ip():
    return run_cmd("curl -s https://api.ipify.org") or "Unknown"

def log_mac_change(interface, ssid, old_mac, new_mac):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    local_ip = get_local_ip(interface)
    signal = get_signal_strength(ssid)
    public_ip = get_public_ip()

    log_entry = (
        f"[{timestamp}] Interface: {interface}, Wi-Fi: {ssid}, "
        f"Old MAC: {old_mac}, New MAC: {new_mac}, "
        f"Local IP: {local_ip}, Signal: {signal}%, Public IP: {public_ip}\n"
    )

    print(log_entry.strip())
    try:
        with open(LOG_FILE, "a") as log:
            log.write(log_entry)
    except Exception as e:
        print(f"[!] Could not write to log file: {e}")

def open_captive_portal():
    print("[+] Trying to open captive portal...")
    run_cmd("xdg-open http://neverssl.com")

# === Main ===
if __name__ == "__main__":
    print("Wifi Free Forever Started")
    iface = get_wifi_interface()
    print(iface)
    ssid = get_connected_ssid(iface)
    print(ssid)
    old_mac, new_mac = change_mac(iface)
    reconnect_wifi(iface, ssid)
    log_mac_change(iface, ssid, old_mac, new_mac)
    open_captive_portal()
    print("[+] MAC spoof complete. Please accept portal terms in your browser.")
