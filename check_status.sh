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
