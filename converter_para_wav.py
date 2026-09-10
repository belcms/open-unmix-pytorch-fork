import musdb
import soundfile as sf
import os

db = musdb.DB(root="./musdb18_amostra", is_wav=False)

pasta_destino = "./musdb18_wav"
for track in db.load_mus_tracks():
    print(f"extraindo: {track.name}")

    pasta_musica = os.path.join(pasta_destino, track.subset, track.name)
    os.makedirs(pasta_musica, exist_ok=True)

    sf.write(os.path.join(pasta_musica, "mixture.wav"), track.audio, track.rate)

    for nome_instrumento, trilha in track.targets.items():
        if nome_instrumento != 'linear_mixture':
            sf.write(os.path.join(pasta_musica, f"{nome_instrumento}.wav"), trilha.audio, track.rate)

print(f"Concluído! Pasta: {pasta_destino}")