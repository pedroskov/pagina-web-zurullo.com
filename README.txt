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
|Creación y mantenimiento de tablas/bases de datos|

# Creación tablas
cd /home/pedro/Desktop/proyectos/zulo
python3 -c "from app import app, db; app.app_context().__enter__(); db.create_all()"
sudo systemctl restart zulo
