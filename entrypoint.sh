#!/bin/bash

# Set timezone ke Asia/Jakarta (WIB)
echo "Asia/Jakarta" > /etc/timezone
ln -sf /usr/share/zoneinfo/Asia/Jakarta /etc/localtime
dpkg-reconfigure -f noninteractive tzdata

# Jalankan web server di background
python3 web_server.py > web_server.log 2>&1 &

# Tampilkan informasi untuk pengguna
echo "Web server telah dimulai. Dapat diakses di http://localhost:8081"
echo "Timezone diatur ke WIB (GMT+7)"
echo "Untuk memeriksa status, jalankan ./check_status.sh di dalam container"

# Setup cron di Docker untuk berjalan pukul 00:00 WIB
# Catatan: cron di Docker perlu dikonfigurasi secara khusus
service cron start
(crontab -l 2>/dev/null; echo "0 0 * * * cd /app && python3 auto_update.py >> cron.log 2>&1") | crontab -

# Buat agar container tetap berjalan dan tidak exit
tail -f /dev/null