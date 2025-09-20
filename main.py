import os
import time
import sys
import json
from tqdm import tqdm

from config import (
    DEFAULT_OUTPUT_EXCEL, DEFAULT_OUTPUT_MAP, 
    DEFAULT_RADIUS, LARGER_RADIUS, logger,
    get_all_province_map_files, set_clustering_mode, get_clustering_info
)
from data_loader import load_data_from_spreadsheet, update_spreadsheet_with_results
from facility_analyzer import (
    batch_process_outlets, check_resume_point, get_remaining_outlets, 
    increase_detection_radius, validate_and_correct_results, generate_summary_report
)
from excel_generator import create_excel_with_checkmarks, add_summary_sheet
from map_generator import generate_multi_province_maps
from utils import check_required_files, format_time, save_json_file
from multi_province_utils import group_outlets_by_province, validate_province_data
from indomaret_handler import IndomaretHandler

def main():
    """
    Fungsi utama program dengan dukungan multi-province maps dan integrasi Indomaret
    """
    print("=" * 80)
    print("    PROGRAM ANALISIS OUTLET - MULTI-PROVINCE MAPS + INDOMARET")
    print("=" * 80)
    
    start_time = time.time()
    
    # Cek file yang diperlukan
    if not check_required_files():
        print("Program tidak dapat dilanjutkan. Harap sediakan file yang diperlukan.")
        return
    
    # Cek ketersediaan data Indomaret
    indomaret_file = None
    default_indomaret_paths = [
        "indomaret_data.json",
        "data_indomaret.json", 
        "indomaret.json"
    ]
    
    for path in default_indomaret_paths:
        if os.path.exists(path):
            indomaret_file = path
            print(f"✅ Ditemukan file data Indomaret: {path}")
            break
    
    if not indomaret_file:
        print("⚠️  File data Indomaret tidak ditemukan.")
        use_sample = input("Buat file contoh data Indomaret? (y/n): ")
        if use_sample.lower() == 'y':
            from indomaret_handler import create_sample_indomaret_data
            indomaret_file = create_sample_indomaret_data()
            if indomaret_file:
                print(f"✅ File contoh dibuat: {indomaret_file}")
                print("💡 Silakan isi file ini dengan data Indomaret yang sebenarnya.")
        else:
            print("🔄 Program akan berjalan tanpa integrasi Indomaret.")
    
    # Initialize Indomaret handler jika ada data
    indomaret_handler = None
    if indomaret_file:
        print(f"\n🏪 Memuat data Indomaret dari {indomaret_file}...")
        indomaret_handler = IndomaretHandler(indomaret_file)
        
        if indomaret_handler.indomaret_data:
            stats = indomaret_handler.get_indomaret_statistics()
            print(f"✅ Data Indomaret berhasil dimuat:")
            print(f"   • Total toko: {stats['total_stores']}")
            print(f"   • Total kecamatan: {stats['total_kecamatan']}")
            
            # Tampilkan beberapa contoh
            sample_stores = indomaret_handler.indomaret_data[:3]
            print("   • Contoh data:")
            for store in sample_stores:
                print(f"     - {store['Store']} di {store['Kecamatan']}")
            if len(indomaret_handler.indomaret_data) > 3:
                print(f"     ... dan {len(indomaret_handler.indomaret_data) - 3} toko lainnya")
        else:
            print("❌ Gagal memuat data Indomaret, program akan berjalan tanpa integrasi")
            indomaret_handler = None
    
    # Cek apakah ada data yang bisa dilanjutkan
    existing_results = check_resume_point()
    if existing_results:
        print(f"\nDitemukan {len(existing_results)} outlet yang sudah diproses sebelumnya.")
        resume = input("Lanjutkan dari data terakhir? (y/n): ")
        if resume.lower() != 'y':
            existing_results = []
    
    # Muat data dari Google Spreadsheet
    print("\nMengambil data dari Google Spreadsheet...")
    outlets = load_data_from_spreadsheet()
    
    if not outlets:
        print("Tidak ada data outlet yang valid dalam spreadsheet. Program dibatalkan.")
        return
    
    print(f"Berhasil memuat {len(outlets)} outlet dari spreadsheet.")
    
    # Tampilkan beberapa outlet sebagai contoh
    print("\nContoh data outlet:")
    for i, outlet in enumerate(outlets[:3], 1):
        print(f"{i}. {outlet['nama']} - Koordinat: {outlet['koordinat']}")
    
    if len(outlets) > 3:
        print(f"... dan {len(outlets) - 3} outlet lainnya")
    
    # Jika sudah ada hasil sebelumnya
    if existing_results:
        outlets = get_remaining_outlets(outlets, existing_results)
        print(f"\nAkan melanjutkan analisis untuk {len(outlets)} outlet yang tersisa")
        
        if not outlets:
            print("Semua outlet sudah diproses sebelumnya!")
            results = existing_results
        else:
            # Konfirmasi sebelum melanjutkan
            print(f"\nAkan menganalisis outlet yang tersisa dengan radius {DEFAULT_RADIUS} meter")
            print("Catatan: Proses ini akan memakan waktu karena menggunakan API eksternal")
            
            proceed = input("\nLanjutkan? (y/n): ")
            if proceed.lower() != 'y':
                print("Program dibatalkan")
                return
            
            # Proses outlet yang tersisa secara batch
            print("\nMemulai analisis outlet yang tersisa...")
            new_results = batch_process_outlets(outlets)
            
            # Gabungkan hasil baru dengan hasil yang sudah ada
            results = existing_results + new_results
    
    # Jika belum ada hasil sebelumnya
    else:
        # Konfirmasi sebelum melanjutkan
        print(f"\nAkan menganalisis {len(outlets)} outlet dengan radius {DEFAULT_RADIUS} meter")
        print("Catatan: Proses ini akan memakan waktu karena menggunakan API eksternal")
        
        proceed = input("\nLanjutkan? (y/n): ")
        if proceed.lower() != 'y':
            print("Program dibatalkan")
            return
        
        # Proses outlet secara batch
        print("\nMemulai analisis outlet...")
        results = batch_process_outlets(outlets)
    
    if not results:
        print("Tidak ada hasil yang diperoleh. Silakan coba lagi.")
        return
    
    # Cek apakah ada outlet tanpa fasilitas terdeteksi dan tawarkan untuk memeriksa ulang dengan radius lebih besar
    check_larger_radius = input(f"\nApakah Anda ingin memeriksa ulang outlet tanpa fasilitas dengan radius lebih besar ({LARGER_RADIUS}m)? (y/n): ")
    if check_larger_radius.lower() == 'y':
        radius_size = input(f"Masukkan radius baru dalam meter (default: {LARGER_RADIUS}): ")
        new_radius = LARGER_RADIUS  # Default
        if radius_size.isdigit():
            new_radius = int(radius_size)
        results = increase_detection_radius(results, new_radius)
    
    # Validasi dan koreksi hasil deteksi
    manual_validation = input("\nApakah Anda ingin melakukan validasi manual untuk hasil deteksi? (y/n): ")
    if manual_validation.lower() == 'y':
        results = validate_and_correct_results(results)
    
    # Enhance data dengan informasi Indomaret jika tersedia
    if indomaret_handler:
        print("\n🏪 Mengintegrasikan data Indomaret dengan outlet...")
        results = indomaret_handler.enhance_outlet_data_with_indomaret(results)
        
        # Tampilkan statistik integrasi
        outlets_with_indomaret = sum(1 for r in results if r.get('Has_Indomaret', False))
        print(f"✅ Integrasi selesai:")
        print(f"   • {outlets_with_indomaret} outlet berada di kecamatan dengan Indomaret")
        print(f"   • {len(results) - outlets_with_indomaret} outlet di kecamatan tanpa Indomaret")
        
        # Generate dan tampilkan laporan kompetisi
        print("\n📊 Membuat laporan kompetisi Indomaret...")
        indomaret_report = indomaret_handler.generate_indomaret_report(results)
        
        if indomaret_report:
            summary = indomaret_report.get('summary', {})
            print(f"   • Tingkat kompetisi: {summary.get('percentage_with_indomaret', 0):.1f}% outlet menghadapi kompetisi")
            print(f"   • Total Indomaret di area outlet: {summary.get('total_indomaret_in_outlet_areas', 0)}")
            
            # Tampilkan insight
            insights = indomaret_report.get('insights', {})
            if 'competition_analysis' in insights:
                print(f"   • {insights['competition_analysis']}")
    
    # Perbarui spreadsheet dengan hasil analisis
    update_spreadsheet = input("\nApakah Anda ingin memperbarui spreadsheet dengan hasil analisis? (y/n): ")
    if update_spreadsheet.lower() == 'y':
        print("Memperbarui spreadsheet dengan hasil analisis...")
        update_spreadsheet_with_results(results)
    
    # Preview multi-province system dengan info Indomaret
    print("\n" + "=" * 60)
    print("🗺️  MULTI-PROVINCE MAPS SYSTEM + INDOMARET INTEGRATION")
    print("=" * 60)
    
    # Validasi data untuk multi-province
    outlets_by_province = group_outlets_by_province(results)
    validation = validate_province_data(outlets_by_province)
    
    print(f"Total outlet: {validation['summary']['total_outlets']}")
    print(f"Provinsi dengan data: {validation['summary']['total_provinces_with_data']}")
    print(f"Maps yang akan dibuat: {validation['summary']['maps_to_generate'] + 1}")  # +1 untuk full map
    print()
    print("Provinsi yang akan dibuat maps:")
    for province, outlets in outlets_by_province.items():
        if province in ['JAKARTA', 'JAWA BARAT', 'JAWA TENGAH', 'SUMBAGSEL', 'SUMBAGUT', 'JATIMBALIKAL', 'SULTER']:
            # Hitung Indomaret di provinsi ini
            indomaret_in_province = 0
            if indomaret_handler:
                for outlet in outlets:
                    indomaret_in_province += outlet.get('Indomaret_Count', 0)
            
            print(f"  ✅ {province}: {len(outlets)} outlets, {indomaret_in_province} Indomaret")
        else:
            print(f"  ⚠️  {province}: {len(outlets)} outlets (tidak dikonfigurasi)")
    
    # Tampilkan warnings jika ada
    for warning in validation['warnings']:
        print(f"⚠️  {warning}")
    
    # Konfirmasi untuk melanjutkan
    proceed_maps = input(f"\nLanjutkan membuat {validation['summary']['maps_to_generate'] + 1} maps dengan integrasi Indomaret? (y/n): ")
    if proceed_maps.lower() != 'y':
        print("Hanya akan membuat file Excel tanpa maps.")
        create_excel_only = True
    else:
        create_excel_only = False
        
        # Opsi clustering untuk performa optimal
        total_all_outlets = sum(len(outlets) for outlets in outlets_by_province.values())
        clustering_info = get_clustering_info()
        
        print(f"\n🔧 OPTIMASI CLUSTERING")
        print(f"Total outlet: {total_all_outlets}")
        print(f"Mode clustering saat ini: {clustering_info['mode'].upper()}")
        
        if total_all_outlets > 500:
            print("\n💡 Dataset besar terdeteksi. Pilih mode clustering:")
            print("1. Auto (default) - Otomatis berdasarkan ukuran")
            print("2. Performance - Performa tinggi, clustering agresif")
            print("3. Quality - Kualitas visual tinggi, clustering minimal")
            print("4. Disabled - Nonaktifkan clustering (tidak disarankan)")
            
            clustering_choice = input("Pilih mode (1-4, Enter untuk default): ")
            
            if clustering_choice == '2':
                set_clustering_mode('performance')
                print("✅ Mode PERFORMANCE diaktifkan - Map akan lebih ringan")
            elif clustering_choice == '3':
                set_clustering_mode('quality')
                print("✅ Mode QUALITY diaktifkan - Visual lebih detail")
            elif clustering_choice == '4':
                set_clustering_mode('disabled')
                print("⚠️ Mode DISABLED - Clustering dinonaktifkan")
            else:
                set_clustering_mode('auto')
                print("✅ Mode AUTO diaktifkan - Otomatis optimal")
        else:
            print(f"ℹ️ Dataset sedang ({total_all_outlets} outlets), menggunakan mode AUTO optimal")
    
    # Tanyakan nama file output
    excel_name = input(f"\nMasukkan nama file Excel output (default: {DEFAULT_OUTPUT_EXCEL}): ")
    if not excel_name:
        excel_name = DEFAULT_OUTPUT_EXCEL
    if not excel_name.endswith(".xlsx"):
        excel_name += ".xlsx"
    
    # Setup output directory
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    excel_file = os.path.join(output_dir, excel_name)
    
    # Simpan hasil ke JSON
    json_file = os.path.join(output_dir, "hasil_analisis_outlet.json")
    try:
        save_json_file(results, json_file)
        print(f"Hasil analisis disimpan ke {json_file}")
    except Exception as e:
        print(f"Error saat menyimpan file JSON: {e}")
    
    # Buat ringkasan hasil
    summary = generate_summary_report(results)
    
    # Buat file Excel dengan checklist
    try:
        excel_path = create_excel_with_checkmarks(results, excel_file)
        if excel_path:
            # Tambahkan lembar ringkasan ke file Excel
            add_summary_sheet(excel_path, summary)
            print(f"\n✅ File Excel berhasil dibuat: {excel_path}")
    except Exception as e:
        print(f"❌ Error saat membuat file Excel: {e}")
    
    # Buat multi-province maps dengan integrasi Indomaret jika dipilih
    if not create_excel_only:
        print("\n" + "=" * 60)
        print("🗺️  MEMBUAT MULTI-PROVINCE MAPS + INDOMARET")
        print("=" * 60)
        print("Mohon tunggu, proses ini membutuhkan waktu...")
        
        try:
            generated_files = generate_multi_province_maps(
                results=results,
                output_dir=output_dir,
                excel_file=excel_path if excel_path else None,
                indomaret_json_path=indomaret_file
            )
            
            if generated_files:
                print("\n✅ Multi-province maps dengan integrasi Indomaret berhasil dibuat!")
                print("\n📁 Files yang dibuat:")
                
                # Full map
                if generated_files.get('full'):
                    full_map_file = os.path.basename(generated_files['full'])
                    print(f"   🌏 Full map: {full_map_file}")
                
                # Province maps
                for province, path in generated_files.get('provinces', {}).items():
                    province_file = os.path.basename(path)
                    outlets_count = len(outlets_by_province.get(province, []))
                    
                    # Hitung Indomaret
                    indomaret_count = 0
                    if indomaret_handler:
                        for outlet in outlets_by_province.get(province, []):
                            indomaret_count += outlet.get('Indomaret_Count', 0)
                    
                    print(f"   🗺️  {province}: {province_file} ({outlets_count} outlets, {indomaret_count} Indomaret)")
                
                # Maps index
                maps_index = os.path.join(output_dir, "maps_index.html")
                if os.path.exists(maps_index):
                    print(f"   📋 Maps index: maps_index.html")
                
                # Indomaret report
                if generated_files.get('indomaret_report'):
                    indomaret_report_file = os.path.basename(generated_files['indomaret_report'])
                    print(f"   📊 Laporan Indomaret: {indomaret_report_file}")
                
                print(f"\n🔗 Akses maps melalui:")
                print(f"   • Dashboard utama: {os.path.join(output_dir, 'index.html')}")
                print(f"   • Maps navigator: {maps_index}")
                if generated_files.get('full'):
                    print(f"   • Full map langsung: {generated_files['full']}")
                
            else:
                print("\n❌ Gagal membuat multi-province maps")
                
        except Exception as e:
            print(f"\n❌ Error saat membuat maps: {e}")
    
    # Tampilkan ringkasan hasil dengan info Indomaret
    print("\n" + "=" * 60)
    print("📊 RINGKASAN HASIL ANALISIS + INDOMARET")
    print("=" * 60)
    
    # Tampilkan statistik per kategori
    for category, (count, percentage) in summary['category_stats'].items():
        print(f"{category}: {count} outlet ({percentage:.1f}%)")
    
    # Tampilkan outlet dengan paling banyak fasilitas
    print(f"\nOutlet dengan paling banyak fasilitas ({summary['max_facilities']} fasilitas):")
    for outlet in summary['best_outlets'][:5]:  # Batasi hanya 5 outlet
        print(f"• {outlet}")
    
    if len(summary['best_outlets']) > 5:
        print(f"... dan {len(summary['best_outlets']) - 5} outlet lainnya")
    
    # Ringkasan Indomaret jika tersedia
    if indomaret_handler:
        print(f"\n🏪 Ringkasan kompetisi Indomaret:")
        indomaret_report = indomaret_handler.generate_indomaret_report(results)
        if indomaret_report:
            summary_data = indomaret_report.get('summary', {})
            print(f"   • Outlet dengan kompetisi Indomaret: {summary_data.get('outlets_with_indomaret', 0)}")
            print(f"   • Outlet tanpa kompetisi Indomaret: {summary_data.get('outlets_without_indomaret', 0)}")
            print(f"   • Persentase kompetisi: {summary_data.get('percentage_with_indomaret', 0):.1f}%")
            
            # Top kecamatan dengan Indomaret terbanyak
            top_kecamatan = indomaret_report.get('top_indomaret_kecamatan', [])
            if top_kecamatan:
                print(f"   • Kecamatan dengan Indomaret terbanyak:")
                for kecamatan, data in top_kecamatan[:3]:
                    print(f"     - {kecamatan}: {data['indomaret_stores']} toko")
    
    # Ringkasan per provinsi
    if not create_excel_only:
        print(f"\n📍 Ringkasan per provinsi:")
        for province, outlets in outlets_by_province.items():
            facilities_count = 0
            indomaret_count = 0
            
            for outlet in outlets:
                detailed_facilities = outlet.get('detailed_facilities', {})
                facilities_count += sum(len(places) for places in detailed_facilities.values())
                indomaret_count += outlet.get('Indomaret_Count', 0)
            
            status = "✅" if province in ['JAKARTA', 'JAWA BARAT', 'JAWA TENGAH', 'SUMBAGSEL', 'SUMBAGUT', 'JATIMBALIKAL', 'SULTER'] else "⚠️"
            print(f"   {status} {province}: {len(outlets)} outlets, {facilities_count} fasilitas, {indomaret_count} Indomaret")
    
    # Hitung waktu eksekusi
    end_time = time.time()
    execution_time = end_time - start_time
    
    print(f"\n⏱️ Analisis selesai dalam waktu: {format_time(execution_time)}")
    
    # Instruksi penggunaan
    if not create_excel_only and generated_files:
        print("\n" + "=" * 60)
        print("🚀 CARA MENGGUNAKAN MULTI-PROVINCE MAPS + INDOMARET")
        print("=" * 60)
        print("1. Buka web server dengan menjalankan: python web_server.py")
        print("2. Akses http://localhost:8080 di browser")
        print("3. Gunakan dropdown untuk memilih provinsi")
        print("4. Atau klik 'Maps Index' untuk navigasi visual")
        print("5. Lihat marker biru untuk Indomaret di setiap kecamatan")
        print()
        print("📁 File utama yang dapat dibuka langsung:")
        print(f"   • {os.path.join(output_dir, 'index.html')} - Dashboard utama")
        print(f"   • {os.path.join(output_dir, 'maps_index.html')} - Navigator maps")
        if generated_files.get('full'):
            print(f"   • {generated_files['full']} - Full map")
        
        # List semua province maps
        if generated_files.get('provinces'):
            print(f"\n🗺️ Maps per provinsi:")
            for province, path in generated_files.get('provinces', {}).items():
                print(f"   • {path}")
        
        # Info Indomaret report
        if generated_files.get('indomaret_report'):
            print(f"\n📊 Laporan kompetisi Indomaret:")
            print(f"   • {generated_files['indomaret_report']}")
    
    print("\n🎉 Terimakasih telah menggunakan program Multi-Province Outlet Analysis dengan Integrasi Indomaret!")

