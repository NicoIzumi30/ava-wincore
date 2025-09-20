import time
import random
import json
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from config import (
    DEFAULT_RADIUS, MAX_WORKERS, BATCH_SIZE, 
    LARGER_RADIUS, PROGRESS_FILE, logger
)
from data_loader import parse_coordinates
from api_handler import check_nearby_facilities_simple, save_cache

def process_outlet_with_retry(outlet, max_retries=2, radius=DEFAULT_RADIUS):
    """
    Memproses satu outlet dengan memeriksa fasilitas di sekitarnya
    Dengan mekanisme retry jika terjadi error
    
    Parameters:
    outlet (dict): Data outlet yang berisi nama, koordinat
    max_retries (int): Jumlah maksimum percobaan ulang jika terjadi error
    radius (int): Radius pencarian dalam meter
    
    Returns:
    dict: Data outlet dengan hasil pengecekan fasilitas
    """
    retries = 0
    while retries < max_retries:
        try:
            # Ambil data outlet
            nama = outlet['nama']
            koordinat_str = outlet['koordinat']
            
            # Parse koordinat
            lat, lon = parse_coordinates(koordinat_str)
            
            # Periksa fasilitas di sekitar
            nearby_facilities = check_nearby_facilities_simple(lat, lon, radius)
            
            # Gabungkan data outlet dengan hasil pengecekan
            result = {
                'Nama Outlet': nama,
                'Koordinat': koordinat_str,
                'Latitude': lat,
                'Longitude': lon,
                'Residential': nearby_facilities['residential'],
                'Education': nearby_facilities['education'],
                'Public Area': nearby_facilities['public_area'],
                'Culinary': nearby_facilities['culinary'],
                'Business Center': nearby_facilities['business_center'],
                'Groceries': nearby_facilities['groceries'],               # Kategori baru
                'Convenient Stores': nearby_facilities['convenient_stores'], # Kategori baru
                'Industrial': nearby_facilities['industrial'],             # Kategori baru
                'Hospital/Clinic': nearby_facilities['hospital_clinic']    # Kategori baru
            }
            
            return result
        
        except Exception as e:
            retries += 1
            logger.warning(f"Percobaan {retries}/{max_retries} gagal untuk outlet {outlet.get('nama', 'unknown')}: {e}")
            # Jeda eksponensial backoff - kurangi untuk mempercepat
            time.sleep(1.5 ** retries)
    
    logger.error(f"Gagal memproses outlet {outlet.get('nama', 'unknown')} setelah {max_retries} percobaan")
    
    # Jika semua percobaan gagal, kembalikan data outlet dengan nilai default False
    try:
        lat, lon = parse_coordinates(outlet['koordinat'])
        return {
            'Nama Outlet': outlet['nama'],
            'Koordinat': outlet['koordinat'],
            'Latitude': lat,
            'Longitude': lon,
            'Residential': False,
            'Education': False,
            'Public Area': False,
            'Culinary': False,
            'Business Center': False,
            'Groceries': False,               # Kategori baru
            'Convenient Stores': False,       # Kategori baru
            'Industrial': False,              # Kategori baru
            'Hospital/Clinic': False,         # Kategori baru
            'Error': 'Failed to process after multiple retries'
        }
    except:
        return None

