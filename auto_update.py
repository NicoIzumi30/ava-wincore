import os
import time
import json
import sys
import shutil
from datetime import datetime
import socket
import importlib.util
import traceback

from config import (
    DEFAULT_OUTPUT_EXCEL, DEFAULT_OUTPUT_MAP, 
    DEFAULT_RADIUS, LARGER_RADIUS, SPREADSHEET_ID, logger,
    get_all_province_map_files
)
from data_loader import load_data_from_spreadsheet, update_spreadsheet_with_results
from facility_analyzer import (
    batch_process_outlets, check_resume_point, 
    increase_detection_radius, generate_summary_report
)
from excel_generator import create_excel_with_checkmarks, add_summary_sheet
from map_generator import generate_multi_province_maps
from utils import save_json_file
from multi_province_utils import group_outlets_by_province, validate_province_data
from indomaret_handler import IndomaretHandler

# Fungsi cleanup yang diperbarui untuk multi-province
def cleanup_old_files(output_dir, keep_days=30):
    """
    Menghapus file output yang lebih tua dari keep_days
    Termasuk file province maps dan laporan Indomaret
    """
    now = time.time()
    keep_seconds = keep_days * 24 * 60 * 60
    
    count = 0
    protected_files = ["latest", "index", "maps_index", "metadata", "indomaret_competition_report", "dashboard_analisis_kecamatan"]
    
    for f in os.listdir(output_dir):
        # Lewati file yang dilindungi
        if any(protected in f.lower() for protected in protected_files):
            continue
            
        # Hanya hapus file yang relevan
        if not any(ext in f for ext in [".xlsx", ".html", ".json"]):
            continue
            
        file_path = os.path.join(output_dir, f)
        
        # Jika file lebih tua dari keep_days, hapus
        if os.path.isfile(file_path) and os.stat(file_path).st_mtime < (now - keep_seconds):
            try:
                os.remove(file_path)
                count += 1
                logger.info(f"Deleted old file: {f}")
            except Exception as e:
                logger.warning(f"Gagal menghapus file lama {f}: {e}")
    
    if count > 0:
        logger.info(f"Berhasil menghapus {count} file lama")

def create_latest_symlinks(output_dir, generated_files):
    """
    Membuat symlink/copy untuk file latest
    
    Parameters:
    output_dir (str): Direktori output
    generated_files (dict): Dictionary file yang dibuat
    """
    try:
        # Latest full map
        if generated_files.get('full'):
            full_map_latest = os.path.join(output_dir, "peta_outlet_latest.html")
            try:
                if os.path.exists(full_map_latest):
                    os.remove(full_map_latest)
                shutil.copy2(generated_files['full'], full_map_latest)
                logger.info(f"Created latest full map: {full_map_latest}")
            except Exception as e:
                logger.warning(f"Failed to create latest full map symlink: {e}")
        
        # Latest province maps dengan prefix
        for province, path in generated_files.get('provinces', {}).items():
            try:
                filename = os.path.basename(path)
                latest_filename = filename.replace('.html', '_latest.html')
                latest_path = os.path.join(output_dir, latest_filename)
                
                if os.path.exists(latest_path):
                    os.remove(latest_path)
                shutil.copy2(path, latest_path)
                logger.info(f"Created latest province map: {latest_filename}")
            except Exception as e:
                logger.warning(f"Failed to create latest province map for {province}: {e}")
        
        # Latest Indomaret report
        if generated_files.get('indomaret_report'):
            latest_report = os.path.join(output_dir, "indomaret_report_latest.json")
            try:
                if os.path.exists(latest_report):
                    os.remove(latest_report)
                shutil.copy2(generated_files['indomaret_report'], latest_report)
                logger.info(f"Created latest Indomaret report: {latest_report}")
            except Exception as e:
                logger.warning(f"Failed to create latest Indomaret report: {e}")
                
    except Exception as e:
        logger.error(f"Error creating latest symlinks: {e}")

