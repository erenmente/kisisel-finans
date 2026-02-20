from tefas import Crawler
from datetime import datetime, timedelta

def test_et():
    crawler = Crawler()
    # Garanti olsun diye 1 aylık veri istiyoruz
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    print(f"--- TEFAS Bağlantı Testi ({start_date} tarihinden itibaren) ---")
    
    try:
        # Sadece TTE ve MAC fonlarını çekmeyi deneyelim
        result = crawler.fetch(start=start_date, columns=["code", "date", "price", "title"])
        
        # TTE var mı kontrol et
        tte_data = result[result['code'] == "TTE"]
        
        if not tte_data.empty:
            print("BAŞARILI! Veri Geldi:")
            # En son tarihi en üste al
            tte_data = tte_data.sort_values(by="date", ascending=False)
            print(tte_data.head(3)) # İlk 3 satırı göster
        else:
            print("HATA: TEFAS'a erişildi ama TTE verisi boş döndü.")
            
    except Exception as e:
        print(f"BAĞLANTI HATASI: {e}")

if __name__ == "__main__":
    test_et()