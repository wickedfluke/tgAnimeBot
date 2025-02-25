from telethon import TelegramClient, events, Button
import requests
from bs4 import BeautifulSoup
import hashlib
import os
import time
import aiohttp

# --- CONFIGURAZIONE ---
api_id = 25765102
api_hash = "ea1f34752c0860fa799b4153da5c5554"
bot_token = "1338679959:AAF-I2mwxJ2QBXm-RViC8mvoleaBNb8WiBo"

# Creiamo il client Telethon
bot = TelegramClient("bot_session", api_id, api_hash).start(bot_token=bot_token)

# Funzione per scaricare il video in modo asincrono
async def download_video(mp4_url, file_name):
    async with aiohttp.ClientSession() as session:
        async with session.get(mp4_url) as response:
            if response.status == 200:
                with open(file_name, "wb") as f:
                    async for chunk in response.content.iter_chunked(5 * 1024 * 1024):  # Usa chunk più grandi (1MB)
                        if chunk:
                            f.write(chunk)
                return True
            else:
                return False
    return False

# Funzione per inviare il video dopo il download
async def invia_video(client, chat_id, video_url):
    # Trova il video MP4 dalla pagina dello streaming (video_url è già completo)
    mp4_url = trova_video_mp4(video_url)
    if mp4_url:
        # Scarica il video
        file_name = "video.mp4"
        
        # Download asincrono
        print("Inizio download...")
        download_success = await download_video(mp4_url, file_name)
        if download_success:
            # Verifica che il video sia stato scaricato correttamente
            if os.path.exists(file_name) and os.path.getsize(file_name) > 0:
                print("Invio del video...")
                await client.send_file(chat_id, file_name)
                print("✅ Video inviato!")
                # Rimuovi il file temporaneo
                os.remove(file_name)
            else:
                await client.send_message(chat_id, "❌ Il video non è stato scaricato correttamente.")
        else:
            await client.send_message(chat_id, "❌ Impossibile scaricare il video.")
    else:
        await client.send_message(chat_id, "❌ Non è stato trovato il video.")

# Funzione per cercare anime
def cerca_anime(nome_anime, pagina=1):
    url = f"https://www.animesaturn.cx/animelist?search={nome_anime}&page={pagina}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        risultati = []

        for a in soup.find_all("a", class_="badge badge-archivio badge-light"):
            titolo = a.text.strip()
            link = a["href"]
            if not link.startswith("http"):
                link = f"https://www.animesaturn.cx{link}"
            
            # Generiamo un hash breve per l'URL (usiamo i primi 8 caratteri dell'hash)
            short_hash = hashlib.md5(link.encode()).hexdigest()[:8]
            
            # Limitiamo la lunghezza dei titoli per i pulsanti (max 30 caratteri)
            titolo_abbreviato = titolo[:30] + ("..." if len(titolo) > 30 else "")
            
            risultati.append((titolo_abbreviato, link, short_hash))

        return risultati if risultati else [], pagina
    else:
        return [], pagina

# Funzione per ottenere il link per lo streaming da una pagina episodio
def trova_link_streaming(url_anime):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url_anime, headers=headers)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Cerchiamo tutti i link <a> con un href
        link_streaming = None
        
        for a in soup.find_all("a", href=True):
            if a["href"].startswith("https://www.animesaturn.cx/watch?file"):
                link_streaming = a["href"]
                break  # Fermati al primo link trovato che corrisponde
        
        return link_streaming  # Restituisce il primo link valido trovato
    else:
        return None

# Funzione per ottenere il video mp4 dalla pagina di streaming
def trova_video_mp4(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Troviamo la sorgente del video
        video_tag = soup.find("source", type="video/mp4")
        if video_tag:
            mp4_url = video_tag["src"]
            # Aggiungiamo il dominio se l'URL è relativo
            return mp4_url
    return None

# Funzione per ottenere gli episodi con il link per lo streaming
def trova_episodi(url_anime):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url_anime, headers=headers)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        episodi = []

        for a in soup.find_all("a", class_="btn btn-dark mb-1 bottone-ep"):
            ep_numero = a.text.strip()
            link_ep = a["href"]
            if not link_ep.startswith("http"):
                link_ep = f"https://www.animesaturn.cx{link_ep}"
            
            # Troviamo il link per lo streaming per ogni episodio
            streaming_link = trova_link_streaming(link_ep)
            if streaming_link:
                # Formattiamo il link per il bot in modo che sia cliccabile come pulsante
                episodi.append(Button.inline(f"{ep_numero}", data=streaming_link))
            else:
                episodi.append(Button.inline(f"{ep_numero} (Nessun streaming)", data="no_stream"))

        return episodi if episodi else []
    else:
        return []

