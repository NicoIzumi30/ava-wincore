#!/bin/bash

echo "Menghentikan web server..."
pkill -f "python3 web_server.py" || true

echo "Memulai web server..."
nohup python3 web_server.py > web_server.log 2>&1 &

echo "Web server direstart."
echo "Server berjalan di http://$(hostname):8080"