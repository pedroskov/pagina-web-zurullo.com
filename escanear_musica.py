"""
Uso:
    cd /home/pedro/Desktop/proyectos/zulo
    python3 escanear_musica.py
    sudo systemctl restart zulo

Requiere:  pip install mutagen --break-system-packages
"""
import os
from mutagen import File as MutagenFile

from app import app, db, Playlist, Cancion, MUSICA_PATH

EXTENSIONES = ('.mp3', '.m4a', '.flac', '.ogg', '.opus', '.wav')


def leer_tags(ruta_abs):
    titulo = artista = album = None
    duracion = 0.0
    try:
        f = MutagenFile(ruta_abs, easy=True)
        if f is not None:
            if getattr(f, 'info', None) is not None:
                duracion = float(f.info.length)
            if f.tags:
                def tag(clave):
                    valor = f.tags.get(clave)
                    return valor[0] if valor else None
                titulo, artista, album = tag('title'), tag('artist'), tag('album')
    except Exception as e:
        print(f'  No se pudieron leer las tags de {ruta_abs}: {e}')

    if not titulo:
        titulo = os.path.splitext(os.path.basename(ruta_abs))[0]
    return titulo, (artista or 'Desconocido'), (album or ''), duracion


def escanear():
    if not os.path.isdir(MUSICA_PATH):
        print(f'No existe la carpeta {MUSICA_PATH}. Hazla y copia dentro una carpeta por playlist.')
        return

    with app.app_context():
        db.create_all()
        total_nuevas = 0
        total_borradas = 0

        for carpeta in sorted(os.listdir(MUSICA_PATH)):
            ruta_carpeta = os.path.join(MUSICA_PATH, carpeta)
            if not os.path.isdir(ruta_carpeta):
                continue

            playlist = Playlist.query.filter_by(carpeta=carpeta).first()
            if not playlist:
                playlist = Playlist(nombre=carpeta, carpeta=carpeta)
                db.session.add(playlist)
                db.session.commit()
            print(f'\nPlaylist: {carpeta}')

            # Todos los audios que hay ahora en disco (rutas relativas a MUSICA_PATH)
            en_disco = set()
            for raiz, _, ficheros in os.walk(ruta_carpeta):
                for nombre in ficheros:
                    if nombre.lower().endswith(EXTENSIONES):
                        en_disco.add(os.path.relpath(os.path.join(raiz, nombre), MUSICA_PATH))

            # Los que ya estaban en la base de datos
            existentes = {c.ruta: c for c in Cancion.query.filter_by(playlist_id=playlist.id)}

            # Canciones nuevas
            nuevas = sorted(en_disco - set(existentes))
            for i, rel in enumerate(nuevas, 1):
                titulo, artista, album, duracion = leer_tags(os.path.join(MUSICA_PATH, rel))
                db.session.add(Cancion(
                    playlist_id=playlist.id, titulo=titulo, artista=artista,
                    album=album, duracion=duracion, ruta=rel
                ))
                if i % 100 == 0:
                    db.session.commit()
                    print(f'  ... {i}/{len(nuevas)}')
            db.session.commit()

            # Canciones que ya no están en disco
            borradas = set(existentes) - en_disco
            for rel in borradas:
                db.session.delete(existentes[rel])
            db.session.commit()

            print(f'  + {len(nuevas)} nuevas   - {len(borradas)} eliminadas   '
                  f'= {len(en_disco)} en total')
            total_nuevas += len(nuevas)
            total_borradas += len(borradas)

        print(f'\nListo. {total_nuevas} canciones añadidas, {total_borradas} eliminadas.')


if __name__ == '__main__':
    escanear()