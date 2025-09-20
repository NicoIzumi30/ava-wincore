# 📍 OUTLET MAPS - SISTEM ANALISIS OUTLET MULTI-PROVINSI

## 🎯 DESKRIPSI PROJECT

**Outlet Maps** adalah sistem analisis komprehensif untuk mengevaluasi lokasi outlet berdasarkan fasilitas sekitar dan kompetisi dengan Indomaret. Sistem ini mengintegrasikan data Google Spreadsheet dengan peta interaktif multi-provinsi dan analisis kompetisi bisnis.

## ✨ FITUR UTAMA

### 🗺️ **Multi-Province Interactive Maps**
- **Peta per Provinsi**: Maps terpisah untuk DKI Jakarta, Jawa Barat, Jawa Tengah, Sumatera Selatan, dan Sumatera Utara
- **Full Map**: Peta gabungan semua provinsi
- **Navigation Dashboard**: Interface untuk navigasi antar provinsi
- **Maps Index**: Visual navigator untuk semua maps

### 📊 **Analisis Fasilitas Sekitar (9 Kategori)**
1. **Residential** - Area perumahan
2. **Education** - Sekolah, universitas, lembaga pendidikan
3. **Public Area** - Taman, area publik
4. **Culinary** - Restoran, warung, cafe
5. **Business Center** - Perkantoran, pusat bisnis
6. **Groceries** - Toko kelontong, supermarket
7. **Convenient Stores** - Minimarket, toko serba ada
8. **Industrial** - Area industri, pabrik
9. **Hospital/Clinic** - Rumah sakit, klinik, puskesmas

### 🏪 **Integrasi Analisis Kompetisi Indomaret**
- **Deteksi Kompetitor**: Identifikasi toko Indomaret di area outlet
- **Laporan Kompetisi**: Analisis tingkat kompetisi per kecamatan
- **Statistik Kompetisi**: Persentase outlet yang menghadapi kompetisi
- **Insight Bisnis**: Rekomendasi strategis berdasarkan kompetisi

### 📈 **Rating & Scoring System**
- **Rating Otomatis**: ⭐⭐⭐⭐⭐ (Excellent) hingga ⭐ (Poor)
- **Scoring Berdasarkan Fasilitas**: Semakin banyak fasilitas = rating lebih tinggi
- **Visual Indicators**: Color-coded markers untuk rating yang berbeda

### 📋 **Export & Reporting**
- **Excel Export**: File .xlsx dengan checkmarks visual dan summary sheet
- **JSON Export**: Data terstruktur untuk integrasi lebih lanjut
- **Web Dashboard**: Interface web untuk akses mudah
- **Laporan Indomaret**: JSON report khusus analisis kompetisi

### 🔄 **Automated Updates**
- **Cron Jobs**: Update otomatis setiap hari pada jam 00:00 WIB
- **Resume Capability**: Melanjutkan analisis yang terputus
- **Progress Tracking**: Monitoring progress real-time
- **Error Recovery**: Retry mechanism untuk API failures

## 📁 INPUT & FILE YANG DIBUTUHKAN

### 🔑 **File Wajib**
1. **`credentials.json`** - Google Sheets API credentials
   - Format: Service Account JSON dari Google Cloud Console
   - Diperlukan untuk akses Google Spreadsheet

2. **Google Spreadsheet** - Data outlet utama
   - **Spreadsheet ID**: `1KfOygJL5i9-Lm5myMA4LvA9frVrNkgvems17N6cqqUQ`
   - **Sheet Name**: `Wincore Input`
   - **Kolom yang dibutuhkan**:
     - Kolom 8 (index 7): Nama Outlet
     - Kolom 12 (index 11): Kecamatan
     - Kolom 14 (index 13): Koordinat (format: "lat, long")

### 📊 **File Opsional**
3. **`indomaret_data.json`** - Data kompetitor Indomaret
   ```json
   [
     {
       "Store": "Indomaret Sudirman",
       "Latitude": -6.208763,
       "Longitude": 106.845599,
       "Kecamatan": "TANAH ABANG"
     }
   ]
   ```

### ⚙️ **File Konfigurasi**
4. **`config.py`** - Konfigurasi sistem (sudah ada)
5. **`api_cache.pkl`** - Cache API untuk optimasi (auto-generated)

## 🚀 OUTPUT YANG DIHASILKAN

### 🗺️ **Interactive Maps**
- **`peta_outlet_full.html`** - Map semua provinsi
- **`peta_outlet_dki_jakarta.html`** - Map DKI Jakarta
- **`peta_outlet_jawa_barat.html`** - Map Jawa Barat  
- **`peta_outlet_jawa_tengah.html`** - Map Jawa Tengah
- **`peta_outlet_sumatera_selatan.html`** - Map Sumatera Selatan
- **`peta_outlet_sumatera_utara.html`** - Map Sumatera Utara
- **`index.html`** - Dashboard utama dengan navigasi
- **`maps_index.html`** - Visual navigator maps