def batch_process_outlets(outlets, batch_size=BATCH_SIZE, max_workers=MAX_WORKERS, radius=DEFAULT_RADIUS):
    """
    Memproses outlet secara batch dengan multi-threading
    
    Parameters:
    outlets (list): Daftar outlet yang akan diproses
    batch_size (int): Jumlah outlet per batch
    max_workers (int): Jumlah worker thread maksimum
    radius (int): Radius pencarian dalam meter
    
    Returns:
    list: Hasil pemrosesan untuk semua outlet
    """
    all_results = []
    
    # Bagi outlet menjadi batch
    total_outlets = len(outlets)
    num_batches = (total_outlets + batch_size - 1) // batch_size
    
    with tqdm(total=total_outlets, desc="Memproses outlet") as pbar:
        for i in range(num_batches):
            start_idx = i * batch_size
            end_idx = min((i + 1) * batch_size, total_outlets)
            batch = outlets[start_idx:end_idx]
            
            logger.info(f"Memproses batch {i+1}/{num_batches} (outlet {start_idx+1}-{end_idx})")
            
            # Proses batch dengan multi-threading
            batch_results = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_outlet = {executor.submit(process_outlet_with_retry, outlet, radius=radius): outlet for outlet in batch}
                for future in as_completed(future_to_outlet):
                    result = future.result()
                    if result:
                        batch_results.append(result)
                    pbar.update(1)
            
            all_results.extend(batch_results)
            
            # Simpan progress ke file untuk backup
            try:
                with open(PROGRESS_FILE, 'w') as f:
                    json.dump(all_results, f)
                logger.info(f"Progress disimpan ke {PROGRESS_FILE}")
            except Exception as e:
                logger.error(f"Gagal menyimpan progress: {e}")
            
            # Kurangi jeda antara batch untuk mempercepat
            if i < num_batches - 1:
                sleep_time = random.uniform(0.5, 1.5)  # 0.5-1.5 detik
                logger.info(f"Menunggu {sleep_time:.1f} detik sebelum batch berikutnya...")
                time.sleep(sleep_time)
    
    # Simpan cache di akhir proses
    save_cache()
    
    return all_results

def check_resume_point():
    """
    Memeriksa apakah ada file progress yang bisa dilanjutkan
    
    Returns:
    list: Data hasil analisis yang sudah ada, atau list kosong jika tidak ada
    """
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r') as f:
                existing_results = json.load(f)
                
            if existing_results:
                return existing_results
        except Exception as e:
            logger.warning(f"Gagal membaca file progress: {e}")
    
    return []

def get_remaining_outlets(outlets, existing_results):
    """
    Mendapatkan outlet yang belum diproses
    
    Parameters:
    outlets (list): Semua outlet yang perlu diproses
    existing_results (list): Hasil yang sudah ada
    
    Returns:
    list: Outlet yang belum diproses
    """
    # Jika tidak ada hasil existing, return semua outlet
    if not existing_results:
        return outlets
    
    # Dapatkan nama outlet yang sudah diproses
    processed_names = {result['Nama Outlet'] for result in existing_results}
    
    # Filter outlet yang belum diproses
    remaining_outlets = [outlet for outlet in outlets if outlet['nama'] not in processed_names]
    
    return remaining_outlets

def increase_detection_radius(results, new_radius=LARGER_RADIUS):
    """
    Mengulang deteksi dengan radius yang lebih besar untuk outlet tanpa fasilitas
    
    Parameters:
    results (list): Hasil analisis outlet
    new_radius (int): Radius baru untuk deteksi
    
    Returns:
    list: Hasil analisis yang diperbarui
    """
    logger.info(f"Memeriksa ulang outlet tanpa fasilitas dengan radius {new_radius}m...")
    
    outlets_without_facilities = []
    indices_without_facilities = []
    
    # Identifikasi outlet tanpa fasilitas
    categories = [
        'Residential', 'Education', 'Public Area', 'Culinary', 'Business Center',
        'Groceries', 'Convenient Stores', 'Industrial', 'Hospital/Clinic'  # Termasuk kategori baru
    ]
    
    for i, result in enumerate(results):
        if not any(result.get(category, False) for category in categories):
            outlet = {
                'nama': result['Nama Outlet'],
                'koordinat': result['Koordinat']
            }
            outlets_without_facilities.append(outlet)
            indices_without_facilities.append(i)
    
    if not outlets_without_facilities:
        logger.info("Semua outlet memiliki setidaknya satu fasilitas terdeteksi.")
        return results
    
    logger.info(f"Menemukan {len(outlets_without_facilities)} outlet tanpa fasilitas terdeteksi.")
    
    # Proses outlet tanpa fasilitas dengan radius yang lebih besar
    updated_results = batch_process_outlets(outlets_without_facilities, radius=new_radius)
    
    # Gabungkan hasil yang diperbarui ke hasil sebelumnya
    for i, updated_result in zip(indices_without_facilities, updated_results):
        if updated_result:
            results[i] = updated_result
    
    return results

