import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod=TTE"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    resp = requests.get(url, headers=headers, verify=False, timeout=10)
    with open("src/tefas_latest.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("Saved to src/tefas_latest.html")
except Exception as e:
    print(f"Error: {e}")
