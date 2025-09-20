#!/usr/bin/env python3
import http.server
import socketserver
import os
import mimetypes
import urllib.parse
from datetime import datetime
import logging
import socket
import time
import sys
import json

# Konfigurasi port
PORT = 8080
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# Setup logging
logging.basicConfig(
    filename="web_server.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("web_server")

# Map MIME types untuk file yang akan diunduh
DOWNLOAD_MIME_TYPES = {
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".json": "application/json"
}

# Province file mappings
PROVINCE_MAPS = {
    'jakarta': 'peta_outlet_dki_jakarta.html',
    'dki-jakarta': 'peta_outlet_dki_jakarta.html',
    'dki_jakarta': 'peta_outlet_dki_jakarta.html',
    'jabar': 'peta_outlet_jawa_barat.html',
    'jawa-barat': 'peta_outlet_jawa_barat.html',
    'jawa_barat': 'peta_outlet_jawa_barat.html',
    'jateng': 'peta_outlet_jawa_tengah.html',
    'jawa-tengah': 'peta_outlet_jawa_tengah.html',
    'jawa_tengah': 'peta_outlet_jawa_tengah.html',
    'sumsel': 'peta_outlet_sumatera_selatan.html',
    'sumatera-selatan': 'peta_outlet_sumatera_selatan.html',
    'sumatera_selatan': 'peta_outlet_sumatera_selatan.html',
    'sumut': 'peta_outlet_sumatera_utara.html',
    'sumatera-utara': 'peta_outlet_sumatera_utara.html',
    'sumatera_utara': 'peta_outlet_sumatera_utara.html',
    'full': 'peta_outlet_full.html',
    'semua': 'peta_outlet_full.html',
    'all': 'peta_outlet_full.html'
}

def is_port_in_use(port):
    """Memeriksa apakah port sudah digunakan."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def get_available_maps():
    """
    Mendapatkan daftar maps yang tersedia di output directory
    
    Returns:
    dict: Dictionary dengan info maps yang tersedia
    """
    available_maps = {
        'full': None,
        'provinces': {},
        'total': 0
    }
    
    try:
        if not os.path.exists(OUTPUT_DIR):
            return available_maps
        
        # Cek full map
        full_map_path = os.path.join(OUTPUT_DIR, 'peta_outlet_full.html')
        if os.path.exists(full_map_path):
            available_maps['full'] = 'peta_outlet_full.html'
            available_maps['total'] += 1
        
        # Cek province maps
        province_patterns = [
            ('DKI Jakarta', 'peta_outlet_dki_jakarta.html'),
            ('Jawa Barat', 'peta_outlet_jawa_barat.html'),
            ('Jawa Tengah', 'peta_outlet_jawa_tengah.html'),
            ('Sumatera Selatan', 'peta_outlet_sumatera_selatan.html'),
            ('Sumatera Utara', 'peta_outlet_sumatera_utara.html')
        ]
        
        for province_name, filename in province_patterns:
            province_path = os.path.join(OUTPUT_DIR, filename)
            if os.path.exists(province_path):
                available_maps['provinces'][province_name] = filename
                available_maps['total'] += 1
        
        # Load metadata jika ada
        metadata_path = os.path.join(OUTPUT_DIR, 'province_maps_metadata.json')
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                available_maps['metadata'] = metadata
            except Exception as e:
                logger.warning(f"Failed to load metadata: {e}")
        
        logger.info(f"Available maps: {available_maps['total']} total, full: {bool(available_maps['full'])}, provinces: {len(available_maps['provinces'])}")
        
    except Exception as e:
        logger.error(f"Error getting available maps: {e}")
    
    return available_maps

class OutletAnalysisHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=OUTPUT_DIR, **kwargs)
    
    def do_GET(self):
        """Menangani permintaan GET dengan dukungan multi-province routing."""
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            clean_path = parsed_path.path.lower().strip('/')
            
            # Handle route khusus untuk dashboard
            if clean_path in ["dashboard", "dashboard/"]:
                dashboard_file = os.path.join(OUTPUT_DIR, "dashboard_analisis_kecamatan.html")
                if os.path.exists(dashboard_file):
                    self.serve_file(dashboard_file, "text/html")
                    return
                else:
                    self.send_error(404, "Dashboard file not found")
                    return
            
            # Handle route untuk maps index
            if clean_path in ["maps", "maps/", "maps-index", "navigator"]:
                maps_index_file = os.path.join(OUTPUT_DIR, "maps_index.html")
                if os.path.exists(maps_index_file):
                    self.serve_file(maps_index_file, "text/html")
                    return
                else:
                    self.send_error(404, "Maps index file not found")
                    return
            
            # Handle route untuk province maps dengan berbagai format URL
            if clean_path.startswith('map/') or clean_path.startswith('province/'):
                province_key = clean_path.split('/')[-1]
                if province_key in PROVINCE_MAPS:
                    target_file = PROVINCE_MAPS[province_key]
                    file_path = os.path.join(OUTPUT_DIR, target_file)
                    if os.path.exists(file_path):
                        self.serve_file(file_path, "text/html")
                        return
                    else:
                        self.send_error(404, f"Province map not found: {target_file}")
                        return
            
            # Handle route untuk logo
            if clean_path == "logo.png":
                logo_locations = [
                    os.path.join(os.path.dirname(OUTPUT_DIR), "logo.png"),
                    os.path.join(OUTPUT_DIR, "logo.png")
                ]
                
                for logo_file in logo_locations:
                    if os.path.exists(logo_file):
                        self.serve_file(logo_file, "image/png")
                        return
                
                self.send_error(404, "Logo file not found")
                return
            
            # Handle API endpoints
            if clean_path.startswith('api/'):
                self.handle_api_request(clean_path)
                return
            
            # Default ke index.html jika path kosong atau root
            if clean_path == "" or clean_path == "/":
                self.path = "/index.html"
            
            # Cek apakah file ada
            file_path = os.path.join(OUTPUT_DIR, parsed_path.path.lstrip("/"))
            if not os.path.exists(file_path) or os.path.isdir(file_path):
                # Jika file tidak ditemukan, coba alternatif
                if not self.try_alternative_files(parsed_path.path):
                    # Fallback ke index.html jika tidak ada alternatif
                    index_file = os.path.join(OUTPUT_DIR, "index.html")
                    if os.path.exists(index_file):
                        self.path = "/index.html"
                    else:
                        # Generate emergency index jika tidak ada
                        self.serve_emergency_index()
                        return
            
            # Set header untuk mengunduh file Excel dan JSON
            file_ext = os.path.splitext(self.path)[1].lower()
            if file_ext in DOWNLOAD_MIME_TYPES:
                file_path = os.path.join(OUTPUT_DIR, self.path.lstrip("/"))
                if os.path.exists(file_path):
                    try:
                        mime_type = DOWNLOAD_MIME_TYPES[file_ext]
                        self.send_response(200)
                        self.send_header("Content-Type", mime_type)
                        self.send_header("Content-Disposition", f"attachment; filename={os.path.basename(self.path)}")
                        file_stats = os.stat(file_path)
                        self.send_header("Content-Length", str(file_stats.st_size))
                        self.end_headers()
                        with open(file_path, 'rb') as file:
                            self.wfile.write(file.read())
                        return
                    except Exception as e:
                        logger.error(f"Error saat mengirim file: {e}")
                        self.send_error(500, f"Error saat mengirim file: {str(e)}")
                        return
            
            # Untuk file lain, gunakan handler default
            return super().do_GET()
            
        except Exception as e:
            logger.error(f"Error saat menangani permintaan: {e}")
            self.send_error(500, f"Internal server error: {str(e)}")
    
    def try_alternative_files(self, requested_path):
        """
        Mencoba file alternatif jika file yang diminta tidak ditemukan
        
        Parameters:
        requested_path (str): Path yang diminta
        
        Returns:
        bool: True jika berhasil menemukan alternatif
        """
        try:
            # Coba file latest jika diminta file tanpa timestamp
            if "outlet" in requested_path.lower() and ".html" in requested_path.lower():
                if "latest" not in requested_path:
                    # Coba tambahkan latest
                    base_name = os.path.splitext(os.path.basename(requested_path))[0]
                    latest_file = f"{base_name}_latest.html"
                    latest_path = os.path.join(OUTPUT_DIR, latest_file)
                    
                    if os.path.exists(latest_path):
                        self.path = f"/{latest_file}"
                        return True
            
            # Coba file maps yang ada jika diminta file map
            if "peta" in requested_path.lower() or "map" in requested_path.lower():
                available_maps = get_available_maps()
                
                # Jika diminta full map tapi tidak ada, coba province map pertama
                if "full" in requested_path.lower() and not available_maps['full']:
                    if available_maps['provinces']:
                        first_province_file = list(available_maps['provinces'].values())[0]
                        self.path = f"/{first_province_file}"
                        return True
                
                # Jika diminta province map tapi tidak ada, coba full map
                if available_maps['full'] and not any(filename in requested_path for filename in available_maps['provinces'].values()):
                    self.path = f"/{available_maps['full']}"
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error trying alternatives: {e}")
            return False
    
    def handle_api_request(self, api_path):
        """
        Menangani API requests untuk informasi maps
        
        Parameters:
        api_path (str): Path API yang diminta
        """
        try:
            if api_path == 'api/maps':
                # Return available maps info
                available_maps = get_available_maps()
                response_data = {
                    'status': 'success',
                    'data': available_maps,
                    'timestamp': datetime.now().isoformat()
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response_data, indent=2).encode())
                return
                
            elif api_path == 'api/status':
                # Return server status
                available_maps = get_available_maps()
                status_data = {
                    'status': 'online',
                    'server_time': datetime.now().isoformat(),
                    'maps_available': available_maps['total'],
                    'output_dir': OUTPUT_DIR,
                    'version': 'multi-province-v1.0'
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(status_data, indent=2).encode())
                return
            
            else:
                self.send_error(404, f"API endpoint not found: {api_path}")
                
        except Exception as e:
            logger.error(f"Error handling API request: {e}")
            self.send_error(500, f"API error: {str(e)}")
    
    def serve_file(self, file_path, content_type):
        """Melayani file dengan content type yang ditentukan."""
        try:
            with open(file_path, 'rb') as file:
                file_content = file.read()
                
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(file_content)))
            self.end_headers()
            self.wfile.write(file_content)
        except Exception as e:
            logger.error(f"Error saat melayani file {file_path}: {e}")
            self.send_error(500, f"Error saat melayani file: {str(e)}")
    
    def serve_emergency_index(self):
        """
        Melayani emergency index page jika tidak ada file index
        """
        available_maps = get_available_maps()
        
        # Generate links untuk maps yang tersedia
        map_links = []
        if available_maps['full']:
            map_links.append(f'<a href="{available_maps["full"]}" class="map-link full-map">🌏 Lihat Semua Provinsi</a>')
        
        for province, filename in available_maps['provinces'].items():
            emoji_map = {
                'DKI Jakarta': '🏙️',
                'Jawa Barat': '🏔️',
                'Jawa Tengah': '🏛️',
                'Sumatera Selatan': '🌴',
                'Sumatera Utara': '🌿'
            }
            emoji = emoji_map.get(province, '📍')
            map_links.append(f'<a href="{filename}" class="map-link province-map">{emoji} {province}</a>')
        
        emergency_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Analisis Outlet - Multi Province Maps</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }}
        
        .container {{
            background: white;
            border-radius: 15px;
            padding: 40px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            max-width: 600px;
            text-align: center;
        }}
        
        .header {{
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            color: #2c3e50;
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}
        
        .header p {{
            color: #7f8c8d;
            font-size: 1.1rem;
        }}
        
        .status-box {{
            background: #f8f9fa;
            border-left: 4px solid #28a745;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        
        .maps-available {{
            margin: 30px 0;
        }}
        
        .maps-available h3 {{
            color: #2c3e50;
            margin-bottom: 20px;
        }}
        
        .map-links {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        
        .map-link {{
            display: inline-block;
            padding: 12px 20px;
            background: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            transition: all 0.3s;
            font-weight: 500;
        }}
        
        .map-link:hover {{
            background: #2980b9;
            transform: translateY(-2px);
        }}
        
        .map-link.full-map {{
            background: #27ae60;
            font-size: 1.1rem;
        }}
        
        .map-link.full-map:hover {{
            background: #229954;
        }}
        
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
            color: #7f8c8d;
            font-size: 0.9rem;
        }}
        
        .api-info {{
            background: #e8f5e8;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            font-size: 0.9rem;
            color: #2d5a2d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><i class="fas fa-map-marked-alt"></i> Multi-Province Maps</h1>
            <p>Sistem Analisis Outlet Berbasis Geolokasi</p>
        </div>
        
        <div class="status-box">
            <h3><i class="fas fa-check-circle" style="color: #28a745;"></i> Server Online</h3>
            <p>Web server berjalan dengan baik. Total {available_maps['total']} maps tersedia.</p>
            <p><strong>Waktu server:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S WIB')}</p>
        </div>
        
        {'<div class="maps-available"><h3>🗺️ Maps Tersedia:</h3><div class="map-links">' + ''.join(map_links) + '</div></div>' if map_links else '<div class="status-box" style="border-left-color: #f39c12;"><p><i class="fas fa-exclamation-triangle" style="color: #f39c12;"></i> Belum ada maps yang tersedia. Jalankan analisis terlebih dahulu.</p></div>'}
        
        <div class="api-info">
            <h4><i class="fas fa-code"></i> API Endpoints:</h4>
            <p><code>GET /api/maps</code> - Info maps tersedia</p>
            <p><code>GET /api/status</code> - Status server</p>
        </div>
        
        <div class="footer">
            <p>&copy; {datetime.now().year} Sistem Analisis Outlet Multi-Province</p>
            <p>Emergency index page - Generated automatically</p>
        </div>
    </div>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(emergency_html.encode())))
        self.end_headers()
        self.wfile.write(emergency_html.encode())
    
    def log_message(self, format, *args):
        """Log pesan akses."""
        logger.info("%s - %s", self.address_string(), format % args)

def get_ip_address():
    """Mendapatkan alamat IP server."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Tidak benar-benar menghubungkan
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Server HTTP dengan Threading untuk menangani request secara paralel."""
    allow_reuse_address = True
    daemon_threads = True

def setup_environment():
    """Menyiapkan lingkungan yang diperlukan."""
    try:
        # Pastikan direktori output ada
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        logger.info(f"Direktori output dibuat/diperiksa: {OUTPUT_DIR}")
        
        # Cek maps yang tersedia
        available_maps = get_available_maps()
        logger.info(f"Maps tersedia: {available_maps['total']}")
        
        return True
    except Exception as e:
        logger.error(f"Error saat menyiapkan lingkungan: {e}")
        print(f"Error saat menyiapkan lingkungan: {e}")
        return False

def find_available_port(start_port, max_attempts=10):
    """Mencari port yang tersedia."""
    current_port = start_port
    attempts = 0
    
    while attempts < max_attempts:
        if not is_port_in_use(current_port):
            return current_port
        current_port += 1
        attempts += 1
    
    return None

def run_server(port):
    """Menjalankan server HTTP dengan dukungan multi-province."""
    try:
        server_address = ('', port)
        with ThreadedHTTPServer(server_address, OutletAnalysisHandler) as httpd:
            ip_address = get_ip_address()
            
            # Log startup info
            logger.info(f"Multi-Province Web Server started on http://{ip_address}:{port}")
            print("=" * 80)
            print("🌐 MULTI-PROVINCE WEB SERVER")
            print("=" * 80)
            print(f"🚀 Server berjalan di: http://{ip_address}:{port}")
            print(f"📁 Output directory: {OUTPUT_DIR}")
            
            # Check dan tampilkan maps yang tersedia
            available_maps = get_available_maps()
            print(f"🗺️  Maps tersedia: {available_maps['total']}")
            
            if available_maps['full']:
                print(f"   🌏 Full map: http://{ip_address}:{port}/{available_maps['full']}")
            
            if available_maps['provinces']:
                print("   📍 Province maps:")
                for province, filename in available_maps['provinces'].items():
                    print(f"      • {province}: http://{ip_address}:{port}/{filename}")
            
            print("\n🔗 Akses Utama:")
            print(f"   • Dashboard: http://{ip_address}:{port}/")
            print(f"   • Maps Navigator: http://{ip_address}:{port}/maps")
            print(f"   • API Info: http://{ip_address}:{port}/api/maps")
            
            print("\n📱 URL Shortcuts:")
            print(f"   • Jakarta: http://{ip_address}:{port}/map/jakarta")
            print(f"   • Jawa Barat: http://{ip_address}:{port}/map/jabar")
            print(f"   • Jawa Tengah: http://{ip_address}:{port}/map/jateng")
            print(f"   • Sumatra Selatan: http://{ip_address}:{port}/map/sumsel")
            print(f"   • Sumatra Utara: http://{ip_address}:{port}/map/sumut")
            print(f"   • Semua Provinsi: http://{ip_address}:{port}/map/full")
            
            print("\n⏹️  Tekan Ctrl+C untuk menghentikan server")
            print("=" * 80)
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        logger.info("Server dihentikan oleh user.")
        print("\n\n⚠️ Server dihentikan.")
        return True
    except Exception as e:
        logger.error(f"Server error: {e}")
        print(f"\n❌ Server error: {e}")
        return False

if __name__ == "__main__":
    # Siapkan lingkungan
    if not setup_environment():
        sys.exit(1)
    
    # Cari port yang tersedia
    available_port = find_available_port(PORT)
    if not available_port:
        logger.error(f"Tidak dapat menemukan port yang tersedia setelah mencoba {PORT} hingga {PORT+9}")
        print(f"❌ Tidak dapat menemukan port yang tersedia setelah mencoba {PORT} hingga {PORT+9}")
        sys.exit(1)
    else:
        if available_port != PORT:
            logger.warning(f"Port {PORT} sudah digunakan, menggunakan port {available_port}")
            print(f"⚠️ Port {PORT} sudah digunakan, menggunakan port {available_port}")
        PORT = available_port
    
    # Loop untuk restart otomatis jika server mati
    max_restarts = 5
    restart_count = 0
    
    while restart_count < max_restarts:
        server_stopped_normally = run_server(PORT)
        
        if server_stopped_normally:
            break  # Server berhenti dengan normal (misalnya karena KeyboardInterrupt)
        
        restart_count += 1
        logger.warning(f"Server mati, mencoba restart ({restart_count}/{max_restarts})")
        print(f"🔄 Server mati, mencoba restart ({restart_count}/{max_restarts})")
        time.sleep(5)  # Tunggu 5 detik sebelum restart
    
    if restart_count >= max_restarts:
        logger.error("Terlalu banyak percobaan restart, server dihentikan")
        print("❌ Terlalu banyak percobaan restart, server dihentikan")
        sys.exit(1)