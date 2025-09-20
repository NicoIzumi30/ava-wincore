#!/usr/bin/env python3
"""
Enhanced Standalone Kecamatan Analysis Runner with Multi-Province Support
Menjalankan analisis kecamatan secara terpisah dengan opsi berbagai mode dan filter provinsi
"""

import os
import sys
import argparse
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("standalone_kecamatan.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("standalone_kecamatan")

def check_dependencies():
    """
    Cek apakah semua dependencies tersedia
    
    Returns:
    bool: True jika semua OK
    """
    required_files = [
        "kecamatan_analysis.py",
        "rekapan_kecamatan.xlsx",
        "output/hasil_analisis_outlet.json"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"File yang diperlukan tidak ditemukan: {missing_files}")
        print("\n❌ DEPENDENCIES MISSING:")
        for file in missing_files:
            print(f"   • {file}")
        
        print("\n💡 SOLUSI:")
        if "hasil_analisis_outlet.json" in str(missing_files):
            print("   • Jalankan analisis outlet terlebih dahulu dengan: python main.py")
            print("   • Atau jalankan auto_update.py untuk generate semua data")
        if "rekapan_kecamatan.xlsx" in str(missing_files):
            print("   • Sediakan file rekapan_kecamatan.xlsx dengan data kecamatan")
            print("   • Format: Kolom 1=Nama Kecamatan, Kolom 2=Luas Wilayah, Kolom 3=Jumlah Penduduk")
        if "kecamatan_analysis.py" in str(missing_files):
            print("   • Pastikan file kecamatan_analysis.py ada di directory yang sama")
        
        return False
    
    return True

def check_enhanced_features():
    """
    Cek apakah kecamatan_analysis.py sudah enhanced dengan multi-province support
    
    Returns:
    bool: True jika sudah enhanced
    """
    try:
        with open("kecamatan_analysis.py", 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for enhanced features
        enhanced_indicators = [
            "group_outlets_by_province_kecamatan",
            "create_modern_web_dashboard_with_province_filter",
            "analyze_kecamatan_data_by_province",
            "export_province_specific_excel"
        ]
        
        enhanced_count = sum(1 for indicator in enhanced_indicators if indicator in content)
        
        if enhanced_count >= 3:
            logger.info("✅ Kecamatan analysis sudah enhanced dengan multi-province support")
            return True
        else:
            logger.warning("⚠️ Kecamatan analysis belum enhanced dengan multi-province support")
            return False
            
    except Exception as e:
        logger.error(f"Error checking enhanced features: {e}")
        return False

def run_kecamatan_analysis_standalone(mode='full', output_dir="output", province_filter=None):
    """
    Menjalankan analisis kecamatan standalone dengan enhanced features
    
    Parameters:
    mode (str): Mode analisis ('full', 'quick', 'dashboard-only', 'province-specific')
    output_dir (str): Directory output
    province_filter (str): Filter provinsi spesifik (optional)
    
    Returns:
    bool: True jika berhasil
    """
    try:
        logger.info("=" * 60)
        logger.info("🚀 ENHANCED STANDALONE KECAMATAN ANALYSIS")
        logger.info("=" * 60)
        logger.info(f"Mode: {mode}")
        logger.info(f"Output directory: {output_dir}")
        if province_filter:
            logger.info(f"Province filter: {province_filter}")
        logger.info(f"Waktu mulai: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Import enhanced kecamatan_analysis
        try:
            import kecamatan_analysis
        except ImportError as e:
            logger.error(f"Gagal import kecamatan_analysis: {e}")
            return False
        
        # Pastikan output directory ada
        os.makedirs(output_dir, exist_ok=True)
        
        # Set path constants jika belum di-set
        if not hasattr(kecamatan_analysis, 'OUTPUT_DIR'):
            kecamatan_analysis.OUTPUT_DIR = output_dir
        if not hasattr(kecamatan_analysis, 'JSON_INPUT'):
            kecamatan_analysis.JSON_INPUT = os.path.join(output_dir, "hasil_analisis_outlet.json")
        if not hasattr(kecamatan_analysis, 'JSON_OUTPUT'):
            kecamatan_analysis.JSON_OUTPUT = os.path.join(output_dir, "hasil_analisis_kecamatan.json")
        if not hasattr(kecamatan_analysis, 'EXCEL_OUTPUT'):
            kecamatan_analysis.EXCEL_OUTPUT = os.path.join(output_dir, "hasil_analisis_kecamatan.xlsx")
        
        # Jalankan berdasarkan mode
        if mode == 'dashboard-only':
            logger.info("🎨 Mode: Dashboard Only - Hanya membuat dashboard dari data yang ada")
            success = run_dashboard_only_mode(kecamatan_analysis, output_dir)
            
        elif mode == 'quick':
            logger.info("⚡ Mode: Quick - Analisis cepat tanpa visualisasi tambahan")
            success = run_quick_mode(kecamatan_analysis, output_dir, province_filter)
            
        elif mode == 'province-specific':
            logger.info(f"🗺️ Mode: Province-Specific - Analisis khusus untuk {province_filter}")
            success = run_province_specific_mode(kecamatan_analysis, output_dir, province_filter)
            
        else:  # mode == 'full'
            logger.info("🔄 Mode: Full - Analisis lengkap dengan semua output dan multi-province")
            success = run_full_mode(kecamatan_analysis, output_dir)
        
        if success:
            logger.info("✅ Enhanced kecamatan analysis standalone berhasil!")
            show_enhanced_results_summary(output_dir, mode, province_filter)
        else:
            logger.error("❌ Enhanced kecamatan analysis standalone gagal!")
        
        return success
        
    except Exception as e:
        logger.error(f"Error dalam enhanced standalone kecamatan analysis: {e}")
        return False

def run_dashboard_only_mode(kecamatan_module, output_dir):
    """
    Mode dashboard-only: Hanya buat enhanced dashboard dari data yang sudah ada
    """
    try:
        # Cek apakah file hasil analisis sudah ada
        excel_file = os.path.join(output_dir, "hasil_analisis_kecamatan.xlsx")
        json_file = os.path.join(output_dir, "hasil_analisis_kecamatan.json")
        
        if not os.path.exists(json_file):
            logger.error("File hasil_analisis_kecamatan.json tidak ditemukan")
            logger.info("💡 Jalankan mode 'full' atau 'quick' terlebih dahulu")
            return False
        
        # Load existing analysis results
        with open(json_file, 'r', encoding='utf-8') as f:
            import json
            analysis_results = json.load(f)
        
        if not analysis_results:
            logger.error("Data analisis kosong")
            return False
        
        logger.info(f"Menggunakan data analisis yang ada: {len(analysis_results)} item")
        
        # Group by province untuk enhanced dashboard
        if hasattr(kecamatan_module, 'group_outlets_by_province_kecamatan'):
            # Untuk backward compatibility, buat dummy province grouping dari hasil existing
            analysis_results_by_province = {'SEMUA': analysis_results}
            
            # Buat enhanced dashboard dengan multi-province support
            if hasattr(kecamatan_module, 'create_modern_web_dashboard_with_province_filter'):
                dashboard_path = kecamatan_module.create_modern_web_dashboard_with_province_filter(
                    analysis_results_by_province, excel_file
                )
            else:
                # Fallback ke dashboard biasa
                dashboard_path = kecamatan_module.create_modern_web_dashboard(analysis_results, excel_file)
        else:
            # Original dashboard
            dashboard_path = kecamatan_module.create_modern_web_dashboard(analysis_results, excel_file)
        
        if dashboard_path:
            logger.info(f"✅ Enhanced dashboard berhasil dibuat: {dashboard_path}")
            return True
        else:
            logger.error("❌ Gagal membuat enhanced dashboard")
            return False
            
    except Exception as e:
        logger.error(f"Error dalam dashboard-only mode: {e}")
        return False

def run_quick_mode(kecamatan_module, output_dir, province_filter=None):
    """
    Mode quick: Analisis cepat dengan optional province filter
    """
    try:
        # Load data dari spreadsheet
        logger.info("📥 Memuat data dari spreadsheet...")
        outlet_data = kecamatan_module.load_data_from_spreadsheet()
        
        if not outlet_data:
            logger.error("Tidak ada data outlet dari spreadsheet")
            return False
        
        # Load data JSON
        json_input = os.path.join(output_dir, "hasil_analisis_outlet.json")
        logger.info(f"📥 Memuat data JSON dari {json_input}...")
        json_data = kecamatan_module.load_existing_json(json_input)
        
        if not json_data:
            logger.error("Data JSON outlet tidak ditemukan")
            return False
        
        # Enhance JSON dengan kecamatan
        logger.info("🔗 Menambahkan informasi kecamatan...")
        updated_json = kecamatan_module.add_kecamatan_to_json(json_data, outlet_data)
        
        # Load data kecamatan
        logger.info("📊 Memuat data kecamatan dari Excel...")
        kecamatan_data = kecamatan_module.load_kecamatan_data("rekapan_kecamatan.xlsx")
        
        if not kecamatan_data:
            logger.error("Data kecamatan tidak valid")
            return False
        
        # Enhanced analysis dengan province support
        if hasattr(kecamatan_module, 'analyze_kecamatan_data_by_province'):
            logger.info("🧮 Melakukan enhanced analisis dengan province support...")
            analysis_results = kecamatan_module.analyze_kecamatan_data_by_province(
                updated_json, kecamatan_data, province_filter
            )
        else:
            logger.info("🧮 Melakukan analisis standard...")
            analysis_results = kecamatan_module.analyze_kecamatan_data(updated_json, kecamatan_data)
        
        if not analysis_results:
            logger.error("Gagal melakukan analisis")
            return False
        
        # Simpan hasil
        json_output = os.path.join(output_dir, "hasil_analisis_kecamatan.json")
        excel_output = os.path.join(output_dir, "hasil_analisis_kecamatan.xlsx")
        
        kecamatan_module.save_json_file(analysis_results, json_output)
        kecamatan_module.create_excel_report(analysis_results, excel_output)
        
        # Group results by province for enhanced dashboard
        if hasattr(kecamatan_module, 'group_outlets_by_province_kecamatan'):
            outlets_by_province = kecamatan_module.group_outlets_by_province_kecamatan(updated_json)
            analysis_results_by_province = {}
            
            for province in outlets_by_province.keys():
                province_results = kecamatan_module.analyze_kecamatan_data_by_province(
                    updated_json, kecamatan_data, province
                )
                if province_results:
                    analysis_results_by_province[province] = province_results
            
            # Buat enhanced dashboard
            logger.info("🎨 Membuat enhanced dashboard dengan multi-province support...")
            dashboard_path = kecamatan_module.create_modern_web_dashboard_with_province_filter(
                analysis_results_by_province, excel_output
            )
        else:
            # Fallback to standard dashboard
            logger.info("🎨 Membuat standard dashboard...")
            dashboard_path = kecamatan_module.create_modern_web_dashboard(analysis_results, excel_output)
        
        if dashboard_path:
            logger.info(f"✅ Dashboard berhasil dibuat: {dashboard_path}")
            return True
        else:
            logger.error("❌ Gagal membuat dashboard")
            return False
            
    except Exception as e:
        logger.error(f"Error dalam quick mode: {e}")
        return False

def run_province_specific_mode(kecamatan_module, output_dir, province_filter):
    """
    Mode province-specific: Analisis khusus untuk provinsi tertentu
    """
    try:
        if not province_filter:
            logger.error("Province filter harus ditentukan untuk mode province-specific")
            return False
        
        logger.info(f"🗺️ Menjalankan analisis khusus untuk provinsi: {province_filter}")
        
        # Jalankan quick mode dengan province filter
        return run_quick_mode(kecamatan_module, output_dir, province_filter)
        
    except Exception as e:
        logger.error(f"Error dalam province-specific mode: {e}")
        return False

def run_full_mode(kecamatan_module, output_dir):
    """
    Mode full: Analisis lengkap dengan enhanced multi-province features
    """
    try:
        # Jalankan enhanced main function
        logger.info("🔄 Menjalankan enhanced analisis lengkap...")
        success = kecamatan_module.main()
        
        if success:
            logger.info("✅ Enhanced analisis lengkap berhasil")
            
            # Generate additional visualizations if available
            if hasattr(kecamatan_module, 'generate_detailed_visualizations'):
                logger.info("📊 Membuat visualisasi tambahan...")
                excel_file = os.path.join(output_dir, "hasil_analisis_kecamatan.xlsx")
                json_file = os.path.join(output_dir, "hasil_analisis_kecamatan.json")
                
                if os.path.exists(json_file):
                    with open(json_file, 'r', encoding='utf-8') as f:
                        import json
                        analysis_results = json.load(f)
                    
                    if analysis_results:
                        kecamatan_module.generate_detailed_visualizations(analysis_results, excel_file)
            
            # Generate API export if available
            if hasattr(kecamatan_module, 'export_analysis_for_api'):
                logger.info("🔌 Membuat export untuk API...")
                # Placeholder for API export - needs actual province data
                # kecamatan_module.export_analysis_for_api({}, json_file)
            
            return True
        else:
            logger.error("❌ Enhanced analisis lengkap gagal")
            return False
            
    except Exception as e:
        logger.error(f"Error dalam full mode: {e}")
        return False

def show_enhanced_results_summary(output_dir, mode, province_filter=None):
    """
    Tampilkan ringkasan hasil enhanced analysis
    """
    logger.info("=" * 60)
    logger.info("📁 RINGKASAN ENHANCED OUTPUT")
    logger.info("=" * 60)
    
    expected_files = [
        ("hasil_analisis_kecamatan.xlsx", "📊 Excel Report Utama"),
        ("hasil_analisis_kecamatan.json", "📄 JSON Data"),
        ("dashboard_analisis_kecamatan.html", "🎨 Enhanced Dashboard HTML"),
        ("visualisasi/", "📈 Folder Visualisasi"),
    ]
    
    # Check for province-specific Excel files
    if mode in ['full', 'quick']:
        try:
            files_in_output = os.listdir(output_dir)
            province_excels = [f for f in files_in_output if f.startswith('hasil_analisis_kecamatan_') and f.endswith('.xlsx')]
            
            if province_excels:
                logger.info(f"📊 Excel per provinsi ditemukan: {len(province_excels)} files")
                for excel_file in province_excels[:5]:  # Show first 5
                    province_name = excel_file.replace('hasil_analisis_kecamatan_', '').replace('.xlsx', '').replace('_', ' ').title()
                    expected_files.append((excel_file, f"📊 Excel {province_name}"))
                
                if len(province_excels) > 5:
                    logger.info(f"   ... dan {len(province_excels) - 5} file Excel provinsi lainnya")
        except:
            pass
    
    for filename, description in expected_files:
        filepath = os.path.join(output_dir, filename)
        if os.path.exists(filepath):
            if os.path.isdir(filepath):
                try:
                    file_count = len([f for f in os.listdir(filepath) if f.endswith(('.png', '.jpg', '.jpeg'))])
                    logger.info(f"✅ {description}: {filepath} ({file_count} files)")
                except:
                    logger.info(f"✅ {description}: {filepath}")
            else:
                try:
                    file_size = os.path.getsize(filepath) / 1024  # KB
                    logger.info(f"✅ {description}: {filepath} ({file_size:.1f} KB)")
                except:
                    logger.info(f"✅ {description}: {filepath}")
        else:
            logger.warning(f"⚠️ {description}: Tidak ditemukan")
    
    # Enhanced access instructions
    logger.info("\n🌐 ENHANCED ACCESS:")
    logger.info("1. Jalankan web server: python web_server.py")
    logger.info("2. Dashboard Enhanced: http://localhost:8080/dashboard_analisis_kecamatan.html")
    logger.info("3. Features:")
    logger.info("   • 🗺️ Filter per provinsi")
    logger.info("   • 📊 Interactive charts")
    logger.info("   • 📱 Responsive design")
    logger.info("   • 📈 Real-time updates")
    
    if province_filter:
        logger.info(f"4. Mode: {mode} untuk provinsi {province_filter}")
    else:
        logger.info(f"4. Mode: {mode} untuk semua provinsi")

def interactive_enhanced_mode_selection():
    """
    Enhanced interactive mode selection dengan province options
    """
    print("🎯 PILIH MODE ENHANCED KECAMATAN ANALYSIS")
    print("=" * 50)
    print("1. 🔄 Full - Enhanced analisis lengkap dengan multi-province (recommended)")
    print("2. ⚡ Quick - Analisis cepat dengan province filter")
    print("3. 🗺️ Province-Specific - Analisis khusus satu provinsi")
    print("4. 🎨 Dashboard Only - Update enhanced dashboard dari data existing")
    print("5. ❌ Cancel")
    
    while True:
        try:
            choice = input("\nPilih mode (1-5): ").strip()
            
            if choice == "1":
                return "full", None
            elif choice == "2":
                return "quick", None
            elif choice == "3":
                # Pilih provinsi untuk mode specific
                province = select_province_filter()
                if province:
                    return "province-specific", province
                else:
                    continue
            elif choice == "4":
                return "dashboard-only", None
            elif choice == "5":
                print("❌ Dibatalkan")
                return None, None
            else:
                print("⚠️ Pilihan tidak valid, masukkan 1-5")
                
        except KeyboardInterrupt:
            print("\n❌ Dibatalkan oleh user")
            return None, None

def select_province_filter():
    """
    Interactive province selection
    """
    provinces = [
        "DKI JAKARTA",
        "JAWA BARAT", 
        "JAWA TENGAH",
        "SUMATERA BAGIAN SELATAN",
        "SUMATERA BAGIAN UTARA"
    ]
    
    print("\n🗺️ PILIH PROVINSI:")
    for i, province in enumerate(provinces, 1):
        emoji_map = {
            "DKI JAKARTA": "🏙️",
            "JAWA BARAT": "🏔️",
            "JAWA TENGAH": "🏛️",
            "SUMATERA BAGIAN SELATAN": "🌴",
            "SUMATERA BAGIAN UTARA": "🌿"
        }
        emoji = emoji_map.get(province, "📍")
        print(f"{i}. {emoji} {province}")
    print(f"{len(provinces) + 1}. ❌ Kembali")
    
    while True:
        try:
            choice = input(f"\nPilih provinsi (1-{len(provinces) + 1}): ").strip()
            
            if choice.isdigit():
                choice_num = int(choice)
                if 1 <= choice_num <= len(provinces):
                    selected_province = provinces[choice_num - 1]
                    print(f"✅ Provinsi dipilih: {selected_province}")
                    return selected_province
                elif choice_num == len(provinces) + 1:
                    return None
                else:
                    print(f"⚠️ Pilihan tidak valid, masukkan 1-{len(provinces) + 1}")
            else:
                print(f"⚠️ Masukkan nomor 1-{len(provinces) + 1}")
                
        except KeyboardInterrupt:
            return None

def main():
    """
    Enhanced main function dengan argument parsing dan province support
    """
    parser = argparse.ArgumentParser(
        description="Enhanced Standalone Kecamatan Analysis Runner with Multi-Province Support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_kecamatan_analysis.py                              # Interactive mode
  python run_kecamatan_analysis.py --mode full                  # Full enhanced analysis
  python run_kecamatan_analysis.py --mode quick                 # Quick analysis
  python run_kecamatan_analysis.py --mode province-specific --province "DKI JAKARTA"
  python run_kecamatan_analysis.py --mode dashboard-only        # Enhanced dashboard only
  python run_kecamatan_analysis.py --check                      # Check dependencies only
        """
    )
    
    parser.add_argument(
        "--mode", 
        choices=["full", "quick", "dashboard-only", "province-specific"],
        help="Mode analisis (default: interactive)"
    )
    
    parser.add_argument(
        "--province",
        choices=["DKI JAKARTA", "JAWA BARAT", "JAWA TENGAH", "SUMATERA BAGIAN SELATAN", "SUMATERA BAGIAN UTARA"],
        help="Filter provinsi untuk mode province-specific"
    )
    
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory (default: output)"
    )
    
    parser.add_argument(
        "--check",
        action="store_true",
        help="Hanya cek dependencies tanpa menjalankan analisis"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging level
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    print("🔍 ENHANCED STANDALONE KECAMATAN ANALYSIS")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Check enhanced features
    enhanced = check_enhanced_features()
    if not enhanced:
        print("⚠️ Warning: kecamatan_analysis.py belum enhanced dengan multi-province support")
        print("💡 Sistem akan berjalan dengan fitur terbatas")
    
    if args.check:
        if enhanced:
            print("✅ Semua dependencies tersedia dan enhanced features terdeteksi!")
        else:
            print("✅ Dependencies tersedia, tapi enhanced features tidak terdeteksi")
        return 0
    
    # Determine mode and province
    if args.mode:
        mode = args.mode
        province_filter = args.province
        
        # Validation
        if mode == 'province-specific' and not province_filter:
            print("❌ Mode province-specific memerlukan --province parameter")
            return 4
        
        print(f"Mode: {mode}")
        if province_filter:
            print(f"Province filter: {province_filter}")
    else:
        mode, province_filter = interactive_enhanced_mode_selection()
        if not mode:
            return 0
    
    # Run enhanced analysis
    start_time = datetime.now()
    success = run_kecamatan_analysis_standalone(mode, args.output_dir, province_filter)
    end_time = datetime.now()
    
    duration = end_time - start_time
    
    if success:
        print(f"\n🎉 ENHANCED ANALISIS SELESAI!")
        print(f"⏱️ Durasi: {duration}")
        print(f"📁 Output: {args.output_dir}")
        if enhanced:
            print("🎯 Enhanced features: Multi-province filtering tersedia")
        return 0
    else:
        print(f"\n❌ ENHANCED ANALISIS GAGAL!")
        print(f"💡 Cek log file untuk detail error")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Dibatalkan oleh user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n💥 Error tidak terduga: {e}")
        sys.exit(1)