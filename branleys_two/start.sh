#!/bin/bash

echo "[*] executing as: " `id` 

# ensure running as root
if [ "$(id -u)" != "0" ]; then
  exec sudo "$0" "$@" 
fi

cd /code/bringchange/avalanche
echo "[*] clearing logs"
rm /code/bringchange/avalanche/logs/*
echo "[*] clearing sessions"
rm /code/bringchange/avalanche/flask_session/*
echo "[*] starting server"
/usr/bin/python3 -m waitress --call avalanche:app

