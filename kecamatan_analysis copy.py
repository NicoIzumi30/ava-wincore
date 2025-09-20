#!/usr/bin/env python3
import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import re
import sys
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging
from datetime import datetime

# Import existing modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import SPREADSHEET_ID, SHEET_NAME, logger
from data_loader import connect_to_spreadsheet, parse_coordinates
from utils import save_json_file

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("kecamatan_analysis.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("kecamatan_analysis")

OUTPUT_DIR = "output"
JSON_INPUT = os.path.join(OUTPUT_DIR, "hasil_analisis_outlet.json")
JSON_OUTPUT = os.path.join(OUTPUT_DIR, "hasil_analisis_kecamatan.json")
EXCEL_OUTPUT = os.path.join(OUTPUT_DIR, "hasil_analisis_kecamatan.xlsx")

def load_data_from_spreadsheet():
    """
    Memuat data outlet dari Google Spreadsheet dengan kolom Kecamatan
    
    Returns:
    list: Daftar outlet dalam format [{nama, kecamatan, koordinat}, ...]
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
        all_values = sheet.get_all_values()
        if not all_values:
            logger.warning("Spreadsheet tidak berisi data atau format tidak sesuai.")
            return []
            
        # Dapatkan header (baris pertama)
        header = all_values[0]
        data_rows = all_values[1:]  # Baris data (tanpa header)
        
        logger.info(f"Berhasil memuat {len(data_rows)} baris data dari spreadsheet")
        
        # Sesuaikan dengan struktur kolom yang diberikan:
        # Kolom 11 (index 10): Nama Outlet
        # Kolom 6 (index 5): Kecamatan
        # Kolom 13 (index 12): Koordinat
        NAMA_OUTLET_IDX = 10
        KECAMATAN_IDX = 5
        KOORDINAT_IDX = 12
        
        # Pastikan indeks valid
        if len(header) <= max(NAMA_OUTLET_IDX, KECAMATAN_IDX, KOORDINAT_IDX):
            logger.error(f"Format spreadsheet tidak sesuai. Header: {header}")
            return []
        
        logger.info(f"Menggunakan kolom '{header[NAMA_OUTLET_IDX]}' untuk nama outlet")
        logger.info(f"Menggunakan kolom '{header[KECAMATAN_IDX]}' untuk kecamatan")
        logger.info(f"Menggunakan kolom '{header[KOORDINAT_IDX]}' untuk koordinat")
        
        # Konversi ke format yang diperlukan
        outlets = []
        for row in data_rows:
            try:
                # Skip jika baris tidak memiliki cukup kolom
                if len(row) <= max(NAMA_OUTLET_IDX, KECAMATAN_IDX, KOORDINAT_IDX):
                    continue
                    
                nama = row[NAMA_OUTLET_IDX].strip()
                kecamatan = row[KECAMATAN_IDX].strip().upper()  # Uppercase untuk konsistensi
                koordinat = row[KOORDINAT_IDX].strip()
                
                # Lewati baris dengan nama atau koordinat kosong
                if not nama or not koordinat:
                    logger.warning(f"Baris dilewati: Nama atau koordinat kosong - {row}")
                    continue
                
                # Validasi format koordinat
                try:
                    lat, lon = parse_coordinates(koordinat)
                    outlets.append({
                        'nama': nama,
                        'kecamatan': kecamatan,
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

def load_existing_json(json_file):
    """
    Memuat data dari file JSON yang sudah ada
    
    Parameters:
    json_file (str): Path ke file JSON
    
    Returns:
    list: Data dari file JSON atau list kosong jika file tidak ada
    """
    try:
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Berhasil memuat {len(data)} data dari {json_file}")
            return data
        else:
            logger.warning(f"File JSON tidak ditemukan: {json_file}")
            return []
    except Exception as e:
        logger.error(f"Error saat memuat file JSON: {e}")
        return []

def add_kecamatan_to_json(json_data, outlet_data):
    """
    Menambahkan informasi kecamatan ke data JSON
    
    Parameters:
    json_data (list): Data JSON yang sudah ada
    outlet_data (list): Data outlet dari spreadsheet
    
    Returns:
    list: Data JSON yang sudah diperbarui
    """
    # Buat mapping nama outlet ke kecamatan
    outlet_to_kecamatan = {outlet['nama']: outlet['kecamatan'] for outlet in outlet_data if 'kecamatan' in outlet}
    
    # Perbarui data JSON
    updated_data = []
    for item in json_data:
        outlet_name = item.get('Nama Outlet')
        if outlet_name in outlet_to_kecamatan:
            # Tambahkan kecamatan jika outlet ditemukan
            item['Kecamatan'] = outlet_to_kecamatan[outlet_name]
        updated_data.append(item)
    
    logger.info(f"Berhasil menambahkan informasi kecamatan ke {len(updated_data)} data")
    return updated_data

def get_province_from_coordinates(lat, lon):
    """
    FIXED: Mendapatkan provinsi dari koordinat dengan output yang aman
    
    Parameters:
    lat (float): Latitude
    lon (float): Longitude
    
    Returns:
    str: Nama provinsi sebagai string
    """
    try:
        # Import function asli dengan safe handling
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from map_generator import get_province_from_coordinates as original_get_province
        
        result = original_get_province(lat, lon)
        
        # Pastikan result adalah string
        if isinstance(result, dict):
            # Jika result adalah dictionary, ambil nilai yang relevan
            if 'name' in result:
                return str(result['name']).strip().upper()
            elif 'province' in result:
                return str(result['province']).strip().upper()
            elif 'Province' in result:
                return str(result['Province']).strip().upper()
            else:
                # Ambil value pertama yang string
                for value in result.values():
                    if isinstance(value, str):
                        return str(value).strip().upper()
                return "LAINNYA"
        elif isinstance(result, str):
            return result.strip().upper()
        else:
            return str(result).strip().upper() if result else "LAINNYA"
            
    except Exception as e:
        logger.warning(f"Error dalam get_province_from_coordinates: {e}")
        return get_province_fallback(lat, lon)

def get_province_fallback(lat, lon):
    """
    Fallback function untuk mendapatkan provinsi berdasarkan koordinat
    
    Parameters:
    lat (float): Latitude
    lon (float): Longitude
    
    Returns:
    str: Nama provinsi
    """
    try:
        lat = float(lat)
        lon = float(lon)
        
        # Simple coordinate-based mapping untuk Indonesia
        if -6.4 <= lat <= -5.8 and 106.5 <= lon <= 107.2:
            return "DKI JAKARTA"
        elif -7.0 <= lat <= -5.5 and 105.0 <= lon <= 108.5:
            return "JAWA BARAT"
        elif -8.5 <= lat <= -6.0 and 108.5 <= lon <= 111.5:
            return "JAWA TENGAH"
        elif -4.0 <= lat <= -1.0 and 102.0 <= lon <= 106.0:
            return "SUMATERA BAGIAN SELATAN"
        elif 1.0 <= lat <= 6.0 and 96.0 <= lon <= 100.0:
            return "SUMATERA BAGIAN UTARA"
        else:
            return "LAINNYA"
            
    except (ValueError, TypeError):
        return "LAINNYA"

def group_outlets_by_province_kecamatan(updated_json):
    """
    FIXED: Mengelompokkan outlet berdasarkan provinsi untuk analisis kecamatan
    
    Parameters:
    updated_json (list): Data outlet dengan kecamatan
    
    Returns:
    dict: Dictionary outlet grouped by province dengan key berupa string
    """
    outlets_by_province = {}
    
    for outlet in updated_json:
        try:
            if outlet.get('Latitude') and outlet.get('Longitude'):
                lat, lon = outlet['Latitude'], outlet['Longitude']
                
                # Gunakan fungsi yang sudah diperbaiki
                province = get_province_from_coordinates(lat, lon)
                
                # Double check province adalah string
                if not isinstance(province, str):
                    province = str(province) if province else "LAINNYA"
                
                province = province.strip().upper()
                if not province:
                    province = "LAINNYA"
                
                if province not in outlets_by_province:
                    outlets_by_province[province] = []
                outlets_by_province[province].append(outlet)
            else:
                # Outlet tanpa koordinat
                if "LAINNYA" not in outlets_by_province:
                    outlets_by_province["LAINNYA"] = []
                outlets_by_province["LAINNYA"].append(outlet)
                
        except Exception as e:
            logger.warning(f"Error memproses outlet {outlet.get('Nama Outlet', 'Unknown')}: {e}")
            # Masukkan ke LAINNYA jika error
            if "LAINNYA" not in outlets_by_province:
                outlets_by_province["LAINNYA"] = []
            outlets_by_province["LAINNYA"].append(outlet)
    
    logger.info(f"Outlets dikelompokkan ke {len(outlets_by_province)} provinsi:")
    for province, outlets in outlets_by_province.items():
        logger.info(f"  {province}: {len(outlets)} outlets")
    
    return outlets_by_province

def parse_numeric_value(value):
    """
    Parse nilai numeric dari string, menangani format yang tidak valid
    
    Parameters:
    value: Nilai yang akan di-parse (string atau numeric)
    
    Returns:
    float: Nilai numerik, atau None jika parsing gagal
    """
    if isinstance(value, (int, float)):
        return float(value)
        
    if isinstance(value, str):
        # Hapus karakter non-numerik kecuali titik dan koma
        value = value.strip()
        
        # Handle nilai kosong atau tanda strip
        if not value or value == '-':
            return None
            
        try:
            # Coba ganti koma dengan titik dulu (format Indonesia)
            clean_value = value.replace(',', '.')
            # Hapus karakter non-numerik lainnya
            clean_value = re.sub(r'[^\d.]', '', clean_value)
            return float(clean_value)
        except:
            pass
    
    return None

def load_kecamatan_data(file_path):
    """
    Memuat data kecamatan dari file Excel
    
    Parameters:
    file_path (str): Path ke file Excel
    
    Returns:
    dict: Data kecamatan dalam format {nama_kecamatan: {population, area}}
    """
    try:
        # Baca file Excel
        df = pd.read_excel(file_path)
        logger.info(f"Berhasil memuat data dari {file_path}")
        
        # Pastikan kolom yang diperlukan ada
        required_columns = 3  # Nama Kecamatan, Luas Wilayah, Jumlah Penduduk
        if df.shape[1] < required_columns:
            logger.error(f"Format file {file_path} tidak sesuai. Minimal {required_columns} kolom diperlukan.")
            return {}
        
        # Buat dictionary data kecamatan
        kecamatan_data = {}
        for _, row in df.iterrows():
            try:
                # Ambil data dari kolom
                kecamatan = str(row.iloc[0]).strip().upper()  # Nama Kecamatan (index 0)
                area = parse_numeric_value(row.iloc[1])       # Luas Wilayah (index 1)
                population = parse_numeric_value(row.iloc[2]) # Jumlah Penduduk (index 2)
                
                # Skip jika kecamatan kosong atau data tidak valid
                if not kecamatan or kecamatan.lower() == 'nan':
                    continue
                    
                kecamatan_data[kecamatan] = {
                    'area': area,          # Luas Wilayah dalam km²
                    'population': population  # Jumlah Penduduk
                }
            except Exception as e:
                logger.warning(f"Error saat memproses baris {row.name}: {e}")
                continue
        
        logger.info(f"Berhasil memuat data {len(kecamatan_data)} kecamatan")
        return kecamatan_data
    
    except Exception as e:
        logger.error(f"Error saat memuat data kecamatan: {e}")
        return {}

def analyze_kecamatan_data_by_province(outlet_data, kecamatan_data, province_filter=None):
    """
    FIXED: Menganalisis data kecamatan dengan opsi filter provinsi
    
    Parameters:
    outlet_data (list): Data outlet dengan kecamatan
    kecamatan_data (dict): Data referensi kecamatan
    province_filter (str): Filter provinsi (optional)
    
    Returns:
    list: Hasil analisis
    """
    try:
        if province_filter and province_filter != 'ALL':
            # Filter outlet_data berdasarkan provinsi
            filtered_outlets = []
            for outlet in outlet_data:
                if outlet.get('Latitude') and outlet.get('Longitude'):
                    lat, lon = outlet['Latitude'], outlet['Longitude']
                    province = get_province_from_coordinates(lat, lon)
                    
                    if province == province_filter:
                        filtered_outlets.append(outlet)
            outlet_data = filtered_outlets
            logger.info(f"Filtered to {len(outlet_data)} outlets for province: {province_filter}")
        
        # Hitung jumlah outlet per kecamatan
        outlet_counts = {}
        for outlet in outlet_data:
            kecamatan = outlet.get('Kecamatan')
            if kecamatan:
                # Pastikan kecamatan adalah string dan konsisten
                kecamatan = str(kecamatan).strip().upper()
                outlet_counts[kecamatan] = outlet_counts.get(kecamatan, 0) + 1
        
        # Analisis kecamatan
        analysis_results = []
        for kecamatan, count in outlet_counts.items():
            # Safe dictionary access
            kec_data = None
            for key, value in kecamatan_data.items():
                # Pastikan key comparison yang aman
                safe_key = str(key).strip().upper()
                if safe_key == kecamatan:
                    kec_data = value
                    break
            
            if not kec_data:
                logger.warning(f"Data kecamatan tidak ditemukan untuk {kecamatan}")
                continue
                
            # Ambil data referensi
            area = kec_data.get('area') if isinstance(kec_data, dict) else None
            population = kec_data.get('population') if isinstance(kec_data, dict) else None
            
            # Skip jika data tidak lengkap
            if not area or not population:
                logger.warning(f"Data tidak lengkap untuk kecamatan {kecamatan}: area={area}, population={population}")
                continue
                
            # Hitung kepadatan penduduk (jiwa/km²)
            density = population / area
            
            # Hitung rasio outlet = 1 / (kepadatan penduduk / jumlah outlet)
            density_per_outlet = density / count if count > 0 else float('inf')
            outlet_ratio = 1 / density_per_outlet if density_per_outlet != float('inf') and density_per_outlet != 0 else 0
            
            # Tentukan rekomendasi berdasarkan rasio outlet
            recommendation = ""
            if outlet_ratio < 0.005:
                recommendation = "Padat - Butuh outlet baru"
            elif outlet_ratio < 0.010:
                recommendation = "Cukup padat - Perlu pertimbangkan outlet baru"
            elif outlet_ratio < 0.020:
                recommendation = "Ideal"
            else:
                recommendation = "Sudah cukup - Fokus pada kualitas"
            
            # Tambahkan hasil analisis
            analysis_results.append({
                'Kecamatan': kecamatan,
                'Jumlah Penduduk': population,
                'Luas Wilayah': area,
                'Jumlah Outlet': count,
                'Kepadatan Penduduk': density,
                'Rasio Outlet': outlet_ratio,
                'Rekomendasi': recommendation
            })
        
        # Urutkan berdasarkan nama kecamatan
        analysis_results.sort(key=lambda x: x['Kecamatan'])
        
        logger.info(f"Berhasil menganalisis {len(analysis_results)} kecamatan")
        return analysis_results
        
    except Exception as e:
        logger.error(f"Error dalam analyze_kecamatan_data_by_province: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []

def generate_business_insights(analysis_results, province_name=None):
    """
    Menghasilkan insight bisnis berdasarkan hasil analisis
    
    Parameters:
    analysis_results (list): Hasil analisis kecamatan
    province_name (str): Nama provinsi (optional)
    
    Returns:
    dict: Insight bisnis dalam bentuk teks
    """
    try:
        # Konversi ke DataFrame untuk memudahkan analisis
        df = pd.DataFrame(analysis_results)
        
        if df.empty:
            return {'summary': 'Tidak ada data untuk dianalisis'}
        
        # Prefix untuk insights berdasarkan filter
        prefix = f"Provinsi {province_name}: " if province_name and province_name != 'ALL' else ""
        
        # 1. Kecamatan yang paling membutuhkan outlet baru
        df_need_outlets = df.sort_values(by='Rasio Outlet', ascending=False)
        top_need_outlets = df_need_outlets.head(3)
        
        # 2. Kecamatan dengan kepadatan penduduk tertinggi
        df_density = df.sort_values(by='Kepadatan Penduduk', ascending=False)
        top_density = df_density.head(3)
        
        # 3. Kecamatan dengan jumlah outlet terbanyak
        df_most_outlets = df.sort_values(by='Jumlah Outlet', ascending=False)
        top_outlets = df_most_outlets.head(3)
        
        # 4. Perhitungan korelasi
        correlation = df['Kepadatan Penduduk'].corr(df['Jumlah Outlet'])
        
        # 5. Kecamatan dengan rasio outlet ideal
        df_ideal = df[df['Rekomendasi'] == 'Ideal']
        
        # Generate insight teks
        insights = {
            'summary': f"{prefix}Dari analisis {len(df)} kecamatan, ditemukan bahwa {len(df[df['Rekomendasi'].str.contains('Butuh outlet baru')])} kecamatan membutuhkan outlet baru, dan {len(df_ideal)} kecamatan memiliki rasio outlet yang ideal.",
            
            'expansion_recommendations': f"{prefix}Kecamatan yang paling membutuhkan outlet baru adalah: {', '.join(top_need_outlets['Kecamatan'].tolist())}. Kecamatan-kecamatan ini memiliki rasio outlet yang rendah.",
            
            'density_insights': f"{prefix}Kecamatan dengan kepadatan penduduk tertinggi adalah: {', '.join(top_density['Kecamatan'].tolist())}. Area padat penduduk ini berpotensi memiliki traffic pelanggan yang tinggi.",
            
            'outlet_distribution': f"{prefix}Distribusi outlet saat ini terkonsentrasi di kecamatan: {', '.join(top_outlets['Kecamatan'].tolist())}.",
            
            'correlation_analysis': f"{prefix}Korelasi antara kepadatan penduduk dan jumlah outlet adalah {correlation:.2f}. " + 
                                  ("Terdapat korelasi positif yang kuat." if correlation > 0.7 else 
                                   "Korelasi moderat." if correlation > 0.3 else 
                                   "Korelasi lemah."),
            
            'business_strategy': f"""
Strategi Bisnis {prefix}:
1. Ekspansi Bertahap: Fokus pembukaan outlet baru di kecamatan dengan rasio outlet sangat rendah.
2. Evaluasi Potensi: Di kecamatan dengan rasio outlet rendah, lakukan studi kelayakan.
3. Optimalisasi: Di kecamatan dengan rasio outlet ideal, pertahankan kualitas layanan.
4. Fokus Kualitas: Di kecamatan dengan rasio outlet tinggi, fokus pada peningkatan varian produk.
5. Monitoring Berkala: Lakukan analisis performa outlet secara berkala."""
        }
        
        return insights
    
    except Exception as e:
        logger.error(f"Error saat menghasilkan insight bisnis: {e}")
        return {
            'summary': "Tidak dapat menghasilkan insight bisnis karena terjadi error.",
            'error': str(e)
        }

def create_excel_report(analysis_results, output_file):
    """
    Membuat laporan Excel dengan hasil analisis
    
    Parameters:
    analysis_results (list): Hasil analisis
    output_file (str): Path file output Excel
    
    Returns:
    str: Path file output, atau None jika gagal
    """
    try:
        # Generate business insights
        business_insights = generate_business_insights(analysis_results)
        
        # Konversi ke DataFrame
        df = pd.DataFrame(analysis_results)
        
        # Buat Excel writer
        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            # Tulis dataframe ke sheet pertama
            df.to_excel(writer, sheet_name='Analisis Kecamatan', index=False)
            
            # Format angka
            workbook = writer.book
            worksheet = writer.sheets['Analisis Kecamatan']
            
            # Format untuk angka dengan koma sebagai pemisah ribuan
            format_number = workbook.add_format({'num_format': '#,##0'})
            format_float = workbook.add_format({'num_format': '#,##0.00'})
            format_ratio = workbook.add_format({'num_format': '0.000000'})
            
            # Terapkan format ke kolom
            worksheet.set_column('B:B', 15, format_number)  # Jumlah Penduduk
            worksheet.set_column('C:C', 12, format_float)   # Luas Wilayah
            worksheet.set_column('D:D', 12, format_number)  # Jumlah Outlet
            worksheet.set_column('E:E', 18, format_float)   # Kepadatan Penduduk
            worksheet.set_column('F:F', 15, format_ratio)   # Rasio Outlet
            worksheet.set_column('G:G', 30)                 # Rekomendasi
            
            # Buat sheet untuk insight bisnis
            insight_sheet = workbook.add_worksheet('Insight Bisnis')
            
            # Format untuk header
            header_format = workbook.add_format({
                'bold': True,
                'font_color': 'white',
                'bg_color': '#4472C4',
                'border': 1,
                'text_wrap': True,
                'valign': 'vcenter',
                'align': 'center'
            })
            
            # Format untuk sub header
            subheader_format = workbook.add_format({
                'bold': True,
                'font_color': '#1F4E78',
                'bg_color': '#D9E1F2',
                'border': 1,
                'text_wrap': True,
                'valign': 'vcenter'
            })
            
            # Format untuk teks normal
            text_format = workbook.add_format({
                'text_wrap': True,
                'valign': 'vcenter',
                'border': 1
            })
            
            # Judul sheet insight
            insight_sheet.merge_range('A1:E1', 'INSIGHT BISNIS ANALISIS KECAMATAN MULTI-PROVINCE', header_format)
            insight_sheet.set_row(0, 30)
            
            # Set lebar kolom
            insight_sheet.set_column('A:A', 20)
            insight_sheet.set_column('B:E', 25)
            
            # Tulis insight
            row = 2
            
            # Ringkasan
            insight_sheet.merge_range(f'A{row}:E{row}', 'RINGKASAN ANALISIS', subheader_format)
            row += 1
            insight_sheet.merge_range(f'A{row}:E{row}', business_insights['summary'], text_format)
            row += 2
            
            # Rekomendasi Ekspansi
            insight_sheet.merge_range(f'A{row}:E{row}', 'REKOMENDASI EKSPANSI', subheader_format)
            row += 1
            insight_sheet.merge_range(f'A{row}:E{row}', business_insights['expansion_recommendations'], text_format)
            row += 2
            
            # Insight Kepadatan Penduduk
            insight_sheet.merge_range(f'A{row}:E{row}', 'INSIGHT KEPADATAN PENDUDUK', subheader_format)
            row += 1
            insight_sheet.merge_range(f'A{row}:E{row}', business_insights['density_insights'], text_format)
            row += 2
            
            # Distribusi Outlet
            insight_sheet.merge_range(f'A{row}:E{row}', 'DISTRIBUSI OUTLET', subheader_format)
            row += 1
            insight_sheet.merge_range(f'A{row}:E{row}', business_insights['outlet_distribution'], text_format)
            row += 2
            
            # Analisis Korelasi
            insight_sheet.merge_range(f'A{row}:E{row}', 'ANALISIS KORELASI', subheader_format)
            row += 1
            insight_sheet.merge_range(f'A{row}:E{row}', business_insights['correlation_analysis'], text_format)
            row += 2
            
            # Strategi Bisnis
            insight_sheet.merge_range(f'A{row}:E{row}', 'STRATEGI BISNIS', subheader_format)
            row += 1
            insight_sheet.merge_range(f'A{row}:E{row+4}', business_insights['business_strategy'], text_format)
            row += 6
            
            # Timestamp
            insight_sheet.merge_range(f'A{row}:E{row}', f"Laporan dibuat pada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", workbook.add_format({'italic': True, 'align': 'right'}))
        
        logger.info(f"Laporan Excel berhasil dibuat: {output_file}")
        return os.path.abspath(output_file)
    
    except Exception as e:
        logger.error(f"Error saat membuat laporan Excel: {e}")
        return None

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

def create_modern_web_dashboard_with_province_filter(analysis_results_by_province, excel_output):
    """
    Dashboard dengan filter provinsi dan data dinamis
    
    Parameters:
    analysis_results_by_province (dict): Hasil analisis per provinsi
    excel_output (str): Path file Excel
    
    Returns:
    str: Path ke file HTML dashboard
    """
    try:
        # Folder untuk dashboard
        output_dir = os.path.dirname(excel_output)
        dashboard_file = os.path.join(output_dir, "dashboard_analisis_kecamatan.html")
        
        # Generate province options
        province_options = ""
        for province in analysis_results_by_province.keys():
            emoji = get_province_emoji(province) if province != 'LAINNYA' else '📍'
            province_options += f'<option value="{province}">{emoji} {province}</option>'
        
        # Prepare data untuk JavaScript
        js_data = {}
        province_stats = {}
        
        for province, results in analysis_results_by_province.items():
            if results:  # Only include provinces with data
                js_data[province] = results
                province_stats[province] = {
                    'total_kecamatan': len(results),
                    'total_outlets': sum(item['Jumlah Outlet'] for item in results),
                    'avg_density': sum(item['Kepadatan Penduduk'] for item in results) / len(results),
                    'avg_ratio': sum(item['Rasio Outlet'] for item in results) / len(results)
                }
        
        # Calculate overall stats
        all_results = []
        for results in analysis_results_by_province.values():
            all_results.extend(results)
        
        total_kecamatan = len(all_results)
        total_outlets = sum(item['Jumlah Outlet'] for item in all_results)
        avg_density = sum(item['Kepadatan Penduduk'] for item in all_results) / len(all_results) if all_results else 0
        avg_ratio = sum(item['Rasio Outlet'] for item in all_results) / len(all_results) if all_results else 0
        
        dashboard_html = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Analisis Kecamatan - Multi Province</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --primary-bg: #1a1a1a;
            --secondary-bg: #2d2d30;
            --card-bg: #252526;
            --border-color: #3e3e42;
            --text-primary: #cccccc;
            --text-secondary: #969696;
            --accent-orange: #FF6002;
            --accent-purple: #c586c0;
            --accent-red: #f44747;
            --accent-yellow: #dcdcaa;
            --hover-bg: #2a2d2e;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, 'Helvetica Neue', sans-serif;
            background: var(--primary-bg);
            color: var(--text-primary);
            line-height: 1.6;
            overflow-x: hidden;
        }}

        .header {{
            background: var(--secondary-bg);
            border-bottom: 1px solid var(--border-color);
            padding: 1.5rem 2rem;
            position: sticky;
            top: 0;
            z-index: 1000;
            backdrop-filter: blur(10px);
            box-shadow: 0 2px 20px rgba(0, 0, 0, 0.3);
        }}

        .header-content {{
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }}

        .header-logo-section {{
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }}

        .company-logo {{
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .logo-image {{
            height: 60px;
            width: auto;
            max-width: 200px;
            object-fit: contain;
            border-radius: 8px;
            transition: all 0.3s ease;
            filter: brightness(1.1);
        }}
        
        .logo-image:hover {{
            transform: scale(1.05);
            filter: brightness(1.2);
        }}
        
        .icon-logo {{
            width: 60px;
            height: 60px;
            border-radius: 12px;
            background: linear-gradient(135deg, var(--accent-orange), var(--accent-orange));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.8rem;
            color: white;
            font-weight: bold;
            transition: all 0.3s ease;
        }}
        
        .icon-logo:hover {{
            transform: scale(1.05) rotate(5deg);
            box-shadow: 0 8px 25px rgba(0, 122, 204, 0.4);
        }}

        .brand-identity {{
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }}

        .header-title {{
            font-size: 1.8rem;
            font-weight: 600;
            background: linear-gradient(135deg, var(--accent-orange), var(--accent-orange));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .header-subtitle {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 0.25rem;
        }}

        .header-actions {{
            display: flex;
            gap: 1rem;
            align-items: center;
            flex-wrap: wrap;
        }}

        .btn {{
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s ease;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.9rem;
        }}

        .btn-primary {{
            background: var(--accent-orange);
            color: white;
        }}

        .btn-primary:hover {{
            background: #005a9e;
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 122, 204, 0.3);
        }}

        .btn-success {{
            background: var(--accent-orange);
            color: white;
        }}

        .btn-success:hover {{
            background: #3ba690;
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(78, 201, 176, 0.3);
        }}

        .main-container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
            min-height: calc(100vh - 120px);
        }}

        .province-filter {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            transition: all 0.3s ease;
        }}

        .filter-select {{
            padding: 10px 15px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            background: var(--secondary-bg);
            color: var(--text-primary);
            font-size: 14px;
            min-width: 200px;
            cursor: pointer;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}

        .stat-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
        }}

        .stat-number {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--accent-orange), var(--accent-orange));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .stat-label {{
            color: var(--text-secondary);
            font-size: 1rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 500;
        }}

        @media (max-width: 768px) {{
            .header-content {{
                flex-direction: column;
                text-align: center;
            }}

            .main-container {{
                padding: 1rem;
            }}

            .stats-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-content">
            <div class="header-logo-section">
                <div class="company-logo">
                    <img src="logo.png" alt="Company Logo" class="logo-image" 
                         onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                    <div class="icon-logo" style="display: none;">
                        <i class="fas fa-chart-line"></i>
                    </div>
                </div>
                <div class="brand-identity">
                    <h1 class="header-title">Dashboard Analisis Kecamatan</h1>
                    <p class="header-subtitle">Sistem analisis distribusi outlet per kecamatan dengan filter multi-provinsi</p>
                </div>
            </div>
            <div class="header-actions">
                <a href="hasil_analisis_kecamatan.xlsx" class="btn btn-success" download>
                    <i class="fas fa-file-excel"></i>
                    Download Excel
                </a>
                <a href="/" class="btn btn-primary">
                    <i class="fas fa-map"></i>
                    Maps Dashboard
                </a>
            </div>
        </div>
    </header>

    <div class="main-container">
        <!-- Province Filter Panel -->
        <div class="province-filter">
            <label for="province-filter">🗺️ Filter Provinsi:</label>
            <select id="province-filter" class="filter-select" onchange="filterByProvince()">
                <option value="ALL">🌏 Semua Provinsi</option>
                {province_options}
            </select>
        </div>

        <div class="stats-grid" id="stats-grid">
            <!-- Will be populated by JavaScript -->
        </div>

        <div style="text-align: center; color: var(--text-secondary); margin-top: 3rem;">
            <p>Dashboard Enhanced Kecamatan Analysis • Generated on {datetime.now().strftime('%d %B %Y, %H:%M WIB')}</p>
        </div>
    </div>

    <script>
        // Data provinsi dari backend
        const provinceData = {json.dumps(js_data, ensure_ascii=False)};
        const provinceStats = {json.dumps(province_stats, ensure_ascii=False)};
        
        let currentProvince = 'ALL';
        let currentData = [];
        
        // Initialize
        document.addEventListener('DOMContentLoaded', function() {{
            updateCurrentData();
            updateStatsGrid();
        }});
        
        function filterByProvince() {{
            const select = document.getElementById('province-filter');
            currentProvince = select.value;
            
            updateCurrentData();
            updateStatsGrid();
        }}
        
        function updateCurrentData() {{
            if (currentProvince === 'ALL') {{
                currentData = [];
                Object.values(provinceData).forEach(provinceResults => {{
                    currentData = currentData.concat(provinceResults);
                }});
            }} else {{
                currentData = provinceData[currentProvince] || [];
            }}
        }}
        
        function updateStatsGrid() {{
            const statsGrid = document.getElementById('stats-grid');
            
            if (currentData.length === 0) {{
                statsGrid.innerHTML = '<div class="stat-card"><div class="stat-number">0</div><div class="stat-label">Tidak ada data</div></div>';
                return;
            }}
            
            const totalKecamatan = currentData.length;
            const totalOutlets = currentData.reduce((sum, item) => sum + item['Jumlah Outlet'], 0);
            const avgDensity = currentData.reduce((sum, item) => sum + item['Kepadatan Penduduk'], 0) / totalKecamatan;
            const avgRatio = currentData.reduce((sum, item) => sum + item['Rasio Outlet'], 0) / totalKecamatan;
            
            statsGrid.innerHTML = `
                <div class="stat-card">
                    <div class="stat-number">${{totalKecamatan}}</div>
                    <div class="stat-label">Total Kecamatan</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${{totalOutlets}}</div>
                    <div class="stat-label">Total Outlets</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${{avgDensity.toFixed(0)}}</div>
                    <div class="stat-label">Rata-rata Kepadatan</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${{avgRatio.toFixed(6)}}</div>
                    <div class="stat-label">Rasio Coverage</div>
                </div>
            `;
        }}
    </script>
</body>
</html>"""
        
        # Tulis ke file HTML
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            f.write(dashboard_html)
        
        logger.info(f"Enhanced dashboard dengan filter provinsi berhasil dibuat: {dashboard_file}")
        return os.path.abspath(dashboard_file)
    
    except Exception as e:
        logger.error(f"Error saat membuat dashboard: {e}")
        return None

def export_province_specific_excel(analysis_results_by_province, base_filename):
    """
    Export Excel files per province
    
    Parameters:
    analysis_results_by_province (dict): Hasil analisis per provinsi
    base_filename (str): Base filename untuk Excel
    """
    for province, results in analysis_results_by_province.items():
        if province != 'LAINNYA' and results:
            province_filename = base_filename.replace('.xlsx', f'_{province.lower().replace(" ", "_").replace("/", "_")}.xlsx')
            excel_path = create_excel_report(results, province_filename)
            if excel_path:
                logger.info(f"Excel report created for {province}: {province_filename}")

def main():
    """
    Fungsi utama dengan dukungan multi-province filtering
    """
    try:
        logger.info("Memulai analisis kecamatan multi-province dengan enhanced filtering")
        
        # Pastikan direktori output ada
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # 1. Muat data dari spreadsheet
        logger.info("Memuat data dari Google Spreadsheet...")
        outlet_data = load_data_from_spreadsheet()
        
        if not outlet_data:
            logger.error("Tidak ada data outlet yang valid. Program dibatalkan.")
            return False
        
        # 2. Muat data dari JSON yang sudah ada
        logger.info(f"Memuat data JSON dari {JSON_INPUT}...")
        json_data = load_existing_json(JSON_INPUT)
        
        if not json_data:
            logger.error("Data JSON tidak ditemukan atau kosong. Program dibatalkan.")
            return False
        
        # 3. Tambahkan kolom Kecamatan ke JSON
        logger.info("Menambahkan informasi kecamatan ke data JSON...")
        updated_json = add_kecamatan_to_json(json_data, outlet_data)
        
        # 4. Simpan ke JSON baru
        logger.info(f"Menyimpan data JSON yang diperbarui ke {JSON_OUTPUT}...")
        json_path = save_json_file(updated_json, JSON_OUTPUT)
        
        if not json_path:
            logger.warning("Gagal menyimpan data JSON yang diperbarui.")
        
        # 5. Muat data kecamatan dari Excel
        logger.info("Memuat data kecamatan dari file Excel...")
        kecamatan_file = "rekapan_kecamatan.xlsx"
        kecamatan_data = load_kecamatan_data(kecamatan_file)
        
        if not kecamatan_data:
            logger.error(f"Tidak ada data kecamatan yang valid dari {kecamatan_file}. Program dibatalkan.")
            return False
        
        # 6. Group outlets by province
        logger.info("Mengelompokkan outlet berdasarkan provinsi...")
        outlets_by_province = group_outlets_by_province_kecamatan(updated_json)
        
        # 7. Analyze each province separately
        logger.info("Menganalisis data per provinsi...")
        analysis_results_by_province = {}
        for province, province_outlets in outlets_by_province.items():
            logger.info(f"Analyzing {province}: {len(province_outlets)} outlets")
            analysis_results = analyze_kecamatan_data_by_province(
                province_outlets, kecamatan_data, province
            )
            if analysis_results:
                analysis_results_by_province[province] = analysis_results
                logger.info(f"✅ {province}: {len(analysis_results)} kecamatan analyzed")
            else:
                logger.warning(f"⚠️ {province}: No analysis results")
        
        # 8. Create combined results for backward compatibility
        logger.info("Menggabungkan hasil semua provinsi...")
        all_results = []
        for results in analysis_results_by_province.values():
            all_results.extend(results)
        
        if not all_results:
            logger.error("Tidak ada hasil analisis yang valid. Program dibatalkan.")
            return False
        
        # 9. Buat laporan Excel gabungan
        logger.info(f"Membuat laporan Excel gabungan {EXCEL_OUTPUT}...")
        excel_path = create_excel_report(all_results, EXCEL_OUTPUT)
        
        if not excel_path:
            logger.error("Gagal membuat laporan Excel.")
            return False
        
        # 10. Export Excel per province (optional)
        logger.info("Membuat laporan Excel per provinsi...")
        export_province_specific_excel(analysis_results_by_province, EXCEL_OUTPUT)
        
        # 11. Buat enhanced dashboard dengan province filter
        logger.info("Membuat enhanced dashboard dengan filter provinsi...")
        dashboard_path = create_modern_web_dashboard_with_province_filter(
            analysis_results_by_province, EXCEL_OUTPUT
        )
        
        if dashboard_path:
            logger.info(f"✅ Enhanced dashboard berhasil dibuat: {dashboard_path}")
        else:
            logger.warning("⚠️ Gagal membuat enhanced dashboard")
        
        # 12. Summary
        logger.info("=" * 60)
        logger.info("🎉 ANALISIS KECAMATAN MULTI-PROVINCE SELESAI!")
        logger.info("=" * 60)
        logger.info(f"📊 Total kecamatan: {len(all_results)}")
        logger.info(f"🗺️ Provinsi dianalisis: {len(analysis_results_by_province)}")
        logger.info(f"📁 Output directory: {OUTPUT_DIR}")
        logger.info("📄 Files yang dibuat:")
        logger.info(f"   • Excel gabungan: {EXCEL_OUTPUT}")
        
        # List province-specific Excel files
        for province in analysis_results_by_province.keys():
            if province != 'LAINNYA':
                province_excel = EXCEL_OUTPUT.replace('.xlsx', f'_{province.lower().replace(" ", "_").replace("/", "_")}.xlsx')
                if os.path.exists(province_excel):
                    logger.info(f"   • Excel {province}: {os.path.basename(province_excel)}")
        
        if dashboard_path:
            logger.info(f"   • Dashboard: {os.path.basename(dashboard_path)}")
        
        logger.info("\n🌐 Akses dashboard:")
        logger.info("1. Jalankan: python web_server.py")
        logger.info("2. Buka: http://localhost:8080/dashboard_analisis_kecamatan.html")
        logger.info("3. Gunakan filter provinsi untuk analisis spesifik")
        
        return True
        
    except Exception as e:
        logger.error(f"Error dalam main function: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("✅ Program analisis kecamatan multi-province berhasil dijalankan!")
            print(f"📁 Output directory: {OUTPUT_DIR}")
            print(f"📊 Dashboard: http://localhost:8080/dashboard_analisis_kecamatan.html")
            print("\n🎯 Fitur yang tersedia:")
            print("   • Filter per provinsi")
            print("   • Visualisasi interaktif")
            print("   • Export Excel per provinsi")
            print("   • Rekomendasi bisnis dinamis")
        else:
            print("❌ Program selesai dengan beberapa error. Periksa log untuk detailnya.")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Program dihentikan oleh pengguna.")
        print("\n⚠️ Program dihentikan.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error tidak terduga: {e}")
        print(f"\n💥 Terjadi error tidak terduga: {e}")
        print("💡 Periksa log file untuk detail lengkap")
        sys.exit(1)
    
    input("\n📌 Tekan Enter untuk keluar...")