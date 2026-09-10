import musdb

db = musdb.DB(root='./musdb18_amostra', download=True)

for track in db.load_mus_tracks():
    print(f"Baixado: {track.name}")