### 📊 **Data & Reports**
- **`analisis_outlet.xlsx`** - Excel dengan checkmarks dan summary
- **`hasil_analisis_outlet.json`** - Raw data JSON
- **`indomaret_competition_report.json`** - Laporan kompetisi
- **`hasil_analisis_kecamatan.xlsx`** - Analisis per kecamatan
- **`hasil_analisis_kecamatan.json`** - Data kecamatan JSON

### 📝 **Log Files**
- **`outlet_analysis.log`** - Log analisis utama
- **`kecamatan_analysis.log`** - Log analisis kecamatan
- **`web_server.log`** - Log web server
- **`cron.log`** - Log automated updates

## 🛠️ CARA MENJALANKAN

### 💻 **Local Development**
```bash
# 1. Install dependencies
pip install pandas numpy matplotlib seaborn folium geopy gspread oauth2client xlsxwriter openpyxl requests tqdm

# 2. Setup Google Sheets API
# - Buat project di Google Cloud Console
# - Enable Google Sheets API
# - Buat Service Account
# - Download credentials.json

# 3. Run main program
python main.py

# 4. Start web server
python web_server.py

# 5. Access dashboard
# http://localhost:8080
```

### 🐳 **Docker Deployment**
```bash
# 1. Build image
docker build -t outlet-analisis .

# 2. Run container
docker run -d -p 8080:8080 --name outlet-analisis outlet-analisis

# 3. Access dashboard
# http://localhost:8080
```

### ⚡ **Quick Commands**
```bash
# Analisis kecamatan terpisah
python kecamatan_analysis.py

# Update otomatis
python auto_update.py

# Check status
./check_status.sh

# Restart services
./restart.sh
```

## 🏗️ ARSITEKTUR SISTEM

### 📦 **Core Modules**
- **`main.py`** - Entry point utama
- **`map_generator.py`** - Generator peta interaktif
- **`facility_analyzer.py`** - Analisis fasilitas sekitar
- **`data_loader.py`** - Loader data Google Sheets
- **`indomaret_handler.py`** - Handler kompetisi Indomaret
- **`excel_generator.py`** - Generator Excel reports
- **`web_server.py`** - Web server untuk dashboard

### 🔧 **Utility Modules**
- **`config.py`** - Konfigurasi sistem
- **`utils.py`** - Utility functions
- **`multi_province_utils.py`** - Utils multi-provinsi
- **`api_handler.py`** - Handler API eksternal
- **`auto_update.py`** - Automated updates

### 🌐 **External APIs**
- **Google Sheets API** - Data outlet
- **Overpass API** - Data OpenStreetMap fasilitas
- **Multiple Endpoints** - Redundancy untuk reliability

## 🎨 UI/UX FEATURES

### 🖱️ **Interactive Elements**
- **Dropdown Navigation** - Pilih provinsi dengan mudah
- **Popup Information** - Detail outlet dengan modern design
- **Color-coded Markers** - Visual rating system
- **Zoom Controls** - Optimal zoom per provinsi
- **Google Maps Integration** - Link langsung ke Google Maps

### 📱 **Responsive Design**
- **Mobile-friendly** - Optimized untuk semua device
- **Modern UI** - Clean, professional interface
- **Fast Loading** - Optimized performance
- **Cross-browser** - Compatible dengan semua browser

## 🔐 KEAMANAN & RELIABILITY

### 🛡️ **Security Features**
- **API Key Protection** - Credentials disimpan aman
- **Input Validation** - Validasi semua input data
- **Error Handling** - Graceful error recovery
- **Log Monitoring** - Comprehensive logging

### 🔄 **Reliability Features**
- **Auto Retry** - Retry mechanism untuk API calls
- **Progress Tracking** - Resume interrupted processes
- **Cache System** - Reduce API calls
- **Backup System** - Data backup otomatis

## 📈 PERFORMANCE OPTIMIZATION

### ⚡ **Speed Optimizations**
- **Multi-threading** - Parallel processing outlets
- **API Caching** - Reduce redundant API calls
- **Batch Processing** - Process multiple outlets together
- **Optimized Queries** - Efficient OpenStreetMap queries

### 💾 **Memory Management**
- **Progressive Loading** - Load data as needed
- **Memory Cleanup** - Automatic cleanup old files
- **Efficient Data Structures** - Optimized data handling

## 🌟 KEUNGGULAN SISTEM

1. **🎯 Comprehensive Analysis** - 9 kategori fasilitas + kompetisi
2. **🗺️ Multi-Province Support** - Fokus per provinsi dengan detail tinggi
3. **🏪 Business Intelligence** - Analisis kompetisi Indomaret
4. **📊 Rich Reporting** - Excel, JSON, Web dashboard
5. **🔄 Automated Operations** - Cron jobs, auto-update
6. **🌐 Web Interface** - Easy access via browser
7. **🐳 Docker Ready** - Easy deployment
8. **📱 Mobile Friendly** - Responsive design
9. **🛡️ Enterprise Grade** - Logging, monitoring, security
10. **⚡ High Performance** - Optimized for large datasets

---

## 📞 SUPPORT & MAINTENANCE

Sistem ini dirancang untuk **production-ready** dengan fitur monitoring, logging, dan automated updates. Cocok untuk analisis bisnis skala enterprise dengan kebutuhan real-time data dan reporting yang komprehensif.

