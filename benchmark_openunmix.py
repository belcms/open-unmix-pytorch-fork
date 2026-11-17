import os
import time
import shutil
import subprocess
import pandas as pd
import museval
import psutil
import threading


# ================= CONFIGURAÇÕES =================
PASTA_TESTES = "./musdb18_wav/test"
PASTA_TEMP = "./temp_mixtures"
PASTA_SAIDA = "./estimativas_benchmark"

# Modelos que você deseja comparar (ex: quantizado, padrão e fine-tunado)
MODELOS = ["umx", "umxhq"]
# =================================================

def preparar_ambiente():
    """Cria pastas necessárias e limpa diretórios temporários antigos."""
    os.makedirs(PASTA_TEMP, exist_ok=True)
    os.makedirs(PASTA_SAIDA, exist_ok=True)

def rodar_benchmark():
    preparar_ambiente()
    
    # Lista todas as subpastas (músicas) dentro da pasta de teste
    musicas = [d for d in os.listdir(PASTA_TESTES) if os.path.isdir(os.path.join(PASTA_TESTES, d))]
    
    resultados_finais = []

    for modelo in MODELOS:
        print(f"\n[{modelo}] Iniciando inferência...")
        tempo_total_modelo = 0
        pico_cpu = 0
        pico_ram_mb = 0
        
        for musica in musicas:
            caminho_mix_original = os.path.join(PASTA_TESTES, musica, "mixture.wav")
            
            # Copiamos o mixture.wav para temp/NomeDaMusica.wav 
            # Isso força o Open-Unmix a nomear a pasta de saída corretamente para o museval
            caminho_mix_temp = os.path.join(PASTA_TEMP, f"{musica}.wav")
            shutil.copy(caminho_mix_original, caminho_mix_temp)
            
            pasta_estimativas_modelo = os.path.join(PASTA_SAIDA, modelo)
            
            # Comando do Open-Unmix
            comando = [
                "umx", 
                "--model", modelo, 
                "--outdir", pasta_estimativas_modelo, 
                caminho_mix_temp
            ]
            
            print(f"  -> Processando: {musica}")
            inicio_tempo = time.time()

            processo = subprocess.Popen(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)



            try:
                ps_proc = psutil.Process(processo.pid)
                while processo.poll() is None:
                    cpu = ps_proc.cpu_percent(interval=0.1)
                    ram = ps_proc.memory_info().rss / (1024 * 1024)

                    if cpu > pico_cpu:
                        pico_cpu = cpu
                    if ram > pico_ram_mb:
                        pico_ram_mb = ram
            except psutil.NoSuchProcess:
                pass

            processo.wait()
            fim_tempo = time.time()

            tempo_decorrido = fim_tempo - inicio_tempo
            tempo_total_modelo += tempo_decorrido
            
            # Limpa o arquivo temporário
            os.remove(caminho_mix_temp)
            
        tempo_medio = tempo_total_modelo / len(musicas)
        
        print(f"[{modelo}] Inferência concluída. Calculando SDR (Qualidade)...")
        pasta_estimativas_modelo = os.path.join(PASTA_SAIDA, modelo)
        
        sdrs_do_modelo = []
        pasta_refs_temp = "./temp_refs"
        
        for musica in musicas:
            ref_dir_track = os.path.join(PASTA_TESTES, musica)
            est_dir_track = os.path.join(pasta_estimativas_modelo, musica)
            
            # --- CORREÇÃO: ISOLANDO O GABARITO ---
            ref_isolada = os.path.join(pasta_refs_temp, musica)
            os.makedirs(ref_isolada, exist_ok=True)
            
            # Copiamos apenas as 4 trilhas para o museval não ler o mixture.wav
            for inst in ["bass.wav", "drums.wav", "other.wav", "vocals.wav"]:
                shutil.copy(os.path.join(ref_dir_track, inst), os.path.join(ref_isolada, inst))
            # -------------------------------------
            
            try:
                # Aponta o avaliador para a pasta limpa temporária
                resultados_avaliacao = museval.eval_dir(
                    reference_dir=ref_isolada, 
                    estimates_dir=est_dir_track
                )
                
                df = resultados_avaliacao.df
                sdr_track = df[df['metric'] == 'SDR']['score'].median()
                sdrs_do_modelo.append(sdr_track)
                
            except Exception as e:
                print(f"  -> Erro ao avaliar a faixa {musica}: {e}")
        
        # Calcula a mediana global deste modelo usando Pandas
        sdr_mediano = pd.Series(sdrs_do_modelo).median() if sdrs_do_modelo else 0
        
        # Limpa o gabarito temporário do modelo atual
        if os.path.exists(pasta_refs_temp):
            shutil.rmtree(pasta_refs_temp)
        
        # Salvamos o resultado
        resultados_finais.append({
            "Modelo": modelo,
            "Tempo Total (s)": round(tempo_total_modelo, 2),
            "Tempo Médio por Faixa (s)": round(tempo_medio, 2),
            "SDR Mediano (dB)": round(sdr_mediano, 2),
            "Pico CPU (%)": round(pico_cpu, 2),
            "Pico RAM (MB)": round(pico_ram_mb, 2)
        })

    # ================= EXPORTAÇÃO =================
    print("\n" + "="*40)
    print("        RESULTADOS DO BENCHMARK")
    print("="*40)
    
    df_resultados = pd.DataFrame(resultados_finais)
    print(df_resultados.to_string(index=False))
    
    # Exporta para um arquivo CSV no projeto
    df_resultados.to_csv("resultados_benchmark.csv", index=False)
    print("\nOs dados completos foram salvos em 'resultados_benchmark.csv'.")
    
    # Limpa a pasta temporária
    shutil.rmtree(PASTA_TEMP)

if __name__ == "__main__":
    rodar_benchmark()