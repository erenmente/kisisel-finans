import sqlite3
from datetime import datetime

class PortfolioDB:
    def __init__(self, db_name="portfoy.db"):
        # 1. Veritabanına Bağlan (Yoksa oluşturur)
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        # 2. Tabloyu Oluştur (Eğer zaten yoksa)
        # Sütunlar: id (kimlik), sembol (TTE), miktar (5), maliyet (60.5), tarih
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS yatirimlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sembol TEXT NOT NULL,
                miktar REAL NOT NULL,
                maliyet REAL NOT NULL,
                tarih TEXT
            )
        """)
        self.conn.commit() # Değişikliği kaydet

    def ekle(self, sembol, miktar, maliyet):
        # 3. Yeni Yatırım Ekleme Fonksiyonu
        tarih = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.cursor.execute("INSERT INTO yatirimlar (sembol, miktar, maliyet, tarih) VALUES (?, ?, ?, ?)",
                            (sembol.upper(), miktar, maliyet, tarih))
        self.conn.commit()
        return f"✅ {sembol} portföye eklendi: {miktar} adet, {maliyet} TL'den."

    def getir(self):
        # 4. Tüm Portföyü Listeleme Fonksiyonu
        self.cursor.execute("SELECT sembol, miktar, maliyet, tarih FROM yatirimlar")
        veriler = self.cursor.fetchall()
        
        # Veriyi yapay zekanın anlayacağı bir listeye çevirelim
        portfoy_listesi = []
        for v in veriler:
            portfoy_listesi.append({
                "sembol": v[0],
                "adet": v[1],
                "alis_fiyati": v[2],
                "tarih": v[3]
            })
        return portfoy_listesi

    def sil(self, sembol):
        # 5. Satış Yapınca veya Yanlış Girince Silme
        self.cursor.execute("DELETE FROM yatirimlar WHERE sembol = ?", (sembol.upper(),))
        self.conn.commit()
        return f"🗑️ {sembol} portföyden silindi."