def validate_and_correct_results(results):
    """
    Memungkinkan pengguna untuk memeriksa dan mengoreksi hasil deteksi secara manual
    Berguna untuk tempat yang tidak terdeteksi dengan benar oleh API
    
    Parameters:
    results (list): Hasil analisis outlet
    
    Returns:
    list: Hasil analisis yang sudah dikoreksi
    """
    logger.info("Memulai validasi dan koreksi hasil deteksi...")
    
    corrected_results = []
    
    # Definisi kategori
    categories = [
        'Residential', 'Education', 'Public Area', 'Culinary', 'Business Center',
        'Groceries', 'Convenient Stores', 'Industrial', 'Hospital/Clinic'  # Termasuk kategori baru
    ]
    
    # Validasi untuk setiap outlet
    for i, result in enumerate(results):
        print(f"\nOutlet {i+1}/{len(results)}: {result['Nama Outlet']}")
        print(f"Koordinat: {result['Koordinat']}")
        print("\nStatus deteksi saat ini:")
        
        for category in categories:
            status = "✓ Ya" if result.get(category, False) else "✗ Tidak"
            print(f"{category}: {status}")
        
        correct = input(f"\nApakah Anda ingin mengoreksi data untuk outlet ini? (y/n): ")
        
        if correct.lower() == 'y':
            corrected_result = result.copy()
            
            for category in categories:
                current_value = "Ya" if result.get(category, False) else "Tidak"
                response = input(f"{category} ({current_value}): ")
                
                if response.lower() == 'y':
                    corrected_result[category] = True
                elif response.lower() == 'n':
                    corrected_result[category] = False
                # Jika Enter, pertahankan nilai saat ini
            
            corrected_results.append(corrected_result)
            logger.info(f"Data outlet {result['Nama Outlet']} telah dikoreksi")
        else:
            corrected_results.append(result)
            logger.info(f"Data outlet {result['Nama Outlet']} tetap tidak berubah")
    
    logger.info("Validasi dan koreksi selesai!")
    return corrected_results

def generate_summary_report(results):
    """
    Menghasilkan laporan ringkasan dari hasil analisis
    
    Parameters:
    results (list): Hasil analisis outlet
    
    Returns:
    dict: Laporan ringkasan
    """
    if not results:
        return None
    
    # Hitung statistik
    total_outlets = len(results)
    categories = [
        'Residential', 'Education', 'Public Area', 'Culinary', 'Business Center',
        'Groceries', 'Convenient Stores', 'Industrial', 'Hospital/Clinic'  # Termasuk kategori baru
    ]
    
    category_counts = {}
    for category in categories:
        count = sum(1 for r in results if r.get(category, False))
        percentage = (count / total_outlets) * 100
        category_counts[category] = (count, percentage)
    
    # Temukan outlet dengan paling banyak fasilitas
    max_facilities = 0
    best_outlets = []
    
    for result in results:
        facility_count = sum(1 for category in categories if result.get(category, False))
        if facility_count > max_facilities:
            max_facilities = facility_count
            best_outlets = [result['Nama Outlet']]
        elif facility_count == max_facilities:
            best_outlets.append(result['Nama Outlet'])
    
    # Buat laporan ringkasan
    summary = {
        'total_outlets': total_outlets,
        'category_stats': category_counts,
        'max_facilities': max_facilities,
        'best_outlets': best_outlets
    }
    
    return summary