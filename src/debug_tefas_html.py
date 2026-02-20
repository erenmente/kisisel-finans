import requests
import sys
import urllib3

sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod=TTE"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.google.com/",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
}

try:
    resp = requests.get(url, headers=headers, verify=False, timeout=10)
    with open("tefas_debug.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("HTML saved to tefas_debug.html")
except Exception as e:
    print(f"Error: {e}")