def run_enhanced_kecamatan_analysis(output_dir):
    """
    Menjalankan enhanced kecamatan analysis dengan multi-province support
    
    Parameters:
    output_dir (str): Direktori output
    
    Returns:
    dict: Status dan informasi hasil analisis
    """
    try:
        logger.info("=" * 60)
        logger.info("📊 MENJALANKAN ENHANCED KECAMATAN ANALYSIS")
        logger.info("=" * 60)
        
        # Cek apakah file kecamatan_analysis.py ada
        kecamatan_file = "kecamatan_analysis.py"
        if not os.path.exists(kecamatan_file):
            logger.error(f"File {kecamatan_file} tidak ditemukan")
            return {
                'success': False,
                'error': f'File {kecamatan_file} tidak ditemukan',
                'enhanced': False
            }
        
        # Cek apakah file rekapan_kecamatan.xlsx ada
        rekapan_file = "rekapan_kecamatan.xlsx"
        if not os.path.exists(rekapan_file):
            logger.warning(f"File {rekapan_file} tidak ditemukan, analisis kecamatan mungkin tidak berjalan dengan baik")
        
        # Check enhanced features
        enhanced_features = check_enhanced_kecamatan_features(kecamatan_file)
        
        # Import kecamatan_analysis sebagai modul
        spec = importlib.util.spec_from_file_location("kecamatan_analysis", kecamatan_file)
        if spec is None or spec.loader is None:
            logger.error(f"Gagal memuat spesifikasi modul dari {kecamatan_file}")
            return {
                'success': False,
                'error': f'Gagal memuat spesifikasi modul dari {kecamatan_file}',
                'enhanced': False
            }
        
        kecamatan_module = importlib.util.module_from_spec(spec)
        
        # Tambahkan ke sys.modules sebelum eksekusi
        sys.modules["kecamatan_analysis"] = kecamatan_module
        
        # Eksekusi modul
        spec.loader.exec_module(kecamatan_module)
        
        # Set output directory
        if hasattr(kecamatan_module, 'OUTPUT_DIR'):
            kecamatan_module.OUTPUT_DIR = output_dir
        
        # Jalankan fungsi main
        if hasattr(kecamatan_module, 'main'):
            logger.info("Menjalankan enhanced main function dari kecamatan_analysis...")
            kecamatan_success = kecamatan_module.main()
            
            if kecamatan_success:
                logger.info("✅ Enhanced kecamatan analysis berhasil dijalankan")
                
                # Cek file output yang dihasilkan
                expected_files = {
                    'excel_main': os.path.join(output_dir, "hasil_analisis_kecamatan.xlsx"),
                    'json_data': os.path.join(output_dir, "hasil_analisis_kecamatan.json"),
                    'dashboard': os.path.join(output_dir, "dashboard_analisis_kecamatan.html"),
                    'visualisasi_folder': os.path.join(output_dir, "visualisasi")
                }
                
                # Check for province-specific Excel files
                province_excels = []
                try:
                    files_in_output = os.listdir(output_dir)
                    province_excels = [f for f in files_in_output if f.startswith('hasil_analisis_kecamatan_') and f.endswith('.xlsx')]
                    logger.info(f"Ditemukan {len(province_excels)} file Excel per provinsi")
                except:
                    pass
                
                created_files = []
                for file_key, file_path in expected_files.items():
                    if os.path.exists(file_path):
                        logger.info(f"✅ {file_key} berhasil dibuat: {os.path.basename(file_path)}")
                        created_files.append(file_key)
                    else:
                        logger.warning(f"⚠️ {file_key} tidak ditemukan: {os.path.basename(file_path)}")
                
                return {
                    'success': True,
                    'enhanced': enhanced_features,
                    'created_files': created_files,
                    'province_excels': province_excels,
                    'dashboard_available': 'dashboard' in created_files,
                    'visualizations_available': 'visualisasi_folder' in created_files
                }
            else:
                logger.error("❌ Enhanced kecamatan analysis gagal dijalankan")
                return {
                    'success': False,
                    'error': 'Enhanced kecamatan analysis gagal dijalankan',
                    'enhanced': enhanced_features
                }
        else:
            logger.error("❌ Fungsi main tidak ditemukan dalam modul kecamatan_analysis")
            return {
                'success': False,
                'error': 'Fungsi main tidak ditemukan dalam modul kecamatan_analysis',
                'enhanced': enhanced_features
            }
            
    except ImportError as e:
        logger.error(f"❌ Error import kecamatan_analysis: {e}")
        logger.error("Pastikan semua dependencies untuk kecamatan_analysis tersedia")
        return {
            'success': False,
            'error': f'Error import kecamatan_analysis: {e}',
            'enhanced': False
        }
    except Exception as e:
        logger.error(f"❌ Error saat menjalankan enhanced kecamatan analysis: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            'success': False,
            'error': f'Error saat menjalankan enhanced kecamatan analysis: {e}',
            'enhanced': False
        }

