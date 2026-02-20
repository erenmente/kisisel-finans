"""
Browser Agent - Playwright ile Gerçek Tarayıcı Otomasyonu
Finans verilerini gerçek kullanıcı gibi tarayıcı açarak çeker.
"""

import asyncio
import logging
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser
from typing import Optional, Dict, Any

# Logger yapılandırması
logger = logging.getLogger("BrowserAgent")

class BrowserAgent:
    """
    Playwright tabanlı tarayıcı otomasyon agent'ı.
    Headless veya görünür modda çalışabilir.
    """
    
    def __init__(self, headless: bool = True, slow_mo: int = 0):
        """
        Args:
            headless: True = Arka planda çalışır, False = Tarayıcı görünür
            slow_mo: Her işlem arasındaki bekleme süresi (ms) - debug için
        """
        self.headless = headless
        self.slow_mo = slow_mo
        self.browser: Optional[Browser] = None
        self.playwright = None
        
    async def start(self):
        """Tarayıcıyı başlat"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo
        )
        logger.info(f"🌐 Tarayıcı başlatıldı (headless={self.headless})")
        
    async def stop(self):
        """Tarayıcıyı kapat"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("🔴 Tarayıcı kapatıldı")
        
    async def get_tefas_price(self, fund_code: str) -> Dict[str, Any]:
        """
        TEFAS'tan fon fiyatını gerçek tarayıcı ile çeker.
        JavaScript render'lı sayfaları da okuyabilir.
        """
        if not self.browser:
            await self.start()
            
        page = await self.browser.new_page()
        result = {"symbol": fund_code, "source": "TEFAS (Browser Agent)"}
        
        try:
            url = f"https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod={fund_code}"
            logger.info(f"🔍 TEFAS açılıyor: {fund_code}")
            
            # Sayfaya git ve yüklenmesini bekle
            await page.goto(url, wait_until="networkidle", timeout=15000)
            
            # Fon başlığını al
            title_elem = page.locator("#MainContent_PanelInfo_lblFundTitle")
            if await title_elem.count() > 0:
                result["title"] = await title_elem.inner_text()
            
            # Fiyatı bul - li elementlerini tara
            li_elements = page.locator("li")
            count = await li_elements.count()
            
            for i in range(count):
                li = li_elements.nth(i)
                text = await li.inner_text()
                
                if "Fiyat" in text and "TL" in text:
                    span = li.locator("span")
                    if await span.count() > 0:
                        result["price"] = await span.first.inner_text()
                        
                elif "Son İşlem" in text or "Tarih" in text:
                    span = li.locator("span")
                    if await span.count() > 0:
                        result["date"] = await span.first.inner_text()
            
            if "price" in result:
                logger.info(f"✅ Fiyat bulundu: {result['price']}")
            else:
                result["error"] = "Fiyat bulunamadı"
                logger.warning(f"⚠️ Fiyat bulunamadı: {fund_code}")
                
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"❌ TEFAS hatası: {e}")
            
        finally:
            await page.close()
            
        return result
    
    async def get_bloomberg_gold(self) -> Dict[str, Any]:
        """Bloomberg HT'den gram altın fiyatını çeker"""
        if not self.browser:
            await self.start()
            
        page = await self.browser.new_page()
        result = {"symbol": "ALTIN", "source": "Bloomberg HT (Browser Agent)"}
        
        try:
            url = "https://www.bloomberght.com/altin/gram-altin"
            logger.info("🥇 Bloomberg Altın açılıyor...")
            
            await page.goto(url, wait_until="networkidle", timeout=15000)
            
            # Fiyatı çek
            price_elem = page.locator(".security-gram-altin .lastPrice")
            if await price_elem.count() > 0:
                result["price"] = await price_elem.inner_text()
                result["currency"] = "TRY"
                logger.info(f"✅ Altın fiyatı: {result['price']}")
            else:
                result["error"] = "Fiyat elementi bulunamadı"
                
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"❌ Bloomberg hatası: {e}")
            
        finally:
            await page.close()
            
        return result
    
    async def get_bist_price(self, symbol: str) -> Dict[str, Any]:
        """Yahoo Finance'tan BIST hisse fiyatını çeker"""
        if not self.browser:
            await self.start()
            
        page = await self.browser.new_page()
        bist_symbol = f"{symbol}.IS"
        result = {"symbol": symbol, "source": "Yahoo Finance (Browser Agent)"}
        
        try:
            url = f"https://finance.yahoo.com/quote/{bist_symbol}"
            logger.info(f"📈 Yahoo Finance açılıyor: {symbol}")
            
            await page.goto(url, wait_until="networkidle", timeout=15000)
            
            # Fiyat elementi
            # Yahoo Finance'ın fiyat selector'ı
            price_elem = page.locator('[data-testid="qsp-price"]')
            if await price_elem.count() > 0:
                result["price"] = await price_elem.inner_text()
                result["currency"] = "TRY"
                logger.info(f"✅ Hisse fiyatı: {result['price']}")
            else:
                # Alternatif selector dene
                price_elem = page.locator('fin-streamer[data-field="regularMarketPrice"]')
                if await price_elem.count() > 0:
                    result["price"] = await price_elem.get_attribute("data-value")
                    result["currency"] = "TRY"
                else:
                    result["error"] = "Fiyat bulunamadı"
                    
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"❌ Yahoo hatası: {e}")
            
        finally:
            await page.close()
            
        return result
    
    async def get_currency(self, currency: str) -> Dict[str, Any]:
        """Döviz kurunu çeker (USD, EUR vs)"""
        if not self.browser:
            await self.start()
            
        page = await self.browser.new_page()
        result = {"symbol": currency, "source": "Bloomberg HT (Browser Agent)"}
        
        try:
            # Bloomberg HT döviz sayfası
            currency_map = {
                "USD": "https://www.bloomberght.com/doviz/dolar",
                "EUR": "https://www.bloomberght.com/doviz/euro",
                "GBP": "https://www.bloomberght.com/doviz/sterlin"
            }
            
            url = currency_map.get(currency.upper())
            if not url:
                result["error"] = f"Desteklenmeyen döviz: {currency}"
                return result
                
            logger.info(f"💱 Döviz bilgisi çekiliyor: {currency}")
            await page.goto(url, wait_until="networkidle", timeout=15000)
            
            # Fiyat elementi
            price_elem = page.locator(".lastPrice").first
            if await price_elem.count() > 0 or True:  # locator.count() her zaman çalışmayabilir
                try:
                    result["price"] = await price_elem.inner_text()
                    result["currency"] = "TRY"
                    logger.info(f"✅ Döviz kuru: {result['price']}")
                except:
                    result["error"] = "Fiyat okunamadı"
            else:
                result["error"] = "Fiyat elementi bulunamadı"
                
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"❌ Döviz hatası: {e}")
            
        finally:
            await page.close()
            
        return result
    
    async def screenshot(self, url: str, save_path: str = "screenshot.png") -> str:
        """Sayfa ekran görüntüsü al - debug için"""
        if not self.browser:
            await self.start()
            
        page = await self.browser.new_page()
        try:
            await page.goto(url, wait_until="networkidle")
            await page.screenshot(path=save_path, full_page=True)
            logger.info(f"📸 Screenshot kaydedildi: {save_path}")
            return save_path
        finally:
            await page.close()


