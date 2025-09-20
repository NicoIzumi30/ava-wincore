import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import sys
import json
from config import SPREADSHEET_ID, SHEET_NAME
from utils import check_required_files, get_credentials_info

def create_or_update_spreadsheet(excel_file=None):
    """
    Membuat atau memperbarui Google Spreadsheet dari file Excel
    atau membuat template spreadsheet baru jika tidak ada file Excel
    
    Parameters:
    excel_file (str): Path ke file Excel (opsional)
    """
    print("=" * 80)
    print("       SETUP GOOGLE SPREADSHEET UNTUK ANALISIS OUTLET")
    print("=" * 80)
    
    # Cek file yang diperlukan
    if not check_required_files():
        print("Setup tidak dapat dilanjutkan. Harap sediakan file yang diperlukan.")
        return
    
    # Connect ke Google Sheets
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    try:
        credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(credentials)
        
        print("Berhasil terhubung ke Google Sheets API")
    except Exception as e:
        print(f"Error saat menghubungkan ke Google Sheets: {e}")
        get_credentials_info()
        return
    
    # Cek apakah spreadsheet sudah ada
    try:
        # Coba buka spreadsheet yang sudah ada
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        print(f"Spreadsheet ditemukan: {spreadsheet.title}")
        
        # Periksa apakah sheet sudah ada
        try:
            worksheet = spreadsheet.worksheet(SHEET_NAME)
            print(f"Sheet '{SHEET_NAME}' ditemukan")
            
            # Konfirmasi sebelum menimpa data
            overwrite = input(f"Sheet '{SHEET_NAME}' sudah ada. Timpa data yang ada? (y/n): ")
            if overwrite.lower() != 'y':
                print("Operasi dibatalkan")
                return
                
        except gspread.exceptions.WorksheetNotFound:
            # Sheet belum ada, buat baru
            print(f"Sheet '{SHEET_NAME}' belum ada, akan dibuat baru")
            worksheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows=1000, cols=20)
    
    except gspread.exceptions.SpreadsheetNotFound:
        # Spreadsheet tidak ditemukan, buat baru
        print(f"Spreadsheet dengan ID '{SPREADSHEET_ID}' tidak ditemukan")
        
        create_new = input("Buat spreadsheet baru? (y/n): ")
        if create_new.lower() != 'y':
            print("Operasi dibatalkan")
            return
            
        try:
            spreadsheet = client.create("Analisis Outlet")
            print(f"Spreadsheet baru dibuat: {spreadsheet.title}")
            
            # Update ID spreadsheet di config.py
            new_id = spreadsheet.id
            print(f"ID Spreadsheet baru: {new_id}")
            print("Perbarui SPREADSHEET_ID di config.py dengan ID ini")
            
            # Buat sheet
            worksheet = spreadsheet.worksheet("Sheet1")
            worksheet.update_title(SHEET_NAME)
            print(f"Sheet '{SHEET_NAME}' dibuat")
            
            # Bagikan spreadsheet dengan pengguna
            share_email = input("Masukkan email untuk berbagi spreadsheet (tekan Enter untuk melewati): ")
            if share_email:
                spreadsheet.share(share_email, perm_type='user', role='writer')
                print(f"Spreadsheet dibagikan dengan {share_email}")
                
        except Exception as e:
            print(f"Error saat membuat spreadsheet baru: {e}")
            return
    
    # Jika ada file Excel, upload data dari Excel
    if excel_file and os.path.exists(excel_file):
        try:
            # Baca file Excel
            df = pd.read_excel(excel_file)
            print(f"Membaca file Excel: {excel_file}")
            
            # Upload data ke spreadsheet
            # Konversi DataFrame ke list (header + data)
            header = df.columns.tolist()
            data = df.values.tolist()
            all_data = [header] + data
            
            # Update worksheet
            worksheet.clear()
            worksheet.update(all_data)
            
            print(f"Data dari {excel_file} berhasil diupload ke spreadsheet")
            
        except Exception as e:
            print(f"Error saat mengupload data dari Excel: {e}")
    else:
        # Buat template data outlet
        template_data = [
            ["Nama Outlet", "Koordinat"],
            ["Outlet Contoh 1", "-7.782913, 110.367032"],  # Koordinat di Yogyakarta
            ["Outlet Contoh 2", "-7.775232, 110.381630"]
        ]
        
        # Update worksheet dengan template
        try:
            worksheet.clear()
            worksheet.update(template_data)
            print("Template data outlet berhasil dibuat")
        except Exception as e:
            print(f"Error saat membuat template: {e}")
    
    print("\nSetup Google Spreadsheet selesai!")
    print(f"Anda dapat mengakses spreadsheet dengan ID: {spreadsheet.id}")
    print("Pastikan untuk mengganti nilai SPREADSHEET_ID di config.py jika Anda membuat spreadsheet baru")

if __name__ == "__main__":
    excel_file = None
    
    # Cek apakah ada file Excel yang diberikan sebagai argumen
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
        if not os.path.exists(excel_file):
            print(f"File Excel tidak ditemukan: {excel_file}")
            excel_file = None
    
    # Jika tidak ada argumen, cek file Excel dengan nama default
    if not excel_file:
        default_excel = "data_jogja.xlsx"
        if os.path.exists(default_excel):
            use_default = input(f"Gunakan file Excel default ({default_excel})? (y/n): ")
            if use_default.lower() == 'y':
                excel_file = default_excel
    
    create_or_update_spreadsheet(excel_file)
    
    input("\nTekan Enter untuk keluar...")