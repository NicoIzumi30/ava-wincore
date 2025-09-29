import os
import logging

# Konfigurasi utama
SPREADSHEET_ID = "1qbyTP6ec2vrwtfW1q5WAR5Iz0D8sZ28OEmF785xpm8s"  # Ganti dengan ID Google Spreadsheet Anda
SHEET_NAME = "INPUT AVA MOBILE"  # Ganti dengan nama sheet yang sesuai

# Konfigurasi untuk caching dan optimasi
CACHE_FILE = "api_ava_wincore.pkl"
MAX_WORKERS = 8  # Jumlah worker thread maksimum
BATCH_SIZE = 1000  # Ukuran batch untuk pemrosesan
ENABLE_CACHE = True  # Aktifkan cache API
USE_SIMPLIFIED_QUERIES = True  # Gunakan query yang lebih sederhana
API_TIMEOUT = 25  # Timeout API dalam detik

# Overpass API endpoints untuk redundansi
OVERPASS_ENDPOINTS = [
    "http://31.97.187.239:12345/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# Default search radius (dalam meter)
DEFAULT_RADIUS = 100
LARGER_RADIUS = 200  # Radius yang lebih besar untuk pemeriksaan ulang

# Files output - Updated untuk Multi-Province
DEFAULT_OUTPUT_EXCEL = "analisis_outlet.xlsx" 
DEFAULT_OUTPUT_MAP = "peta_outlet.html"
DEFAULT_OUTPUT_MAP_FULL = "peta_outlet_full.html"  # Map dengan semua provinsi
PROGRESS_FILE = "outlet_analysis_progress.json"

# Multi-Province Configuration
PROVINCE_MAP_PREFIX = "peta_outlet_"  # Prefix untuk file map per provinsi
PROVINCE_MAP_SUFFIX = ".html"  # Suffix untuk file map per provinsi

# Province bounds untuk zoom yang tepat per provinsi
PROVINCE_BOUNDS = {
    'JAKARTA': {
        'bounds': [[-5.899, 106.480], [-6.367, 107.078]],
        'center': [-6.133, 106.779],
        'zoom': 11,
        'filename': 'dki_jakarta'
    },
    'JAWA BARAT': {
        'bounds': [[-5.501, 105.015], [-7.641, 108.715]],
        'center': [-6.571, 106.865],
        'zoom': 8,
        'filename': 'jawa_barat'
    },
    'JAWA TENGAH': {
        'bounds': [[-5.998, 108.715], [-8.566, 111.744]], 
        'center': [-7.282, 110.229],
        'zoom': 8,
        'filename': 'jawa_tengah'
    },
    'SUMBAGSEL': {
        'bounds': [[-1.917, 100.000], [-6.385, 108.000]],
        'center': [-4.151, 104.000],
        'zoom': 7,
        'filename': 'sumatera_selatan'
    },
    'SUMBAGUT': {
        'bounds': [[6.084, 95.183], [-2.838, 104.720]],
        'center': [1.623, 99.951],
        'zoom': 7,
        'filename': 'sumatera_utara'
    },
    'JATIMBANUSKAL': {
    'bounds': [[-1.000, 110.000], [-9.500, 119.500]],
    'center': [-5.600, 113.800],
    'zoom': 6,
    'filename': 'jatimbanuskal'
},'SULTER': {
    'bounds': [[-3.000, 120.000], [-6.500, 124.000]],
    'center': [-4.800, 122.500],
    'zoom': 7,
    'filename': 'sulter'
}


}

# UI Configuration untuk Multi-Province
ENABLE_PROVINCE_NAVIGATION = True  # Aktifkan navigasi antar provinsi
NAVIGATION_STYLE = "dropdown"  # "dropdown" atau "tabs"
INCLUDE_FULL_MAP = True  # Sertakan map dengan semua provinsi

# Clustering Configuration untuk performa optimal
CLUSTERING_SETTINGS = {
    'ENABLE_CLUSTERING': True,  # Master switch untuk clustering
    'AGGRESSIVE_CLUSTERING': False,  # Mode clustering agresif untuk dataset besar
    'AUTO_AGGRESSIVE_THRESHOLD': 1000,  # Otomatis aktifkan clustering agresif di atas N outlets
    'DISABLE_CLUSTERING_THRESHOLD': 50,  # Nonaktifkan clustering di bawah N outlets
    'OUTLET_CLUSTER_RADIUS': 50,  # Radius clustering outlet (pixel)
    'FACILITY_CLUSTER_RADIUS': 40,  # Radius clustering fasilitas (pixel)
    'INDOMARET_CLUSTER_RADIUS': 60,  # Radius clustering Indomaret (pixel)
    'MAX_ZOOM_LEVEL': 15,  # Zoom maksimum sebelum cluster membuka
    'DISABLE_COVERAGE_ON_HOVER': True,  # Nonaktifkan area coverage saat hover
    'ENABLE_SPIDERFY': True,  # Aktifkan spiderfy untuk marker overlap
    'MINIMUM_CLUSTER_SIZE': 2,  # Jumlah minimum marker untuk membentuk cluster
    'PERFORMANCE_MODE': 'auto'  # 'auto', 'performance', 'quality'
}

# Konfigurasi logging
LOG_FILE = "outlet_analysis.log"
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# Setup logging
def setup_logging():
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# Helper functions untuk Multi-Province
def get_province_filename(province_name):
    """
    Mendapatkan nama file untuk provinsi tertentu
    
    Parameters:
    province_name (str): Nama provinsi
    
    Returns:
    str: Nama file untuk provinsi
    """
    if province_name in PROVINCE_BOUNDS:
        return PROVINCE_BOUNDS[province_name]['filename']
    else:
        # Fallback untuk provinsi yang tidak ada di config
        return province_name.lower().replace(' ', '_').replace('/', '_')

def get_province_map_filename(province_name):
    """
    Mendapatkan nama file lengkap untuk map provinsi
    
    Parameters:
    province_name (str): Nama provinsi
    
    Returns:
    str: Nama file lengkap untuk map provinsi
    """
    filename = get_province_filename(province_name)
    return f"{PROVINCE_MAP_PREFIX}{filename}{PROVINCE_MAP_SUFFIX}"

def get_all_province_map_files():
    """
    Mendapatkan daftar semua file map provinsi yang akan dibuat
    
    Returns:
    dict: Dictionary dengan provinsi sebagai key dan nama file sebagai value
    """
    return {
        province: get_province_map_filename(province) 
        for province in PROVINCE_BOUNDS.keys()
    }

def get_province_config(province_name):
    """
    Mendapatkan konfigurasi untuk provinsi tertentu
    
    Parameters:
    province_name (str): Nama provinsi
    
    Returns:
    dict: Konfigurasi provinsi atau None jika tidak ditemukan
    """
    return PROVINCE_BOUNDS.get(province_name, None)

def set_clustering_mode(mode='auto'):
    """
    Mengatur mode clustering untuk performa optimal
    
    Parameters:
    mode (str): Mode clustering
        - 'auto': Otomatis berdasarkan ukuran dataset
        - 'performance': Prioritas performa (clustering agresif)
        - 'quality': Prioritas kualitas visual (clustering minimal)
        - 'disabled': Nonaktifkan clustering sepenuhnya
    """
    global CLUSTERING_SETTINGS
    
    if mode == 'performance':
        CLUSTERING_SETTINGS.update({
            'ENABLE_CLUSTERING': True,
            'AGGRESSIVE_CLUSTERING': True,
            'OUTLET_CLUSTER_RADIUS': 80,
            'FACILITY_CLUSTER_RADIUS': 60,
            'INDOMARET_CLUSTER_RADIUS': 100,
            'MAX_ZOOM_LEVEL': 12,
            'DISABLE_COVERAGE_ON_HOVER': True,
            'ENABLE_SPIDERFY': False
        })
        logger.info("Clustering mode: PERFORMANCE - Performa tinggi, clustering agresif")
        
    elif mode == 'quality':
        CLUSTERING_SETTINGS.update({
            'ENABLE_CLUSTERING': True,
            'AGGRESSIVE_CLUSTERING': False,
            'OUTLET_CLUSTER_RADIUS': 30,
            'FACILITY_CLUSTER_RADIUS': 25,
            'INDOMARET_CLUSTER_RADIUS': 40,
            'MAX_ZOOM_LEVEL': 18,
            'DISABLE_COVERAGE_ON_HOVER': False,
            'ENABLE_SPIDERFY': True
        })
        logger.info("Clustering mode: QUALITY - Kualitas visual tinggi, clustering minimal")
        
    elif mode == 'disabled':
        CLUSTERING_SETTINGS.update({
            'ENABLE_CLUSTERING': False
        })
        logger.info("Clustering mode: DISABLED - Clustering dinonaktifkan")
        
    else:  # auto
        CLUSTERING_SETTINGS.update({
            'ENABLE_CLUSTERING': True,
            'AGGRESSIVE_CLUSTERING': False,
            'OUTLET_CLUSTER_RADIUS': 50,
            'FACILITY_CLUSTER_RADIUS': 40,
            'INDOMARET_CLUSTER_RADIUS': 60,
            'MAX_ZOOM_LEVEL': 15,
            'DISABLE_COVERAGE_ON_HOVER': True,
            'ENABLE_SPIDERFY': True,
            'PERFORMANCE_MODE': 'auto'
        })
        logger.info("Clustering mode: AUTO - Otomatis berdasarkan ukuran dataset")

def get_clustering_info():
    """
    Mendapatkan informasi konfigurasi clustering saat ini
    
    Returns:
    dict: Informasi clustering
    """
    return {
        'enabled': CLUSTERING_SETTINGS.get('ENABLE_CLUSTERING', True),
        'aggressive': CLUSTERING_SETTINGS.get('AGGRESSIVE_CLUSTERING', False),
        'mode': CLUSTERING_SETTINGS.get('PERFORMANCE_MODE', 'auto'),
        'outlet_radius': CLUSTERING_SETTINGS.get('OUTLET_CLUSTER_RADIUS', 50),
        'facility_radius': CLUSTERING_SETTINGS.get('FACILITY_CLUSTER_RADIUS', 40),
        'indomaret_radius': CLUSTERING_SETTINGS.get('INDOMARET_CLUSTER_RADIUS', 60),
        'max_zoom': CLUSTERING_SETTINGS.get('MAX_ZOOM_LEVEL', 15),
        'auto_threshold': CLUSTERING_SETTINGS.get('AUTO_AGGRESSIVE_THRESHOLD', 1000),
        'disable_threshold': CLUSTERING_SETTINGS.get('DISABLE_CLUSTERING_THRESHOLD', 50)
    }