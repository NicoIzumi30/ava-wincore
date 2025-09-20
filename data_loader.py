import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging
import os
from config import SPREADSHEET_ID, SHEET_NAME, logger

def parse_coordinates(coord_str):
    """
    Memisahkan string koordinat menjadi latitude dan longitude
    Format input dapat berupa:
    - "-7.850893, 110.410161"
    - "-7.850893 110.410161"
    
    Parameters:
    coord_str (str): String koordinat dalam format "lat, long" atau "lat long"
    
    Returns:
    tuple: (latitude, longitude) sebagai float
    """
    try:
        # Hapus spasi berlebih
        coord_str = coord_str.strip()
        
        # Coba split berdasarkan koma jika ada
        if ',' in coord_str:
            parts = coord_str.split(',')
        else:
            # Jika tidak ada koma, coba split berdasarkan spasi
            parts = coord_str.split()
        
        if len(parts) != 2:
            raise ValueError(f"Format koordinat tidak valid: {coord_str}")
        
        # Konversi ke float
        latitude = float(parts[0].strip())
        longitude = float(parts[1].strip())
        
        return latitude, longitude
    except Exception as e:
        raise ValueError(f"Error saat parsing koordinat '{coord_str}': {str(e)}")

def connect_to_spreadsheet():
    """
    Menghubungkan ke Google Spreadsheet menggunakan kredensial
    
    Returns:
    gspread.Client: Client untuk berinteraksi dengan Google Spreadsheet
    """
    try:
        # Gunakan OAuth2 untuk autentikasi Google Sheets API
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        
        # Pastikan file credentials.json ada
        creds_file = 'credentials.json'
        if not os.path.exists(creds_file):
            logger.error(f"File kredensial '{creds_file}' tidak ditemukan.")
            logger.error("Harap unduh credentials.json dari Google Cloud Console untuk akses ke Google Sheets API.")
            return None
            
        credentials = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
        client = gspread.authorize(credentials)
        
        logger.info("Berhasil terhubung ke Google Sheets API")
        return client
    
    except Exception as e:
        logger.error(f"Error saat menghubungkan ke Google Sheets: {e}")
        return None

def load_data_from_spreadsheet():
    """
    Memuat data outlet dari Google Spreadsheet
    
    Returns:
    list: Daftar outlet dalam format [{nama, koordinat}, ...]
    """
    try:
        # Connect ke Google Sheets
        client = connect_to_spreadsheet()
        if not client:
            logger.error("Tidak dapat terhubung ke Google Sheets. Periksa file kredensial.")
            return []
            
        # Buka spreadsheet
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        logger.info(f"Berhasil membuka spreadsheet ID: {SPREADSHEET_ID}, sheet: {SHEET_NAME}")
        
        # Ambil semua data
        data = sheet.get_all_records()
        if not data:
            logger.warning("Spreadsheet tidak berisi data atau format tidak sesuai.")
            return []
            
        logger.info(f"Berhasil memuat {len(data)} baris data dari spreadsheet")
        
        # Deteksi kolom yang digunakan untuk nama dan koordinat
        sample_row = data[14] if data else {}
        column_keys = list(sample_row.keys())
        
        # Cari kolom nama outlet - biasanya berisi kata "NAMA" atau "OUTLET"
        name_column = None
        for col in column_keys:
            if 'NAMA TOKO' in col.upper() :
                name_column = col
                break
        
        if not name_column and column_keys:
            name_column = column_keys[4]  # Default: kolom pertama
            logger.info(f"Tidak ditemukan kolom nama yang sesuai, menggunakan kolom pertama: '{name_column}'")
        
        # Cari kolom koordinat - biasanya berisi kata "MAPS", "KOORDINAT", "GPS", "LAT", "LONG"
        coord_column = None
        for col in column_keys:
            if any(keyword in col.upper() for keyword in ['MAPS']):
                coord_column = col
                break
        
        if not coord_column and len(column_keys) > 1:
            coord_column = column_keys[16]  # Default: kolom kedua
            logger.info(f"Tidak ditemukan kolom koordinat yang sesuai, menggunakan kolom kedua: '{coord_column}'")
        
        if not name_column or not coord_column:
            logger.error("Kolom nama atau koordinat tidak ditemukan dalam spreadsheet.")
            return []
            
        logger.info(f"Menggunakan kolom '{name_column}' untuk nama outlet dan '{coord_column}' untuk koordinat")
        
        # Konversi ke format yang diperlukan
        outlets = []
        for row in data:
            try:
                nama = str(row[name_column]).strip()
                koordinat = str(row[coord_column]).strip()
                
                # Lewati baris dengan nama atau koordinat kosong
                if not nama or not koordinat:
                    logger.warning(f"Baris dilewati: Nama atau koordinat kosong - {row}")
                    continue
                
                # Validasi format koordinat
                try:
                    lat, lon = parse_coordinates(koordinat)
                    outlets.append({
                        'nama': nama,
                        'koordinat': f"{lat}, {lon}"  # Format ulang koordinat untuk konsistensi
                    })
                except ValueError as e:
                    logger.warning(f"Outlet '{nama}' dilewati: {e}")
                    continue
                
            except Exception as e:
                logger.warning(f"Error saat memproses baris: {e}")
                continue
        
        logger.info(f"Berhasil memuat {len(outlets)} outlet dari spreadsheet")
        return outlets
    
    except Exception as e:
        logger.error(f"Error saat memuat data dari spreadsheet: {e}")
        return []