def check_enhanced_kecamatan_features(kecamatan_file):
    """
    Cek apakah kecamatan_analysis.py sudah enhanced dengan multi-province support
    
    Parameters:
    kecamatan_file (str): Path ke file kecamatan_analysis.py
    
    Returns:
    bool: True jika sudah enhanced
    """
    try:
        with open(kecamatan_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for enhanced features
        enhanced_indicators = [
            "group_outlets_by_province_kecamatan",
            "create_modern_web_dashboard_with_province_filter",
            "analyze_kecamatan_data_by_province",
            "export_province_specific_excel",
            "province_filter"
        ]
        
        enhanced_count = sum(1 for indicator in enhanced_indicators if indicator in content)
        
        if enhanced_count >= 3:
            logger.info("✅ Kecamatan analysis enhanced dengan multi-province support")
            return True
        else:
            logger.warning("⚠️ Kecamatan analysis belum enhanced dengan multi-province support")
            return False
            
    except Exception as e:
        logger.error(f"Error checking enhanced features: {e}")
        return False

def create_enhanced_dashboard(update_time, output_dir, generated_files, indomaret_stats=None, kecamatan_info=None):
    """
    Membuat enhanced dashboard HTML dengan peta multi-province, link download, info Indomaret, dan kecamatan
    
    Parameters:
    update_time (datetime): Waktu update
    output_dir (str): Direktori output
    generated_files (dict): Dictionary file yang dibuat
    indomaret_stats (dict): Statistik Indomaret (optional)
    kecamatan_info (dict): Informasi hasil kecamatan analysis (optional)
    """
    # Buat dropdown untuk pemilihan province
    province_options = ""
    if generated_files.get('full'):
        province_options += '<option value="peta_outlet_full.html">🌏 Semua Provinsi</option>'
    
    for province, path in generated_files.get('provinces', {}).items():
        filename = os.path.basename(path)
        from multi_province_utils import get_province_emoji
        emoji = get_province_emoji(province)
        province_options += f'<option value="{filename}">{emoji} {province}</option>'
    
    # Statistik maps
    total_maps = len(generated_files.get('provinces', {}))
    if generated_files.get('full'):
        total_maps += 1
    
    # Info Indomaret untuk dashboard
    indomaret_info = ""
    if indomaret_stats:
        indomaret_info = f"""
        <div style="background: #1e88e5; padding: 8px 15px; border-radius: 6px; font-size: 12px; color: white; margin-left: 10px;">
            <i class="fas fa-store"></i> {indomaret_stats.get('total_stores', 0)} Indomaret
        </div>
        """
    
    # Info Kecamatan untuk dashboard
    kecamatan_info_widget = ""
    if kecamatan_info and kecamatan_info.get('success'):
        kecamatan_count = len(kecamatan_info.get('province_excels', []))
        enhanced_text = "Enhanced" if kecamatan_info.get('enhanced') else "Standard"
        kecamatan_info_widget = f"""
        <div style="background: #9c27b0; padding: 8px 15px; border-radius: 6px; font-size: 12px; color: white; margin-left: 10px;">
            <i class="fas fa-map-marked-alt"></i> {enhanced_text} Kecamatan ({kecamatan_count} provinsi)
        </div>
        """
    
    # Quick links untuk Indomaret dan Kecamatan
    additional_links = ""
    if generated_files.get('indomaret_report'):
        indomaret_report_filename = os.path.basename(generated_files['indomaret_report'])
        additional_links += f"""
            <a href="{indomaret_report_filename}" download class="indomaret-report">
                <i class="fas fa-chart-pie"></i> Laporan Indomaret
            </a>
        """
    
    # Enhanced link dashboard kecamatan
    kecamatan_dashboard = os.path.join(output_dir, "dashboard_analisis_kecamatan.html")
    if os.path.exists(kecamatan_dashboard):
        enhanced_label = "Enhanced " if kecamatan_info and kecamatan_info.get('enhanced') else ""
        additional_links += f"""
            <a href="dashboard_analisis_kecamatan.html" target="_blank" class="kecamatan-dashboard">
                <i class="fas fa-map-marked-alt"></i> {enhanced_label}Dashboard Kecamatan
            </a>
        """
    
    dashboard_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Enhanced Dashboard Analisis Outlet - Multi Province + Indomaret + Kecamatan</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
    <style>
        body {{ margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
        
        #header {{
            background: #2c3e50;
            color: white;
            padding: 15px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .header-left {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .header-logo {{
            height: 50px;
            border-radius: 5px;
        }}
        
        .header-title {{
            font-size: 1.5rem;
            font-weight: 600;
            margin: 0;
        }}
        
        .province-selector {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .province-selector select {{
            padding: 8px 15px;
            border-radius: 6px;
            border: 1px solid #bdc3c7;
            background: white;
            font-size: 14px;
            font-weight: 500;
            min-width: 200px;
            cursor: pointer;
        }}
        
        .stats-info {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .stats-info > div {{
            background: #34495e;
            padding: 8px 15px;
            border-radius: 6px;
            font-size: 12px;
        }}
        
        #content {{
            display: flex;
            flex-direction: column;
            height: calc(100vh - 80px);
        }}
        
        #map-container {{
            flex-grow: 1;
            position: relative;
        }}
        
        #map-iframe {{
            width: 100%;
            height: 100%;
            border: none;
        }}
        
        #footer {{
            background-color: #34495e;
            color: white;
            padding: 10px 20px;
            text-align: center;
            font-size: 14px;
        }}
        
        .quick-links {{
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }}
        
        .quick-links a {{
            padding: 6px 12px;
            background: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-size: 12px;
            transition: background 0.3s;
        }}
        
        .quick-links a:hover {{
            background: #2980b9;
        }}
        
        .quick-links a.index {{
            background: #27ae60;
        }}
        
        .quick-links a.index:hover {{
            background: #229954;
        }}
        
        .quick-links a.indomaret-report {{
            background: #1e88e5;
        }}
        
        .quick-links a.indomaret-report:hover {{
            background: #1976d2;
        }}
        
        .quick-links a.kecamatan-dashboard {{
            background: #9c27b0;
        }}
        
        .quick-links a.kecamatan-dashboard:hover {{
            background: #7b1fa2;
        }}
        
        /* Enhanced features indicator */
        .enhanced-indicator {{
            background: linear-gradient(45deg, #FF6002, #ff8c42);
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 5px;
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0% {{ opacity: 1; }}
            50% {{ opacity: 0.7; }}
            100% {{ opacity: 1; }}
        }}
        
        @media (max-width: 768px) {{
            #header {{
                flex-direction: column;
                text-align: center;
            }}
            
            .province-selector select {{
                min-width: 150px;
            }}
            
            .quick-links {{
                justify-content: center;
            }}
        }}
    </style>
