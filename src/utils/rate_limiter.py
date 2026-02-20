"""
Rate Limiter - API ve Web Scraping İstek Sınırlandırma
"""

import time
from collections import defaultdict
from threading import Lock
from functools import wraps
from typing import Callable, Dict
import logging

logger = logging.getLogger("RateLimiter")


class RateLimiter:
    """
    Token Bucket algoritması ile rate limiting.
    Her kaynak için ayrı limit tanımlanabilir.
    """
    
    def __init__(self):
        self._buckets: Dict[str, dict] = {}
        self._lock = Lock()
        
        # Varsayılan limitler (kaynak_adı: {saniye_başına_istek, max_burst})
        self.default_limits = {
            "tefas": {"rate": 2, "burst": 5},       # Saniyede 2 istek, max 5 burst
            "bloomberg": {"rate": 3, "burst": 10},  # Saniyede 3 istek, max 10 burst
            "yahoo": {"rate": 5, "burst": 20},      # Saniyede 5 istek, max 20 burst
            "groq": {"rate": 10, "burst": 30},      # Saniyede 10 istek, max 30 burst
            "default": {"rate": 5, "burst": 10}     # Bilinmeyen kaynaklar için
        }
    
    def _get_bucket(self, resource: str) -> dict:
        """Kaynak için token bucket al veya oluştur"""
        if resource not in self._buckets:
            limits = self.default_limits.get(resource, self.default_limits["default"])
            self._buckets[resource] = {
                "tokens": limits["burst"],
                "last_update": time.time(),
                "rate": limits["rate"],
                "burst": limits["burst"]
            }
        return self._buckets[resource]
    
    def _refill(self, bucket: dict):
        """Token'ları yenile"""
        now = time.time()
        elapsed = now - bucket["last_update"]
        
        # Geçen süreye göre token ekle
        new_tokens = elapsed * bucket["rate"]
        bucket["tokens"] = min(bucket["burst"], bucket["tokens"] + new_tokens)
        bucket["last_update"] = now
    
    def acquire(self, resource: str, tokens: int = 1, block: bool = True) -> bool:
        """
        Token al. 
        
        Args:
            resource: Kaynak adı (tefas, bloomberg, yahoo, groq)
            tokens: Kaç token gerekiyor
            block: Token yoksa bekle mi?
        
        Returns:
            True = başarılı, False = token yok
        """
        with self._lock:
            bucket = self._get_bucket(resource)
            self._refill(bucket)
            
            if bucket["tokens"] >= tokens:
                bucket["tokens"] -= tokens
                return True
            
            if block:
                # Gerekli token'lar için bekleme süresi hesapla
                needed = tokens - bucket["tokens"]
                wait_time = needed / bucket["rate"]
                
                logger.debug(f"⏳ Rate limit: {resource} için {wait_time:.2f}s bekleniyor...")
                time.sleep(wait_time)
                
                # Tekrar dene
                self._refill(bucket)
                bucket["tokens"] -= tokens
                return True
            
            return False
    
    def get_status(self, resource: str) -> dict:
        """Kaynak durumunu göster"""
        bucket = self._get_bucket(resource)
        self._refill(bucket)
        return {
            "resource": resource,
            "available_tokens": round(bucket["tokens"], 2),
            "rate_per_second": bucket["rate"],
            "max_burst": bucket["burst"]
        }


# Global rate limiter instance
_limiter = RateLimiter()


def rate_limited(resource: str, tokens: int = 1):
    """
    Decorator: Fonksiyonu rate limit ile çalıştır.
    
    Kullanım:
        @rate_limited("tefas")
        def get_tefas_price(code):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _limiter.acquire(resource, tokens)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def acquire(resource: str, tokens: int = 1, block: bool = True) -> bool:
    """Global rate limiter'dan token al"""
    return _limiter.acquire(resource, tokens, block)


def status(resource: str) -> dict:
    """Rate limit durumunu göster"""
    return _limiter.get_status(resource)


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.DEBUG)
    
    @rate_limited("tefas")
    def test_request(i):
        print(f"İstek {i} gönderildi - {time.strftime('%H:%M:%S')}")
    
    print("Rate Limit Testi (TEFAS: 2/saniye)")
    print("-" * 40)
    
    for i in range(10):
        test_request(i)
    
    print("\nDurum:", status("tefas"))
