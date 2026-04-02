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