</head>
<body>    
    <div id="content">
        <div id="map-container">
            <iframe id="map-iframe" src="{'peta_outlet_full.html' if generated_files.get('full') else list(generated_files.get('provinces', {}).values())[0] if generated_files.get('provinces') else 'maps_index.html'}"></iframe>
        </div>
    </div>
    
    
    <script>
    function changeMap(filename) {{
        if (filename) {{
            document.getElementById('map-iframe').src = filename;
        }}
    }}
    
    // Auto-select based on URL parameter
    const urlParams = new URLSearchParams(window.location.search);
    const selectedProvince = urlParams.get('province');
    if (selectedProvince) {{
        const select = document.getElementById('province-select');
        const option = select.querySelector(`option[value="${{selectedProvince}}"]`);
        if (option) {{
            select.value = selectedProvince;
            changeMap(selectedProvince);
        }}
    }}
    </script>
</body>
</html>
"""
    
    dashboard_output = os.path.join(output_dir, "index.html")
    
    try:
        with open(dashboard_output, 'w', encoding='utf-8') as f:
            f.write(dashboard_html)
            
        logger.info(f"Enhanced multi-province dashboard berhasil dibuat: {dashboard_output}")
        return True
    except Exception as e:
        logger.error(f"Error saat membuat enhanced dashboard: {e}")
        return False

def auto_update():
    """
    Fungsi untuk pembaruan otomatis data dan pembuatan multi-province maps dengan enhanced integrasi Indomaret dan Kecamatan
    Dijalankan tanpa interaksi pengguna
    """
    timestamp_dt = datetime.now()
    timestamp = timestamp_dt.strftime("%Y-%m-%d_%H-%M-%S")
    logger.info(f"Memulai enhanced pembaruan otomatis multi-province pada {timestamp}")
    
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Nama file output dengan timestamp
    excel_file = os.path.join(output_dir, f"analisis_outlet_{timestamp}.xlsx")
    json_file = os.path.join(output_dir, f"hasil_analisis_{timestamp}.json")
    
    # Nama file untuk link permanen (selalu diganti dengan hasil terbaru)
    permanent_excel = os.path.join(output_dir, "analisis_outlet_latest.xlsx")
    permanent_json = os.path.join(output_dir, "hasil_analisis_outlet.json")
    
    # Initialize Indomaret handler
    indomaret_handler = None
    indomaret_stats = None
    
    # Cek ketersediaan data Indomaret
    default_indomaret_paths = [
        "indomaret_data.json",
        "data_indomaret.json", 
        "indomaret.json"
    ]
    
    indomaret_file = None
    for path in default_indomaret_paths:
        if os.path.exists(path):
            indomaret_file = path
            logger.info(f"Ditemukan file data Indomaret: {path}")
            break
    
    if indomaret_file:
        logger.info(f"Memuat data Indomaret dari {indomaret_file}...")
        indomaret_handler = IndomaretHandler(indomaret_file)
        
        if indomaret_handler.indomaret_data:
            indomaret_stats = indomaret_handler.get_indomaret_statistics()
            logger.info(f"Data Indomaret berhasil dimuat: {indomaret_stats['total_stores']} toko di {indomaret_stats['total_kecamatan']} kecamatan")
        else:
            logger.warning("Gagal memuat data Indomaret, lanjut tanpa integrasi")
            indomaret_handler = None
    else:
        logger.info("File data Indomaret tidak ditemukan, lanjut tanpa integrasi Indomaret")
    
    try:
        # Muat data dari Google Spreadsheet
        logger.info("Mengambil data dari Google Spreadsheet...")
        outlets = load_data_from_spreadsheet()
        
        if not outlets:
            logger.error("Tidak ada data outlet yang valid dalam spreadsheet.")
            return False
        
        logger.info(f"Berhasil memuat {len(outlets)} outlet dari spreadsheet.")
        
        # Proses outlet secara batch
        logger.info(f"Memulai analisis outlet dengan radius {DEFAULT_RADIUS}m...")
        results = batch_process_outlets(outlets)
        
        if not results:
            logger.error("Tidak ada hasil yang diperoleh dari analisis.")
            return False
        
        # Periksa ulang outlet tanpa fasilitas dengan radius lebih besar
        logger.info(f"Memeriksa outlet tanpa fasilitas dengan radius {LARGER_RADIUS}m...")
        results = increase_detection_radius(results, LARGER_RADIUS)
        
        # Enhance data dengan informasi Indomaret jika tersedia
        if indomaret_handler:
            logger.info("Mengintegrasikan data Indomaret dengan outlet...")
            results = indomaret_handler.enhance_outlet_data_with_indomaret(results)
            
            # Log statistik integrasi
            outlets_with_indomaret = sum(1 for r in results if r.get('Has_Indomaret', False))
            logger.info(f"Integrasi Indomaret selesai: {outlets_with_indomaret}/{len(results)} outlet di kecamatan dengan Indomaret")
        
        # Perbarui spreadsheet dengan hasil analisis
        logger.info("Memperbarui spreadsheet dengan hasil analisis...")
        update_spreadsheet_with_results(results)
        
        # Buat ringkasan hasil
        summary = generate_summary_report(results)
        
        # Validasi data untuk multi-province
        outlets_by_province = group_outlets_by_province(results)
        validation = validate_province_data(outlets_by_province)
        logger.info(f"Province validation: {validation['summary']}")
        
        # Simpan hasil ke JSON
        save_json_file(results, json_file)
        logger.info(f"Hasil analisis disimpan ke {json_file}")
        
        # Buat salinan sebagai latest
        save_json_file(results, permanent_json)
        
        # Buat file Excel dengan checklist
        excel_path = create_excel_with_checkmarks(results, excel_file)
        if excel_path:
            # Tambahkan lembar ringkasan ke file Excel
            add_summary_sheet(excel_path, summary)
            logger.info(f"File Excel berhasil dibuat: {excel_path}")
            
            # Buat salinan sebagai latest
            shutil.copy2(excel_path, permanent_excel)
            logger.info(f"Salinan terbaru Excel: {permanent_excel}")
        
        # Buat multi-province maps dengan integrasi Indomaret - INI YANG UTAMA!
        logger.info("=" * 60)
        logger.info("🗺️  MEMBUAT MULTI-PROVINCE MAPS + INDOMARET")
        logger.info("=" * 60)
        
        generated_files = generate_multi_province_maps(
            results=results,
            output_dir=output_dir,
            excel_file=permanent_excel,
            indomaret_json_path=indomaret_file
        )
        
        if generated_files:
            logger.info("✅ Multi-province maps dengan Indomaret berhasil dibuat!")
            
            # Buat symlinks untuk file latest
            create_latest_symlinks(output_dir, generated_files)
            
            # Log semua file yang dibuat
            logger.info("📁 Files yang dibuat:")
            if generated_files.get('full'):
                logger.info(f"   🌏 Full map: {os.path.basename(generated_files['full'])}")
            
            for province, path in generated_files.get('provinces', {}).items():
                # Hitung statistik Indomaret untuk provinsi
                indomaret_count = 0
                if indomaret_handler:
                    for outlet in outlets_by_province.get(province, []):
                        indomaret_count += outlet.get('Indomaret_Count', 0)
                
                logger.info(f"   🗺️  {province}: {os.path.basename(path)} ({indomaret_count} Indomaret)")
            
            # Log Indomaret report jika ada
            if generated_files.get('indomaret_report'):
                logger.info(f"   📊 Indomaret report: {os.path.basename(generated_files['indomaret_report'])}")
                
        else:
            logger.error("❌ Gagal membuat multi-province maps")
        
        # Generate Indomaret report terpisah jika handler tersedia
        if indomaret_handler:
            logger.info("Membuat laporan kompetisi Indomaret...")
            indomaret_report = indomaret_handler.generate_indomaret_report(results)
            
            if indomaret_report:
                # Log insights dari laporan
                insights = indomaret_report.get('insights', {})
                if 'competition_analysis' in insights:
                    logger.info(f"Kompetisi: {insights['competition_analysis']}")
                if 'market_opportunity' in insights:
                    logger.info(f"Peluang: {insights['market_opportunity']}")
        
        # Jalankan ENHANCED kecamatan analysis dengan multi-province support
        logger.info("=" * 60)
        logger.info("📊 MENJALANKAN ENHANCED KECAMATAN ANALYSIS")
        logger.info("=" * 60)
        
        kecamatan_info = run_enhanced_kecamatan_analysis(output_dir)
        
        if kecamatan_info['success']:
            logger.info("✅ Enhanced kecamatan analysis berhasil dijalankan")
            
            if kecamatan_info.get('enhanced'):
                logger.info("🎯 Enhanced features: Multi-province filtering tersedia")
            
            if kecamatan_info.get('dashboard_available'):
                logger.info(f"📊 Enhanced dashboard tersedia di: dashboard_analisis_kecamatan.html")
            
            if kecamatan_info.get('province_excels'):
                logger.info(f"📊 Excel per provinsi: {len(kecamatan_info['province_excels'])} files")
            
            if kecamatan_info.get('visualizations_available'):
                logger.info("📈 Visualisasi tambahan tersedia")
        else:
            logger.error("❌ Enhanced kecamatan analysis gagal dijalankan")
            logger.error(f"Error: {kecamatan_info.get('error', 'Unknown error')}")
        
        # Buat enhanced dashboard HTML multi-province dengan semua link dan info
        create_enhanced_dashboard(timestamp_dt, output_dir, generated_files, indomaret_stats, kecamatan_info)
        
        # Catat ringkasan statistik
        logger.info("=" * 60)
        logger.info("📊 RINGKASAN HASIL ENHANCED ANALISIS")
        logger.info("=" * 60)
        for category, (count, percentage) in summary['category_stats'].items():
            logger.info(f"{category}: {count} outlet ({percentage:.1f}%)")
        
        # Ringkasan Indomaret
        if indomaret_handler:
            logger.info("=" * 60)
            logger.info("🏪 RINGKASAN INDOMARET")
            logger.info("=" * 60)
            indomaret_report = indomaret_handler.generate_indomaret_report(results)
            if indomaret_report:
                summary_data = indomaret_report.get('summary', {})
                logger.info(f"Total Indomaret di area outlet: {summary_data.get('total_indomaret_in_outlet_areas', 0)}")
                logger.info(f"Outlet dengan kompetisi: {summary_data.get('outlets_with_indomaret', 0)}")
                logger.info(f"Outlet tanpa kompetisi: {summary_data.get('outlets_without_indomaret', 0)}")
                logger.info(f"Persentase kompetisi: {summary_data.get('percentage_with_indomaret', 0):.1f}%")
        
        # Ringkasan Enhanced Kecamatan
        if kecamatan_info['success']:
            logger.info("=" * 60)
            logger.info("📊 RINGKASAN ENHANCED KECAMATAN ANALYSIS")
            logger.info("=" * 60)
            logger.info(f"Status: {'Enhanced' if kecamatan_info.get('enhanced') else 'Standard'}")
            logger.info(f"Dashboard: {'✅' if kecamatan_info.get('dashboard_available') else '❌'}")
            logger.info(f"Excel per provinsi: {len(kecamatan_info.get('province_excels', []))}")
            logger.info(f"Visualisasi: {'✅' if kecamatan_info.get('visualizations_available') else '❌'}")
        
        # Ringkasan Multi-Province Maps
        logger.info("=" * 60)
        logger.info("🗺️  RINGKASAN ENHANCED MULTI-PROVINCE SYSTEM")
        logger.info("=" * 60)
        logger.info(f"Total maps dibuat: {len(generated_files.get('provinces', {})) + (1 if generated_files.get('full') else 0)}")
        logger.info(f"Full map: {'✅' if generated_files.get('full') else '❌'}")
        logger.info(f"Province maps: {len(generated_files.get('provinces', {}))}")
        logger.info(f"Indomaret integration: {'✅' if indomaret_handler else '❌'}")
        logger.info(f"Enhanced kecamatan analysis: {'✅' if kecamatan_info['success'] else '❌'}")
        
        for province in outlets_by_province.keys():
            if province in generated_files.get('provinces', {}):
                # Hitung Indomaret di provinsi
                indomaret_count = 0
                if indomaret_handler:
                    for outlet in outlets_by_province.get(province, []):
                        indomaret_count += outlet.get('Indomaret_Count', 0)
                logger.info(f"  ✅ {province} ({indomaret_count} Indomaret)")
            else:
                logger.info(f"  ❌ {province} (tidak dikonfigurasi)")
        
        # Bersihkan file lama
        cleanup_old_files(output_dir)
        
        # Tampilkan URL akses
        try:
            ip_address = socket.gethostbyname(socket.gethostname())
            logger.info("=" * 60)
            logger.info("🌐 AKSES ENHANCED SYSTEM")
            logger.info("=" * 60)
            logger.info(f"Dashboard utama: http://{ip_address}:8080")
            logger.info(f"Maps index: http://{ip_address}:8080/maps_index.html")
            if generated_files.get('full'):
                logger.info(f"Full map: http://{ip_address}:8080/{os.path.basename(generated_files['full'])}")
            if generated_files.get('indomaret_report'):
                logger.info(f"Laporan Indomaret: http://{ip_address}:8080/{os.path.basename(generated_files['indomaret_report'])}")
            if kecamatan_info['success'] and kecamatan_info.get('dashboard_available'):
                enhanced_label = "Enhanced " if kecamatan_info.get('enhanced') else ""
                logger.info(f"{enhanced_label}Dashboard Kecamatan: http://{ip_address}:8080/dashboard_analisis_kecamatan.html")
        except:
            logger.info(f"Enhanced pembaruan selesai. System tersedia di port 8080")
        
        return True
        
    except Exception as e:
        logger.error(f"Error saat enhanced pembaruan otomatis: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    # Jalankan enhanced pembaruan otomatis
    success = auto_update()
    sys.exit(0 if success else 1)