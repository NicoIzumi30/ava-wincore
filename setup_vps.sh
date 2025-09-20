#!/bin/bash

# Update sistem
sudo apt update && sudo apt upgrade -y

# Install Python dan dependensi
sudo apt install -y python3 python3-pip

# Instal dependensi Python
pip3 install pandas requests tqdm folium geopy openpyxl gspread oauth2client

# Buat folder output jika belum ada
mkdir -p output

# Setup cron job untuk menjalankan analisis setiap jam 12 malam
(crontab -l 2>/dev/null; echo "0 0 * * * cd $(pwd) && python3 auto_update.py >> cron.log 2>&1") | crontab -

# Setup cron job untuk menjalankan web server saat reboot
(crontab -l 2>/dev/null; echo "@reboot cd $(pwd) && python3 web_server.py >> web_server.log 2>&1") | crontab -

# Tes jika kredensial sudah ada
if [ -f "credentials.json" ]; then
    echo "Kredensial ditemukan. Menjalankan tes koneksi ke Google Sheets..."
    python3 -c "from data_loader import connect_to_spreadsheet; print('Koneksi berhasil' if connect_to_spreadsheet() else 'Koneksi gagal')"
else
    echo "WARNING: File credentials.json tidak ditemukan!"
    echo "Harap upload file credentials.json sebelum menjalankan script."
fi

# Buat script untuk memeriksa status
cat > check_status.sh << 'EOF'
#!/bin/bash

echo "=== Status Sistem Analisis Outlet ==="
echo "Log terakhir:"
tail -n 20 cron.log

echo -e "\nFile output terbaru:"
ls -la output/ | grep latest

echo -e "\nPembaruan terakhir:"
find output/ -type f -name "*.html" -o -name "*.xlsx" | sort | tail -n 5

echo -e "\nStatus web server:"
ps aux | grep web_server.py | grep -v grep

echo -e "\nMemperbarui sekarang? (y/n)"
read choice
if [ "$choice" = "y" ] || [ "$choice" = "Y" ]; then
    echo "Menjalankan pembaruan..."
    python3 auto_update.py
    echo "Pembaruan selesai."
fi

echo -e "\nRestart web server? (y/n)"
read choice
if [ "$choice" = "y" ] || [ "$choice" = "Y" ]; then
    echo "Merestart web server..."
    pkill -f "python3 web_server.py"
    nohup python3 web_server.py > web_server.log 2>&1 &
    echo "Web server direstart."
fi
EOF

chmod +x check_status.sh

# Jalankan web server
echo "Memulai web server..."
nohup python3 web_server.py > web_server.log 2>&1 &

echo "Setup selesai! Sistem akan menjalankan update otomatis setiap jam 12 malam."
echo "Peta dapat diakses di http://$(hostname):8080"
echo "Untuk memeriksa status, jalankan ./check_status.sh"