def show_help():
    """
    Menampilkan bantuan penggunaan program
    """
    print("=" * 80)
    print("    BANTUAN PROGRAM ANALISIS OUTLET MULTI-PROVINCE + INDOMARET")
    print("=" * 80)
    print()
    print("FITUR UTAMA:")
    print("• Analisis outlet berdasarkan 9 kategori fasilitas sekitar")
    print("• Maps interaktif dengan fokus per provinsi")
    print("• Integrasi data Indomaret untuk analisis kompetisi")
    print("• Export hasil ke Excel dengan visualisasi")
    print("• Dashboard web dengan navigasi antar provinsi")
    print("• Laporan kompetisi dengan kompetitor Indomaret")
    print("• Clustering marker otomatis untuk performa optimal")
    print("• Mode clustering adaptif berdasarkan ukuran dataset")
    print()
    print("PROVINSI YANG DIDUKUNG:")
    print("• Jakarta")
    print("• Jawa Barat") 
    print("• Jawa Tengah")
    print("• Sumbagsel (Sumatera Bagian Selatan)")
    print("• Sumbagut (Sumatera Bagian Utara)")
    print("• Jatimbalikal (Jawa Timur, Bali, Kalimantan)")
    print("• Sulter (Sulawesi Tenggara)")
    print()
    print("OUTPUT YANG DIHASILKAN:")
    print("• peta_outlet_full.html - Map semua provinsi")
    print("• peta_outlet_[provinsi].html - Map per provinsi") 
    print("• maps_index.html - Navigator visual")
    print("• index.html - Dashboard utama")
    print("• analisis_outlet.xlsx - Data Excel")
    print("• indomaret_competition_report.json - Laporan kompetisi")
    print()
    print("REQUIREMENTS:")
    print("• credentials.json - File Google Sheets API")
    print("• indomaret_data.json - Data toko Indomaret (opsional)")
    print("• Koneksi internet untuk Overpass API")
    print("• Python libraries sesuai requirements")
    print()
    print("FORMAT DATA INDOMARET:")
    print('• JSON array dengan format: {"Store": "nama", "Latitude": lat,')
    print('  "Longitude": lon, "Kecamatan": "nama_kecamatan"}')
    print()
    print("MODE CLUSTERING:")
    print("• Auto - Otomatis berdasarkan ukuran dataset")
    print("• Performance - Clustering agresif untuk dataset besar (>1000 outlets)")
    print("• Quality - Clustering minimal untuk detail visual maksimal")
    print("• Disabled - Nonaktifkan clustering (hanya untuk dataset kecil)")
    print()

if __name__ == "__main__":
    try:
        # Cek apakah ada argumen help
        if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
            show_help()
            sys.exit(0)
        
        # Jalankan program utama
        main()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Program dihentikan oleh pengguna.")
    except Exception as e:
        logger.error(f"Error tidak terduga: {e}")
        print(f"\n❌ Terjadi error tidak terduga: {e}")
        print("💡 Jalankan 'python main.py --help' untuk bantuan")
    
    input("\n📌 Tekan Enter untuk keluar...")