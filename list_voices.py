# AISSY - Copyright (c) 2026 Geovana Ribeiro Borges (noxieeex).
# Todos os direitos reservados.

import pyttsx3

engine = pyttsx3.init()

for voice in engine.getProperty("voices"):
    print(voice.name, "|", voice.id)
