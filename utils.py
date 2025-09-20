import json
import os
import random
import string
from config import logger, SPREADSHEET_ID

def cleanup_old_files(output_dir, keep_days=30):
    """
    Menghapus file output yang lebih tua dari keep_days
    
    Parameters:
    output_dir (str): Direktori yang berisi file output
    keep_days (int): Jumlah hari untuk menyimpan file
    
    Returns:
    int: Jumlah file yang dihapus
    """
    import time
    import os
    
    if not os.path.exists(output_dir):
        logger.warning(f"Direktori {output_dir} tidak ditemukan")
        return 0
        
    now = time.time()
    keep_seconds = keep_days * 24 * 60 * 60
    
    count = 0
    for f in os.listdir(output_dir):
        # Lewati file latest
        if "latest" in f:
            continue
            
        # Lewati file non timestamp
        if not any(x in f for x in [".xlsx", ".html", ".json"]):
            continue
            
        file_path = os.path.join(output_dir, f)
        
        # Jika file lebih tua dari keep_days, hapus
        if os.path.isfile(file_path) and os.stat(file_path).st_mtime < (now - keep_seconds):
            try:
                os.remove(file_path)
                count += 1
            except Exception as e:
                logger.warning(f"Gagal menghapus file lama {f}: {e}")
    
    if count > 0:
        logger.info(f"Berhasil menghapus {count} file lama")
        
    return count
def generate_random_id(length=8):
    """
    Menghasilkan ID acak untuk digunakan dalam nama file sementara
    
    Parameters:
    length (int): Panjang ID yang diinginkan
    
    Returns:
    str: ID acak
    """
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for i in range(length))

def save_json_file(data, filename):
    """
    Menyimpan data ke file JSON
    
    Parameters:
    data: Data yang akan disimpan
    filename (str): Nama file output
    
    Returns:
    str: Path ke file output, None jika gagal
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return os.path.abspath(filename)
    except Exception as e:
        logger.error(f"Error saat menyimpan file JSON: {e}")
        return None

def load_json_file(filename):
    """
    Memuat data dari file JSON
    
    Parameters:
    filename (str): Nama file yang akan dimuat
    
    Returns:
    dict/list: Data dari file JSON, None jika gagal
    """
    try:
        if not os.path.exists(filename):
            logger.warning(f"File JSON tidak ditemukan: {filename}")
            return None
            
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Error saat memuat file JSON: {e}")
        return None

def format_time(seconds):
    """
    Memformat waktu dalam detik menjadi format yang lebih mudah dibaca
    
    Parameters:
    seconds (float): Waktu dalam detik
    
    Returns:
    str: Waktu yang diformat (HH:MM:SS)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def get_credentials_info():
    """
    Memberikan informasi tentang cara mendapatkan kredensial Google API
    """
    print("\n=== Cara Mendapatkan Kredensial Google Sheets API ===")
    print("1. Buka Google Cloud Console: https://console.cloud.google.com/")
    print("2. Buat Project baru atau pilih project yang sudah ada")
    print("3. Aktifkan Google Sheets API dan Google Drive API")
    print("4. Buat Service Account dengan peran Editor")
    print("5. Unduh file JSON kredensial dan simpan sebagai 'credentials.json'")
    print("6. Buka spreadsheet Anda dan bagikan dengan email Service Account")
    print(f"7. Dapatkan ID spreadsheet dari URL dan masukkan di config.py")
    print("   Contoh: SPREADSHEET_ID = '1a2b3c4d...'")
    print("\nPenting: ID spreadsheet saat ini: " + SPREADSHEET_ID)
    print("Pastikan spreadsheet berisi kolom nama outlet dan koordinat")

def get_province_emoji(province):
    """Get emoji for province"""
    emoji_map = {
        'DKI JAKARTA': '🏙️',
        'JAWA BARAT': '🏔️',
        'JAWA TENGAH': '🏛️',
        'SUMATERA BAGIAN SELATAN': '🌴',
        'SUMATERA BAGIAN UTARA': '🌿',
        'LAINNYA': '📍'
    }
    return emoji_map.get(province, '📍')

def export_province_specific_excel(analysis_results_by_province, base_filename):
    """
    Export Excel files per province
    """
    for province, results in analysis_results_by_province.items():
        if province != 'LAINNYA':
            province_filename = base_filename.replace('.xlsx', f'_{province.lower().replace(" ", "_")}.xlsx')
            create_excel_report(results, province_filename)
            logger.info(f"Excel report created for {province}: {province_filename}")

def check_required_files():
    """
    Memeriksa keberadaan file yang diperlukan
    
    Returns:
    bool: True jika semua file ada, False jika tidak
    """
    required_files = ['credentials.json']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        logger.error(f"File diperlukan tidak ditemukan: {', '.join(missing_files)}")
        print(f"\nPerhatian: File berikut tidak ditemukan: {', '.join(missing_files)}")
        
        if 'credentials.json' in missing_files:
            get_credentials_info()
        
        return False
    
    return True