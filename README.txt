GESTIONAR zurullo.com (SERVER-ZULO):

|app.py (archivo de zulo server):|

# Ver si está corriendo
sudo systemctl status zulo

# Parar la app
sudo systemctl stop zulo

# Arrancar la app
sudo systemctl start zulo

# Reiniciar la app (útil tras cambios en el código)
sudo systemctl restart zulo

-------------------------------------------------------
|cloudflared (lo que conecta a nuestro dominio, a Internet):|

# Parar el túnel
sudo systemctl stop cloudflared

# Arrancar el túnel
sudo systemctl start cloudflared

# Reiniciar túnel
sudo systemctl restart cloudflared

-------------------------------------------------------
|Creación y mantenimiento de tablas/bases de datos:|

# Creación tablas
cd /home/pedro/Desktop/proyectos/zulo
python3 -c "from app import app, db; app.app_context().__enter__(); db.create_all()"
sudo systemctl restart zulo

-------------------------------------------------------
|Descarga de archivos de audio desde spotify:|

# Descargar cookies en youtube music o youtube con "Get cookies.txt LOCALLY"
# Crear una carpeta donde descargar las canciones, poner ahí el archivo de las cookies (se pone límite para evitar bloqueo de IP por active-bot)

python -m spotdl https://open.spotify.com/playlist/311oOk5BT2OJ2ckcaT8Ers?si=4m5mtJmASFSGuZbaLSX07w --cookie-file music.youtube.com_cookies.txt --threads 1 --yt-dlp-args "--sleep-requests 2" --save-errors errores.txt
