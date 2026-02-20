"""
Finans Asistanı - Gelişmiş Portföy Veritabanı
SQLite ile yatırım takibi - Thread-safe versiyon
"""

import sqlite3
import threading
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger("PortfolioDB")


class PortfolioDB:
    """
    SQLite tabanlı portföy yönetim sistemi.
    Thread-safe: Her işlem kendi cursor'ını kullanır.
    
    Özellikler:
    - Yatırım ekleme
    - Kısmi satış desteği
    - Portföy güncelleme
    - İşlem geçmişi
    - Kar/Zarar hesaplama
    """
    
    def __init__(self, db_name: str = "portfoy.db"):
        """
        Args:
            db_name: Veritabanı dosya adı
        """
        self.db_name = db_name
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self._create_tables()
        logger.info(f"📂 Veritabanı bağlantısı kuruldu: {db_name}")

    def _get_cursor(self):
        """Her işlem için yeni cursor oluştur"""
        return self.conn.cursor()

    def _create_tables(self):
        """Tabloları oluştur"""
        cursor = self._get_cursor()
        # Ana yatırımlar tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS yatirimlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sembol TEXT NOT NULL,
                miktar REAL NOT NULL,
                maliyet REAL NOT NULL,
                tarih TEXT,
                notlar TEXT
            )
        """)
        
        # İşlem geçmişi tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS islem_gecmisi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sembol TEXT NOT NULL,
                islem_tipi TEXT NOT NULL,
                miktar REAL NOT NULL,
                fiyat REAL NOT NULL,
                tarih TEXT NOT NULL,
                kar_zarar REAL DEFAULT 0,
                detay TEXT
            )
        """)
        
        self.conn.commit()
        cursor.close()

    def ekle(self, sembol: str, miktar: float, maliyet: float, notlar: str = "") -> str:
        """Yeni yatırım ekle."""
        tarih = datetime.now().strftime("%Y-%m-%d %H:%M")
        sembol = sembol.upper().strip()
        
        with self.lock:
            cursor = self._get_cursor()
            cursor.execute(
                "INSERT INTO yatirimlar (sembol, miktar, maliyet, tarih, notlar) VALUES (?, ?, ?, ?, ?)",
                (sembol, miktar, maliyet, tarih, notlar)
            )
            self._log_islem(cursor, sembol, "ALIS", miktar, maliyet)
            self.conn.commit()
            cursor.close()
        
        logger.info(f"✅ Yatırım eklendi: {sembol} x{miktar} @ {maliyet} TL")
        return f"✅ {sembol} portföye eklendi: {miktar} adet, {maliyet} TL'den."

    def sat(self, sembol: str, miktar: float, satis_fiyati: float) -> str:
        """Kısmi veya tam satış yap."""
        sembol = sembol.upper().strip()
        
        with self.lock:
            cursor = self._get_cursor()
            
            cursor.execute(
                "SELECT id, miktar, maliyet FROM yatirimlar WHERE sembol = ? ORDER BY tarih ASC",
                (sembol,)
            )
            pozisyonlar = cursor.fetchall()
            
            if not pozisyonlar:
                cursor.close()
                return f"❌ {sembol} portföyünde bulunamadı."
            
            toplam_miktar = sum(p[1] for p in pozisyonlar)
            if miktar > toplam_miktar:
                cursor.close()
                return f"❌ Yetersiz miktar. Portföyde {toplam_miktar} adet {sembol} var."
            
            kalan_satis = miktar
            toplam_kar_zarar = 0
            ortalama_maliyet = 0
            
            for poz_id, poz_miktar, poz_maliyet in pozisyonlar:
                if kalan_satis <= 0:
                    break
                
                satilacak = min(kalan_satis, poz_miktar)
                kar_zarar = satilacak * (satis_fiyati - poz_maliyet)
                toplam_kar_zarar += kar_zarar
                ortalama_maliyet += satilacak * poz_maliyet
                
                if satilacak >= poz_miktar:
                    cursor.execute("DELETE FROM yatirimlar WHERE id = ?", (poz_id,))
                else:
                    yeni_miktar = poz_miktar - satilacak
                    cursor.execute(
                        "UPDATE yatirimlar SET miktar = ? WHERE id = ?",
                        (yeni_miktar, poz_id)
                    )
                
                kalan_satis -= satilacak
            
            ortalama_maliyet = ortalama_maliyet / miktar if miktar > 0 else 0
            
            self._log_islem(cursor, sembol, "SATIS", miktar, satis_fiyati, toplam_kar_zarar)
            self.conn.commit()
            cursor.close()
        
        kar_zarar_str = f"+{toplam_kar_zarar:.2f}" if toplam_kar_zarar >= 0 else f"{toplam_kar_zarar:.2f}"
        emoji = "📈" if toplam_kar_zarar >= 0 else "📉"
        
        logger.info(f"💰 Satış: {sembol} x{miktar} @ {satis_fiyati} TL = {kar_zarar_str} TL")
        
        return f"""\
{emoji} **{sembol} Satış Tamamlandı**
• Satılan: {miktar} adet @ {satis_fiyati} TL
• Ortalama Maliyet: {ortalama_maliyet:.2f} TL
• **Kar/Zarar: {kar_zarar_str} TL**"""

    def guncelle(self, sembol: str, yeni_miktar: Optional[float] = None, 
                 yeni_maliyet: Optional[float] = None) -> str:
        """Mevcut pozisyonu güncelle."""
        sembol = sembol.upper().strip()
        
        with self.lock:
            cursor = self._get_cursor()
            
            cursor.execute(
                "SELECT id, miktar, maliyet FROM yatirimlar WHERE sembol = ? LIMIT 1",
                (sembol,)
            )
            result = cursor.fetchone()
            
            if not result:
                cursor.close()
                return f"❌ {sembol} portföyünde bulunamadı."
            
            poz_id, eski_miktar, eski_maliyet = result
            
            miktar = yeni_miktar if yeni_miktar is not None else eski_miktar
            maliyet = yeni_maliyet if yeni_maliyet is not None else eski_maliyet
            
            cursor.execute(
                "UPDATE yatirimlar SET miktar = ?, maliyet = ? WHERE id = ?",
                (miktar, maliyet, poz_id)
            )
            
            self._log_islem(cursor, sembol, "GUNCELLEME", miktar, maliyet, 
                            detay=f"Eski: {eski_miktar}@{eski_maliyet}")
            
            self.conn.commit()
            cursor.close()
        
        logger.info(f"🔄 Güncelleme: {sembol} {eski_miktar}→{miktar} adet, {eski_maliyet}→{maliyet} TL")
        return f"🔄 {sembol} güncellendi: {miktar} adet, {maliyet} TL"

    def sil(self, sembol: str) -> str:
        """Sembolü tamamen portföyden sil"""
        sembol = sembol.upper().strip()
        
        with self.lock:
            cursor = self._get_cursor()
            
            cursor.execute("SELECT miktar FROM yatirimlar WHERE sembol = ?", (sembol,))
            if not cursor.fetchone():
                cursor.close()
                return f"❌ {sembol} portföyünde bulunamadı."
            
            cursor.execute("DELETE FROM yatirimlar WHERE sembol = ?", (sembol,))
            self.conn.commit()
            cursor.close()
        
        logger.info(f"🗑️ Silindi: {sembol}")
        return f"🗑️ {sembol} portföyden silindi."

    def getir(self) -> List[Dict]:
        """Tüm portföyü listele."""
        with self.lock:
            cursor = self._get_cursor()
            cursor.execute("""
                SELECT sembol, SUM(miktar) as toplam_miktar, 
                       SUM(miktar * maliyet) / SUM(miktar) as ort_maliyet,
                       MIN(tarih) as ilk_alis
                FROM yatirimlar 
                GROUP BY sembol
                ORDER BY sembol
            """)
            veriler = cursor.fetchall()
            cursor.close()
        
        portfoy = []
        for v in veriler:
            portfoy.append({
                "sembol": v[0],
                "adet": round(v[1], 4),
                "alis_fiyati": round(v[2], 4),
                "ilk_alis": v[3],
                "toplam_maliyet": round(v[1] * v[2], 2)
            })
        
        return portfoy

    def getir_detayli(self) -> List[Dict]:
        """Her pozisyonu ayrı ayrı listele (FIFO görünümü)"""
        with self.lock:
            cursor = self._get_cursor()
            cursor.execute(
                "SELECT id, sembol, miktar, maliyet, tarih, notlar FROM yatirimlar ORDER BY tarih"
            )
            veriler = cursor.fetchall()
            cursor.close()
        
        return [
            {
                "id": v[0],
                "sembol": v[1],
                "adet": v[2],
                "alis_fiyati": v[3],
                "tarih": v[4],
                "notlar": v[5] or ""
            }
            for v in veriler
        ]

    def islem_gecmisi(self, sembol: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """İşlem geçmişini getir."""
        with self.lock:
            cursor = self._get_cursor()
            
            if sembol:
                cursor.execute("""
                    SELECT sembol, islem_tipi, miktar, fiyat, tarih, kar_zarar, detay
                    FROM islem_gecmisi 
                    WHERE sembol = ?
                    ORDER BY tarih DESC
                    LIMIT ?
                """, (sembol.upper(), limit))
            else:
                cursor.execute("""
                    SELECT sembol, islem_tipi, miktar, fiyat, tarih, kar_zarar, detay
                    FROM islem_gecmisi 
                    ORDER BY tarih DESC
                    LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            cursor.close()
        
        return [
            {
                "sembol": r[0],
                "islem": r[1],
                "miktar": r[2],
                "fiyat": r[3],
                "tarih": r[4],
                "kar_zarar": r[5],
                "detay": r[6]
            }
            for r in rows
        ]

    def _log_islem(self, cursor, sembol: str, islem_tipi: str, miktar: float, 
                   fiyat: float, kar_zarar: float = 0, detay: str = ""):
        """İşlemi geçmişe kaydet (cursor dışarıdan alınır)"""
        tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO islem_gecmisi (sembol, islem_tipi, miktar, fiyat, tarih, kar_zarar, detay)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (sembol, islem_tipi, miktar, fiyat, tarih, kar_zarar, detay))

    def ozet(self) -> Dict:
        """Portföy özeti"""
        portfoy = self.getir()
        
        toplam_maliyet = sum(p["toplam_maliyet"] for p in portfoy)
        sembol_sayisi = len(portfoy)
        
        return {
            "sembol_sayisi": sembol_sayisi,
            "toplam_maliyet": round(toplam_maliyet, 2),
            "yatirimlar": portfoy
        }

    def close(self):
        """Veritabanı bağlantısını kapat"""
        self.conn.close()
        logger.info("📂 Veritabanı bağlantısı kapatıldı")


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    
    db = PortfolioDB("test_portfoy.db")
    
    print(db.ekle("TTE", 100, 1.05))
    print(db.ekle("TTE", 50, 1.10))
    print(db.ekle("THYAO", 20, 350))
    
    print("\n📊 Portföy:")
    for p in db.getir():
        print(f"  {p}")
    
    print("\n" + db.sat("TTE", 75, 1.20))
    print("\n" + db.guncelle("THYAO", yeni_maliyet=360))
    
    print("\n📜 İşlem Geçmişi:")
    for i in db.islem_gecmisi():
        print(f"  {i}")
    
    db.close()