# Dokumentasi Outlet Analisis Docker

Dokumentasi ini menjelaskan langkah-langkah untuk menjalankan sistem analisis outlet menggunakan Docker.

## Prasyarat

- [Docker](https://docs.docker.com/get-docker/) terinstal di sistem Anda
- File-file berikut harus berada dalam satu folder:
  - `setup_vps.sh` (script setup utama)
  - `auto_update.py` (script untuk pembaruan data)
  - `web_server.py` (script untuk web server)
  - `data_loader.py` (jika ada, untuk koneksi ke data source)
  - File Python lain yang dibutuhkan
  - `credentials.json` (jika menggunakan Google Sheets)
  - `Dockerfile` (dari dokumentasi ini)
  - `entrypoint.sh` (dari dokumentasi ini)

## Membangun dan Menjalankan Container

### 1. Membuat File Docker

Simpan kedua file berikut di direktori yang sama dengan script aplikasi Anda:

#### A. Dockerfile
```dockerfile
FROM ubuntu:22.04

# Hindari interaksi pengguna selama instalasi
ENV DEBIAN_FRONTEND=noninteractive

# Instal dependensi yang diperlukan
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    sudo \
    cron \
    curl \
    nano \
    procps \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Buat direktori kerja
WORKDIR /app

# Salin script setup dan file pendukung ke container
COPY setup_vps.sh /app/
COPY *.py /app/ 
# Asumsikan file Python tersedia di direktori yang sama dengan Dockerfile

# Jika ada credentials.json, salin juga
COPY credentials.json* /app/

# Buat direktori output
RUN mkdir -p /app/output

# Ubah permission untuk script
RUN chmod +x /app/setup_vps.sh

# Modifikasi setup_vps.sh untuk Docker (menghapus sudo)
RUN sed -i 's/sudo //g' /app/setup_vps.sh

# Instal dependensi Python
RUN pip3 install pandas requests tqdm folium geopy openpyxl gspread oauth2client

# Expose port untuk web server
EXPOSE 8080

# Script entrypoint untuk menjalankan aplikasi
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
```

#### B. entrypoint.sh
```bash
#!/bin/bash

# Set timezone ke Asia/Jakarta (WIB)
echo "Asia/Jakarta" > /etc/timezone
ln -sf /usr/share/zoneinfo/Asia/Jakarta /etc/localtime
dpkg-reconfigure -f noninteractive tzdata

# Jalankan web server di background
python3 web_server.py > web_server.log 2>&1 &

# Tampilkan informasi untuk pengguna
echo "Web server telah dimulai. Dapat diakses di http://localhost:8080"
echo "Timezone diatur ke WIB (GMT+7)"
echo "Untuk memeriksa status, jalankan ./check_status.sh di dalam container"

# Setup cron di Docker untuk berjalan pukul 00:00 WIB
# Catatan: cron di Docker perlu dikonfigurasi secara khusus
service cron start
(crontab -l 2>/dev/null; echo "0 0 * * * cd /app && python3 auto_update.py >> cron.log 2>&1") | crontab -

# Buat agar container tetap berjalan dan tidak exit
tail -f /dev/null
```

### 2. Build Docker Image

```bash
docker build -t ava-wincore .
```

### 3. Jalankan Container

Pilih salah satu opsi berikut:

#### Opsi A: Dengan port yang ditentukan (8082 di contoh ini)
```bash
docker run -d -p 8080:8080 --name ava-wincore ava-wincore
```
Web server akan dapat diakses di http://localhost:8082

#### Opsi B: Dengan port yang ditentukan Docker secara otomatis
```bash
docker run -d -P --name ava-wincore ava-wincore
```

Untuk mengetahui port yang digunakan:
```bash
docker port ava-wincore
```

## Manajemen Container

### Melihat Status Container
```bash
docker ps -a | grep ava-wincore
```

### Menghentikan Container
```bash
docker stop ava-wincore
```

### Menjalankan Kembali Container yang Terhenti
```bash
docker start ava-wincore
```

### Menghapus Container
```bash
docker stop ava-wincore
docker rm ava-wincore
```

## Mengakses dan Mengelola Aplikasi Dalam Container

### 1. Masuk ke Container
```bash
docker exec -it ava-wincore /bin/bash
```

### 2. Memeriksa Status Aplikasi
Setelah masuk ke container:
```bash
./check_status.sh
```

### 3. Menjalankan Auto Update Manual

#### Cara A: Dari luar container
```bash
docker exec -it ava-wincore python3 /app/auto_update.py
```

#### Cara B: Dari dalam container
Setelah masuk ke container:
```bash
cd /app
python3 auto_update.py
```

#### Cara C: Menggunakan check_status.sh
Setelah masuk ke container, jalankan `./check_status.sh` dan pilih "y" saat ditanya untuk memperbarui.

### 4. Melihat Log

#### Web Server Log
```bash
docker exec -it ava-wincore cat /app/web_server.log
```

#### Cron Update Log
```bash
docker exec -it ava-wincore cat /app/cron.log
```

### 5. Memeriksa Timezone

Untuk memastikan timezone sudah diatur dengan benar:
```bash
docker exec -it ava-wincore date
```

Output seharusnya menunjukkan waktu WIB (GMT+7).

## Persistent Data (Opsional)

Jika Anda ingin menyimpan data secara permanen di host, gunakan volume:

```bash
docker run -d -p 8082:8080 -v /path/di/host:/app/output --name ava-wincore ava-wincore
```

Ganti `/path/di/host` dengan direktori di sistem Anda.

## Troubleshooting

### Jika Port Sudah Digunakan

Jika Anda mendapat error "address already in use", gunakan port yang berbeda:
```bash
docker run -d -p 8083:8080 --name outlet-analisis outlet-analisis
```

### Jika Container Sudah Ada

Jika container dengan nama yang sama sudah ada:
1. Hentikan dan hapus container lama:
   ```bash
   docker stop outlet-analisis
   docker rm outlet-analisis
   ```
2. Jalankan container baru dengan perintah di atas.

### Jika Web Server Tidak Berjalan

Masuk ke container dan restart web server:
```bash
docker exec -it outlet-analisis /bin/bash
pkill -f "python3 web_server.py"
python3 web_server.py > web_server.log 2>&1 &
```

### Jika Cronjob Tidak Berjalan pada Waktu yang Benar

Pastikan timezone dikonfigurasi dengan benar:
```bash
docker exec -it outlet-analisis /bin/bash
date
```

Jika timezone tidak benar, Anda mungkin perlu me-rebuild container atau mengatur timezone secara manual:
```bash
docker exec -it outlet-analisis /bin/bash
echo "Asia/Jakarta" > /etc/timezone
ln -sf /usr/share/zoneinfo/Asia/Jakarta /etc/localtime
dpkg-reconfigure -f noninteractive tzdata
service cron restart
```

## Catatan Penting

1. Web server berjalan di port 8080 di dalam container
2. Container menggunakan timezone Asia/Jakarta (WIB/GMT+7)
3. Cron job diatur untuk menjalankan auto_update.py setiap jam 12 malam waktu Indonesia
4. File output disimpan di direktori `/app/output` di dalam container
