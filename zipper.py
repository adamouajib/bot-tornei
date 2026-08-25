import zipfile
import os

files_to_zip = ['main.py', 'discloud.config', 'requirements.txt', '.env']
with zipfile.ZipFile('bot.zip', 'w') as z:
    for f in files_to_zip:
        if os.path.exists(f):
            z.write(f)
            
print("Fatto! zip creato.")