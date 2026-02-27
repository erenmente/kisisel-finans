"""
Finans Asistanı - Gelişmiş Portföy Veritabanı
PostgreSQL (Supabase) ile yatırım takibi
"""

import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("PortfolioDB")

class PortfolioDB:
    """
    PostgreSQL (Supabase) tabanlı portföy yönetim sistemi.
    Serverless ortama uygun olarak connection pooling kullanır.
    """
    
    def __init__(self, db_url: str = None):
        """
        Args:
            db_url: PostgreSQL veritabanı bağlantı adresi (URL)
        """
        self.db_url = db_url or os.environ.get("DATABASE_URL")
        
        if not self.db_url:
            logger.error("❌ DATABASE_URL ortam değişkeni bulunamadı. Lütfen .env dosyasını kontrol edin.")
            raise ValueError("DATABASE_URL gerekli!")
            
        try:
            # Thread-safe bağlantı havuzu (min 1, max 10 bağlantı)
            self.connection_pool = pool.ThreadedConnectionPool(1, 10, dsn=self.db_url)
            logger.info("📂 Supabase (PostgreSQL) bağlantı havuzu başarıyla kuruldu.")
            self._create_tables()
        except Exception as e:
            logger.error(f"❌ Veritabanına bağlanılamadı: {e}")
            raise

    def get_connection(self):
        """Havuzdan bir bağlantı alır"""
        return self.connection_pool.getconn()

    def release_connection(self, conn):
        """Bağlantıyı havuza geri verir"""
        if self.connection_pool:
            self.connection_pool.putconn(conn)

    def _create_tables(self):
        """Tabloları oluştur"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Ana yatırımlar tablosu (SQLite'daki AUTOINCREMENT yerine SERIAL kullanılır)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS yatirimlar (
                    id SERIAL PRIMARY KEY,
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
                    id SERIAL PRIMARY KEY,
                    sembol TEXT NOT NULL,
                    islem_tipi TEXT NOT NULL,
                    miktar REAL NOT NULL,
                    fiyat REAL NOT NULL,
                    tarih TEXT NOT NULL,
                    kar_zarar REAL DEFAULT 0,
                    detay TEXT
                )
            """)
            
            conn.commit()
            cursor.close()
        except Exception as e:
            conn.rollback()
            logger.error(f"Tablo oluşturma hatası: {e}")
        finally:
            self.release_connection(conn)

    def ekle(self, sembol: str, miktar: float, maliyet: float, notlar: str = "") -> str:
        """Yeni yatırım ekle."""
        tarih = datetime.now().strftime("%Y-%m-%d %H:%M")
        sembol = sembol.upper().strip()
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO yatirimlar (sembol, miktar, maliyet, tarih, notlar) VALUES (%s, %s, %s, %s, %s)",
                (sembol, miktar, maliyet, tarih, notlar)
            )
            self._log_islem(cursor, sembol, "ALIS", miktar, maliyet)
            conn.commit()
            cursor.close()
            logger.info(f"✅ Yatırım eklendi: {sembol} x{miktar} @ {maliyet} TL")
            return f"✅ {sembol} portföye eklendi: {miktar} adet, {maliyet} TL'den."
        except Exception as e:
            conn.rollback()
            logger.error(f"Ekleme hatası: {e}")
            return f"❌ Hata oluştu: {str(e)}"
        finally:
            self.release_connection(conn)

    def sat(self, sembol: str, miktar: float, satis_fiyati: float) -> str:
        """Kısmi veya tam satış yap."""
        sembol = sembol.upper().strip()
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, miktar, maliyet FROM yatirimlar WHERE sembol = %s ORDER BY tarih ASC",
                (sembol,)
            )
            pozisyonlar = cursor.fetchall()
            
            if not pozisyonlar:
                cursor.close()
                self.release_connection(conn)
                return f"❌ {sembol} portföyünde bulunamadı."
            
            toplam_miktar = sum(p[1] for p in pozisyonlar)
            if miktar > toplam_miktar:
                cursor.close()
                self.release_connection(conn)
                return f"❌ Yetersiz miktar. Portföyde {toplam_miktar} adet {sembol} var."
            
            kalan_satis = miktar
            toplam_kar_zarar = 0
            ortalama_maliyet = 0
            
            for poz_id, poz_miktar, poz_maliyet in pozisyonlar:
                if kalan_satis <= 0:
                    break
                
                satilacak = min(kalan_satis, float(poz_miktar))
                poz_maliyet_float = float(poz_maliyet)
                kar_zarar = satilacak * (satis_fiyati - poz_maliyet_float)
                toplam_kar_zarar += kar_zarar
                ortalama_maliyet += satilacak * poz_maliyet_float
                
                if satilacak >= poz_miktar:
                    cursor.execute("DELETE FROM yatirimlar WHERE id = %s", (poz_id,))
                else:
                    yeni_miktar = poz_miktar - satilacak
                    cursor.execute(
                        "UPDATE yatirimlar SET miktar = %s WHERE id = %s",
                        (yeni_miktar, poz_id)
                    )
                
                kalan_satis -= satilacak
            
            ortalama_maliyet = ortalama_maliyet / miktar if miktar > 0 else 0
            
            self._log_islem(cursor, sembol, "SATIS", miktar, satis_fiyati, toplam_kar_zarar)
            conn.commit()
            cursor.close()
            
            kar_zarar_str = f"+{toplam_kar_zarar:.2f}" if toplam_kar_zarar >= 0 else f"{toplam_kar_zarar:.2f}"
            emoji = "📈" if toplam_kar_zarar >= 0 else "📉"
            logger.info(f"💰 Satış: {sembol} x{miktar} @ {satis_fiyati} TL = {kar_zarar_str} TL")
            
            return f"{emoji} **{sembol} Satış Tamamlandı**\n• Satılan: {miktar} adet @ {satis_fiyati} TL\n• Ortalama Maliyet: {ortalama_maliyet:.2f} TL\n• **Kar/Zarar: {kar_zarar_str} TL**"
        except Exception as e:
            conn.rollback()
            logger.error(f"Satış hatası: {e}")
            return f"❌ Hata oluştu: {str(e)}"
        finally:
            self.release_connection(conn)

    def guncelle(self, sembol: str, yeni_miktar: Optional[float] = None, 
                 yeni_maliyet: Optional[float] = None) -> str:
        """Mevcut pozisyonu güncelle."""
        sembol = sembol.upper().strip()
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, miktar, maliyet FROM yatirimlar WHERE sembol = %s LIMIT 1",
                (sembol,)
            )
            result = cursor.fetchone()
            
            if not result:
                cursor.close()
                self.release_connection(conn)
                return f"❌ {sembol} portföyünde bulunamadı."
            
            poz_id, eski_miktar, eski_maliyet = result
            
            miktar = yeni_miktar if yeni_miktar is not None else float(eski_miktar)
            maliyet = yeni_maliyet if yeni_maliyet is not None else float(eski_maliyet)
            
            cursor.execute(
                "UPDATE yatirimlar SET miktar = %s, maliyet = %s WHERE id = %s",
                (miktar, maliyet, poz_id)
            )
            
            self._log_islem(cursor, sembol, "GUNCELLEME", miktar, maliyet, 
                            detay=f"Eski: {eski_miktar}@{eski_maliyet}")
            
            conn.commit()
            cursor.close()
            
            logger.info(f"🔄 Güncelleme: {sembol} {eski_miktar}→{miktar} adet, {eski_maliyet}→{maliyet} TL")
            return f"🔄 {sembol} güncellendi: {miktar} adet, {maliyet} TL"
        except Exception as e:
            conn.rollback()
            logger.error(f"Güncelleme hatası: {e}")
            return f"❌ Hata oluştu: {str(e)}"
        finally:
            self.release_connection(conn)

    def sil(self, sembol: str) -> str:
        """Sembolü tamamen portföyden sil"""
        sembol = sembol.upper().strip()
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT miktar FROM yatirimlar WHERE sembol = %s", (sembol,))
            if not cursor.fetchone():
                cursor.close()
                self.release_connection(conn)
                return f"❌ {sembol} portföyünde bulunamadı."
            
            cursor.execute("DELETE FROM yatirimlar WHERE sembol = %s", (sembol,))
            conn.commit()
            cursor.close()
            
            logger.info(f"🗑️ Silindi: {sembol}")
            return f"🗑️ {sembol} portföyden silindi."
        except Exception as e:
            conn.rollback()
            logger.error(f"Silme hatası: {e}")
            return f"❌ Hata oluştu: {str(e)}"
        finally:
            self.release_connection(conn)

    def getir(self) -> List[Dict]:
        """Tüm portföyü listele."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
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
                miktar = float(v[1])
                ort_maliyet = float(v[2])
                portfoy.append({
                    "sembol": v[0],
                    "adet": round(miktar, 4),
                    "alis_fiyati": round(ort_maliyet, 4),
                    "ilk_alis": v[3],
                    "toplam_maliyet": round(miktar * ort_maliyet, 2)
                })
            
            return portfoy
        except Exception as e:
            logger.error(f"Getirme hatası: {e}")
            return []
        finally:
            self.release_connection(conn)

    def getir_detayli(self) -> List[Dict]:
        """Her pozisyonu ayrı ayrı listele (FIFO görünümü)"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, sembol, miktar, maliyet, tarih, notlar FROM yatirimlar ORDER BY tarih"
            )
            veriler = cursor.fetchall()
            cursor.close()
            
            return [
                {
                    "id": v[0],
                    "sembol": v[1],
                    "adet": float(v[2]),
                    "alis_fiyati": float(v[3]),
                    "tarih": v[4],
                    "notlar": v[5] or ""
                }
                for v in veriler
            ]
        except Exception as e:
            logger.error(f"Getirme detay hatası: {e}")
            return []
        finally:
            self.release_connection(conn)

    def islem_gecmisi(self, sembol: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """İşlem geçmişini getir."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            if sembol:
                cursor.execute("""
                    SELECT sembol, islem_tipi, miktar, fiyat, tarih, kar_zarar, detay
                    FROM islem_gecmisi 
                    WHERE sembol = %s
                    ORDER BY tarih DESC
                    LIMIT %s
                """, (sembol.upper(), limit))
            else:
                cursor.execute("""
                    SELECT sembol, islem_tipi, miktar, fiyat, tarih, kar_zarar, detay
                    FROM islem_gecmisi 
                    ORDER BY tarih DESC
                    LIMIT %s
                """, (limit,))
            
            rows = cursor.fetchall()
            cursor.close()
            
            return [
                {
                    "sembol": r[0],
                    "islem": r[1],
                    "miktar": float(r[2]),
                    "fiyat": float(r[3]),
                    "tarih": r[4],
                    "kar_zarar": float(r[5]) if r[5] is not None else 0,
                    "detay": r[6]
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"İşlem geçmişi hatası: {e}")
            return []
        finally:
            self.release_connection(conn)

    def _log_islem(self, cursor, sembol: str, islem_tipi: str, miktar: float, 
                   fiyat: float, kar_zarar: float = 0, detay: str = ""):
        """İşlemi geçmişe kaydet"""
        tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO islem_gecmisi (sembol, islem_tipi, miktar, fiyat, tarih, kar_zarar, detay)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
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
        """Veritabanı bağlantı havuzunu kapat"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("📂 Veritabanı bağlantı havuzu kapatıldı")