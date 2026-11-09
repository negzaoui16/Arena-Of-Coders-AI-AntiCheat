import requests
import os
import glob
import json
import sys

# Force UTF-8 encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

URL = "http://127.0.0.1:8001/scan-audio"
FOLDER_PATH = "Vocal"

def test_audio_folder():
    print("--- Demarrage du test sur les fichiers vocaux ---")
    
    # Check if folder exists
    if not os.path.exists(FOLDER_PATH):
        print(f"Erreur : Le dossier {FOLDER_PATH} n'existe pas.")
        return

    # Grab all supported audio files
    audio_extensions = ("*.m4a", "*.mp3", "*.wav")
    files_to_test = []
    for ext in audio_extensions:
        files_to_test.extend(glob.glob(os.path.join(FOLDER_PATH, ext)))

    if not files_to_test:
        print(f"Aucun fichier audio trouve dans {FOLDER_PATH}.")
        return

    results = []

    for file_path in files_to_test:
        file_name = os.path.basename(file_path)
        print(f"\n[TEST] Test de l'audio : {file_name}...")
        
        try:
            with open(file_path, "rb") as audio_file:
                # Prepare the multipart/form-data payload
                files = {"audio": (file_name, audio_file, "audio/mp4")}
                
                # Send the POST request to the API
                response = requests.post(URL, files=files)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    print(f"-> Accepte : {data.get('accepte')}")
                    print(f"-> Score de Confiance : {data.get('confiance')}%")
                    print(f"-> Transcription : '{data.get('transcription')}'")
                    print(f"-> Message IA : {data.get('message')}")
                    
                    data["file"] = file_name
                    results.append(data)
                else:
                    print(f"-> Erreur {response.status_code}: {response.text}")
                    results.append({"file": file_name, "error": response.text})
                    
        except Exception as e:
            print(f"-> Erreur d'execution : {e}")
            results.append({"file": file_name, "error": str(e)})

    # Save Results to JSON file
    result_file = "vocal_test_results.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
        
    print(f"\nResultats sauvegardes dans {result_file}")

if __name__ == "__main__":
    test_audio_folder()
