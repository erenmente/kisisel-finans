from app import get_financial_data
import sys

# Windows terminalinde Türkçe karakter sorununu çöz
sys.stdout.reconfigure(encoding='utf-8')

print("--- APP LOGIC VERIFICATION ---")

print("\n[1] Testing Gold (ALTIN)...")
print(get_financial_data("ALTIN"))

print("\n[2] Testing TEFAS (TTE)...")
print(get_financial_data("TTE"))

print("\n[3] Testing USD...")
print(get_financial_data("USD"))
