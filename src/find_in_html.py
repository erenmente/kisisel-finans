import re

def search_html():
    try:
        with open("tefas_debug.html", "r", encoding="utf-8") as f:
            content = f.read()
        
        print(f"File size: {len(content)} chars")
        
        # Search for ID
        if "MainContent_PanelInfo_lblPrice" in content:
            print("FOUND ID: MainContent_PanelInfo_lblPrice")
            # Find context
            idx = content.find("MainContent_PanelInfo_lblPrice")
            start = max(0, idx - 100)
            end = min(len(content), idx + 200)
            print(f"CONTEXT:\n{content[start:end]}")
        else:
            print("ID NOT FOUND")
            
        # Search for Price Pattern (e.g. 1,234567)
        # TEFAS prices usually have 6 decimal places
        match = re.search(r'\d{1,3},\d{6}', content)
        if match:
            print(f"FOUND PRICE PATTERN: {match.group(0)}")
            start = max(0, match.start() - 100)
            end = min(len(content), match.end() + 100)
            print(f"CONTEXT:\n{content[start:end]}")
        else:
            print("PRICE PATTERN NOT FOUND")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    search_html()
