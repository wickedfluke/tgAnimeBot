import google.generativeai as genai
from config import gemini_api_key

genai.configure(api_key=gemini_api_key)

def consiglia_anime(nome_anime):
    prompt = f"Mi piace l'anime '{nome_anime}'. Puoi consigliarmi altri anime simili? Non porre altre domande o richieste, grazie. Non formattare il testo della risposta in nessun modo!!!. Spiega il perché di ogni suggerimento. Inizia dicendo Ecco dei consigli se ti piace '{nome_anime}'!"
    
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    
    if response and response.text:
        return response.text.strip()
    else:
        return "❌ Non riesco a trovare suggerimenti in questo momento."
    
def riconosci_anime(nome_anime, lista_nomi):
    prompt = f"Hai il nome di un anime che è '{nome_anime}' e ti viene passata una lista di nomi che è '{lista_nomi}'. Quello che mi devi restituire è la tua percentuale di sicurezza che i nomi che ti sono stati passati nella lista nomi corrispondano allo stesso anime che ti è stato passato inizialmente. La risposta deve essere strutturata (per ogni anime nella lista nomi): 'Nome anime' - 'percentuale sicurezza' e nient'altro"
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)

    if response and response.text:
        return response.text.strip()
    else:
        return "❌ Anime non riconosciuto."
