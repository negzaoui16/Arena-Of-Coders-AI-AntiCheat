import json
with open('test_results.json', encoding='utf-8') as f:
    for r in json.load(f):
        if 'error' in r:
            print(f"{r['file']} ERROR: {r['error']}")
        else:
            score = r.get('details', {}).get('zero_shot_score', 0)
            bonus = r.get('details', {}).get('memory_bonus', 0)
            mem = r.get('details', {}).get('images_in_memory', 0)
            print(f"{r['file']} | ACCEPTE: {r['accepte']} | Total: {r['confiance']}% (ZeroShot: {score}%, Bonus: +{bonus}%) | Memoire totale: {mem}")
