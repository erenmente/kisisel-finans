import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod=TTE"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

s = requests.Session()
s.headers.update(headers)

# First visit the home page or list page to get cookies
try:
    print("Visiting main page...")
    s.get("https://www.tefas.gov.tr/FonAnaliz.aspx", verify=False, timeout=10)
    
    print("Visiting fund page...")
    resp = s.get(url, verify=False, timeout=10)
    
    if "Son Fiyat" in resp.text:
        print("Found 'Son Fiyat'!")
    else:
        print("'Son Fiyat' NOT found.")
        
    if "TTE" in resp.text:
        print("Found 'TTE' in text!")
        
    with open("src/tefas_session.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
        
except Exception as e:
    print(f"Error: {e}")
