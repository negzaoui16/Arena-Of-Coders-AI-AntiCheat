# -*- coding: utf-8 -*-
import requests, json
url_scan = 'http://127.0.0.1:8001/scan-audio'
url_learn = 'http://127.0.0.1:8001/learn-audio'
try:
  print('1. Scan:', requests.post(url_scan, files={'audio': open('Vocal/Enregistrement (4).m4a', 'rb')}).json())
  print('2. Learn:', requests.post(url_learn, data={'text': 'وانا اصنعوزك استينعي دي حلالا الى سوات واطائي نتيجة الى اصعوط'}).json())
  print('3. Scan:', requests.post(url_scan, files={'audio': open('Vocal/Enregistrement (4).m4a', 'rb')}).json())
except Exception as e: print(e)