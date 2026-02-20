"""
Browser Agent Güvenli Test
Sadece TEFAS'a gidip fiyat okur, hiçbir şey göndermez.
"""

import asyncio
import sys
sys.path.insert(0, ".")

from browser_agent import BrowserAgent

async def safe_test():
    print("=" * 50)
    print("  🔒 GÜVENLİ BROWSER AGENT TESTİ")
    print("=" * 50)
    print()
    print("Bu test şunları yapacak:")
    print("  1. Chrome tarayıcı açılacak (görünür)")
    print("  2. TEFAS sitesine gidilecek")
    print("  3. TTE fon fiyatı okunacak")
    print("  4. Tarayıcı kapanacak")
    print()
    print("⚠️  Hiçbir kişisel bilgi gönderilmez!")
    print("=" * 50)
    print()
    
    # Görünür modda test (ne yaptığını görebilirsin)
    agent = BrowserAgent(headless=False, slow_mo=1000)  # Yavaş, görünür
    
    try:
        await agent.start()
        print("✅ Tarayıcı başlatıldı")
        
        # TEFAS testi
        print("\n🔍 TEFAS'tan TTE fiyatı çekiliyor...")
        result = await agent.get_tefas_price("TTE")
        
        if "error" not in result:
            print(f"\n✅ Başarılı!")
            print(f"   Sembol: {result.get('symbol')}")
            print(f"   Fiyat: {result.get('price')}")
            print(f"   Kaynak: {result.get('source')}")
        else:
            print(f"\n⚠️ Hata: {result.get('error')}")
            
    except Exception as e:
        print(f"\n❌ Hata oluştu: {e}")
        
    finally:
        await agent.stop()
        print("\n🔴 Tarayıcı kapatıldı")
        print("\n✅ Test tamamlandı - güvenli!")

if __name__ == "__main__":
    asyncio.run(safe_test())