# Senkron wrapper - mevcut sistemle uyumluluk için
class SyncBrowserAgent:
    """
    Asenkron BrowserAgent'ı senkron olarak kullanmak için wrapper.
    Mevcut app.py ile uyumlu çalışır.
    """
    
    def __init__(self, headless: bool = True, show_browser: bool = False):
        """
        Args:
            headless: Arka planda çalış
            show_browser: Kullanıcıya tarayıcıyı göster (headless=False yapar)
        """
        if show_browser:
            headless = False
        self.agent = BrowserAgent(headless=headless, slow_mo=100 if show_browser else 0)
        self._loop = None
        
    def _get_loop(self):
        """Event loop al veya oluştur"""
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop
    
    def _run(self, coro):
        """Coroutine'i senkron çalıştır"""
        loop = self._get_loop()
        return loop.run_until_complete(coro)
    
    def get_tefas(self, fund_code: str) -> Dict[str, Any]:
        """TEFAS fiyatı çek (senkron)"""
        return self._run(self.agent.get_tefas_price(fund_code))
    
    def get_gold(self) -> Dict[str, Any]:
        """Altın fiyatı çek (senkron)"""
        return self._run(self.agent.get_bloomberg_gold())
    
    def get_stock(self, symbol: str) -> Dict[str, Any]:
        """Hisse fiyatı çek (senkron)"""
        return self._run(self.agent.get_bist_price(symbol))
    
    def get_currency(self, currency: str) -> Dict[str, Any]:
        """Döviz kuru çek (senkron)"""
        return self._run(self.agent.get_currency(currency))
    
    def close(self):
        """Tarayıcıyı kapat"""
        self._run(self.agent.stop())


# Test kodu
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
    
    async def test():
        agent = BrowserAgent(headless=False, slow_mo=500)  # Görünür mod, yavaş
        await agent.start()
        
        # Test: TEFAS
        result = await agent.get_tefas_price("TTE")
        print(f"\n📊 TEFAS Sonuç: {result}")
        
        # Test: Altın
        result = await agent.get_bloomberg_gold()
        print(f"\n🥇 Altın Sonuç: {result}")
        
        await agent.stop()
    
    asyncio.run(test())