def update_spreadsheet_with_results(results):
    """
    Memperbarui spreadsheet dengan hasil analisis
    Dengan error handling untuk permission issues
    
    Parameters:
    results (list): Hasil analisis outlet
    
    Returns:
    bool: True jika berhasil, False jika gagal
    """
    try:
        # Connect ke Google Sheets
        client = connect_to_spreadsheet()
        if not client:
            logger.error("Tidak dapat memperbarui spreadsheet. Gagal terhubung ke Google Sheets.")
            return False
            
        # Buka spreadsheet
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        
        # Test write permission dulu
        try:
            # Test dengan cell kosong
            test_cell = sheet.acell('A1')
            logger.info("Read permission OK, testing write permission...")
            
            # Coba update cell test
            sheet.update('A1', test_cell.value)  # Update dengan value yang sama
            logger.info("Write permission OK, proceeding with update...")
            
        except Exception as perm_error:
            logger.error(f"Permission error: {perm_error}")
            logger.error("SOLUSI: Share spreadsheet dengan email service account sebagai Editor")
            logger.error("Service account email ada di credentials.json → client_email")
            return False
        
        # Dapatkan semua data
        all_data = sheet.get_all_records()
        headers = list(all_data[0].keys()) if all_data else []
        
        # Cari kolom nama outlet
        name_column = None
        for col in headers:
            if 'NAMA' in col.upper() or 'TOKO' in col.upper():
                name_column = col
                break
        
        if not name_column and headers:
            name_column = headers[14]
        
        if not name_column:
            logger.error("Tidak dapat menemukan kolom nama outlet dalam spreadsheet.")
            return False
        
        # Tambahkan kolom baru jika belum ada
        new_columns = ['Residential', 'Education', 'Public Area', 'Culinary', 'Business Center', 
                      'Groceries', 'Convenient Stores', 'Industrial', 'Hospital/Clinic']
        
        columns_added = 0
        for col in new_columns:
            if col not in headers:
                next_col_num = len(headers) + columns_added + 1
                try:
                    sheet.update_cell(1, next_col_num, col)
                    headers.append(col)
                    columns_added += 1
                    logger.info(f"Added column: {col}")
                except Exception as e:
                    logger.error(f"Failed to add column {col}: {e}")
                    return False
        
        # Perbarui spreadsheet dengan hasil analisis
        updates_made = 0
        for result in results:
            # Cari baris dengan nama outlet yang sesuai
            outlet_name = result['Nama Outlet']
            for i, row in enumerate(all_data):
                if row.get(name_column, '').strip() == outlet_name.strip():
                    # Perbarui baris dengan hasil
                    row_idx = i + 2  # +2 karena indeks mulai dari 0 dan ada header
                    
                    for col in new_columns:
                        if col in headers:
                            col_idx = headers.index(col) + 1  # +1 karena indeks kolom dimulai dari 1
                            value = "✓" if result.get(col, False) else "✗"
                            try:
                                sheet.update_cell(row_idx, col_idx, value)
                                updates_made += 1
                            except Exception as e:
                                logger.error(f"Failed to update cell for {outlet_name}, {col}: {e}")
                    
                    break
        
        logger.info(f"Berhasil memperbarui {len(results)} outlet dengan {updates_made} cell updates di spreadsheet")
        return True
    
    except Exception as e:
        logger.error(f"Error saat memperbarui spreadsheet: {e}")
        logger.error("SOLUSI CEPAT: Skip update spreadsheet dengan set SKIP_SPREADSHEET_UPDATE=True di config.py")
        return False