# Cache globale per i risultati di ricerca
cerca_anime_cache = {}

# Evento per la ricerca di anime
@bot.on(events.NewMessage(pattern="/cerca (.+)"))
async def cerca_handler(event):
    nome_anime = event.pattern_match.group(1)
    risultati, pagina = cerca_anime(nome_anime)

    if not risultati:
        await event.reply("❌ Nessun risultato trovato.")
        return

    # Salviamo i risultati nella cache
    cerca_anime_cache[event.chat_id] = {
        "nome": nome_anime,
        "risultati": risultati,
        "pagina": pagina,
    }

    # Suddividi i pulsanti in gruppi di 2 per la visualizzazione a due colonne
    buttons = [Button.inline(titolo, data=short_hash) for titolo, link, short_hash in risultati]
    buttons_row = [buttons[i:i+2] for i in range(0, len(buttons), 2)]  # Dividi i pulsanti in righe di 2

    # Paginazione: Aggiungiamo pulsanti per la paginazione
    paginazione_buttons = []
    if pagina > 1:
        paginazione_buttons.append(Button.inline("⬅️ Precedente", data=f"page_{pagina-1}"))
    paginazione_buttons.append(Button.inline("➡️ Successivo", data=f"page_{pagina+1}"))
    
    # Invia il messaggio con i pulsanti della ricerca e la paginazione
    await event.respond(
        f"🔍 Risultati per: `{nome_anime}`\n\nScegli un anime:",
        buttons=buttons_row + [paginazione_buttons],  # Aggiungi i pulsanti di paginazione
        parse_mode="markdown"
    )


@bot.on(events.CallbackQuery)
async def episodi_handler(event):
    data = event.data.decode("utf-8")

    # Se è un clic su una pagina per la paginazione
    if data.startswith("page_"):
        # Paginazione
        pagina = int(data.split("_")[1])
        nome_anime = cerca_anime_cache[event.chat_id]["nome"]
        risultati, _ = cerca_anime(nome_anime, pagina)

        # Suddividi i pulsanti in gruppi di 2 per la visualizzazione a due colonne
        buttons = [Button.inline(titolo, data=short_hash) for titolo, link, short_hash in risultati]
        buttons_row = [buttons[i:i+2] for i in range(0, len(buttons), 2)]  # Dividi i pulsanti in righe di 2

        # Paginazione: aggiungi i pulsanti per la navigazione
        paginazione_buttons = []
        if pagina > 1:
            paginazione_buttons.append(Button.inline("⬅️ Precedente", data=f"page_{pagina-1}"))
        paginazione_buttons.append(Button.inline("➡️ Successivo", data=f"page_{pagina+1}"))
        
        # Aggiungi i pulsanti di paginazione alla fine
        await event.edit(
            f"🔍 Risultati per: `{nome_anime}`\n\nScegli un anime:",
            buttons=buttons_row + [paginazione_buttons],
            parse_mode="markdown"
        )
    else:
        # Clic su un anime per vedere gli episodi
        url_anime = None
        for titolo, link, short_hash in cerca_anime_cache[event.chat_id]["risultati"]:
            if data == short_hash:
                url_anime = link
                break

        if url_anime:
            episodi = trova_episodi(url_anime)

            if not episodi:
                await event.answer("❌ Nessun episodio trovato.", alert=True)
                return

            # Suddividi i pulsanti degli episodi in gruppi di 2
            episodi_row = [episodi[i:i+2] for i in range(0, len(episodi), 2)]  # Dividi in righe di 2

            risposta = f"📺 Episodi disponibili:\n\n"

            # Aggiungi il messaggio "Invio video in corso"
            await event.edit(
                "🎬 Invio video in corso...\n\nStiamo preparando il video per il download.",
                parse_mode="markdown"
            )

            # Aggiungi i pulsanti degli episodi
            await event.edit(
                risposta,
                buttons=episodi_row + [[Button.inline("➡️ Avanti", data="next_page")]],  # Pulsante per andare avanti
                parse_mode="markdown"
            )


@bot.on(events.CallbackQuery)
async def invio_video_handler(event):
    data = event.data.decode("utf-8")
    if data.startswith("http"):
        # Scarica il video
        video_url = data
        await event.respond("🎬 Invio video in corso...")
        await invia_video(bot, event.chat_id, video_url)
    else:
        await event.answer("❌ Nessuno streaming disponibile per questo episodio.", alert=True)


# Avvia il bot
print("✅ Bot avviato! Aspettando messaggi...")
bot.run_until_disconnected()
