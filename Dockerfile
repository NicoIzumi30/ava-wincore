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
COPY rekapan_kecamatan.xlsx /app/
COPY indomaret_data.json /app/
COPY *.py /app/ 
COPY *.png /app/ 
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
RUN pip3 install pandas numpy matplotlib seaborn folium geopy gspread oauth2client xlsxwriter openpyxl requests tqdm

# Expose port untuk web server
EXPOSE 8081

# Script entrypoint untuk menjalankan aplikasi
COPY entrypoint.sh /app/
COPY api_cache.pkl /app/
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]