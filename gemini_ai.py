import google.generativeai as genai
from config import gemini_api_key  # Assicurati di avere questa chiave nel file config.py

genai.configure(api_key=gemini_api_key)

def consiglia_anime(nome_anime):
    prompt = f"Mi piace l'anime '{nome_anime}'. Puoi consigliarmi altri anime simili?"
    
    model = genai.GenerativeModel("gemini-1.5-flash")  # Usa il modello più veloce per risposte rapide
    response = model.generate_content(prompt)
    
    if response and response.text:
        return response.text.strip()
    else:
        return "❌ Non riesco a trovare suggerimenti in questo momento."
