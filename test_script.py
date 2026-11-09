import os
import requests
import json
import time

API_URL = "http://127.0.0.1:8000/scan"
TEST_FOLDER = "test_images"

def test_10_images():
    print("--- Demarrage du test sur les images ---")
    
    if not os.path.exists(TEST_FOLDER):
        print(f"Le dossier '{TEST_FOLDER}' n'existe pas. Veuillez le creer.")
        os.makedirs(TEST_FOLDER)
        return

    images = [f for f in os.listdir(TEST_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.avif', '.webp'))]
    
    if not images:
        print(f"Aucune image trouvee.")
        return

    results_data = []

    for img_name in images:
        img_path = os.path.join(TEST_FOLDER, img_name)
        print(f"[TEST] Test de l'image : {img_name}...")
        
        try:
            with open(img_path, 'rb') as f:
                start_time = time.time()
                response = requests.post(API_URL, files={'image': (img_name, f, 'image/jpeg')})
                end_time = time.time()
                
                if response.status_code == 200:
                    result = response.json()
                    result["file"] = img_name
                    result["time_s"] = round(end_time - start_time, 2)
                    results_data.append(result)
                else:
                    results_data.append({"file": img_name, "error": response.text})
        except Exception as e:
            results_data.append({"file": img_name, "error": str(e)})

    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=4)
    print("Resultats sauvegardes dans test_results.json")

if __name__ == "__main__":
    test_10_images()
