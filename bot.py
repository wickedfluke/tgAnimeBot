from telethon import TelegramClient, events, Button
from config import api_id, api_hash, bot_token
from scraping import cerca_anime, trova_episodi, trova_video_mp4
from gemini_ai import consiglia_anime
import os

cerca_anime_cache = {}

bot = TelegramClient("bot_session", api_id, api_hash).start(bot_token=bot_token)

# Funzione per la schermata home
async def show_home(event):
    buttons = [
        [Button.inline("🔍 Cerca Anime", data="cerca_anime")],
        [Button.inline("🏠 Torna alla home", data="home")]
    ]
    await event.respond(
        "🏠 Benvenuto nel bot! Scegli una delle opzioni:",
        buttons=buttons
    )

@bot.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    await show_home(event)

# Gestione della schermata home
@bot.on(events.CallbackQuery(data="home"))
async def home_handler(event):
    await show_home(event)

# Gestione del comando /cerca (inizia la ricerca dell'anime)
@bot.on(events.NewMessage(pattern="/cerca (.+)"))
async def cerca_handler(event):
    nome_anime = event.pattern_match.group(1)
    risultati, pagina = cerca_anime(nome_anime)

    if not risultati:
        await event.reply("❌ Nessun risultato trovato.")
        return

    cerca_anime_cache[event.chat_id] = {
        "nome": nome_anime,
        "risultati": risultati,
        "pagina": pagina,
        "previous_screen": "home",  # Schermata iniziale prima della ricerca
    }

    buttons = [Button.inline(titolo, data=short_hash) for titolo, link, short_hash in risultati]
    buttons_row = [buttons[i:i+2] for i in range(0, len(buttons), 2)]

    paginazione_buttons = []
    if pagina > 1:
        paginazione_buttons.append(Button.inline("⬅️ Precedente", data=f"page_{pagina-1}"))
    paginazione_buttons.append(Button.inline("➡️ Successivo", data=f"page_{pagina+1}"))
    
    # Pulsanti per tornare alla schermata precedente o home
    back_to_home_button = Button.inline("🏠 Torna alla home", data="home")
    back_button = Button.inline("↩️ Torna alla schermata precedente", data="back")

    await event.respond(
        f"🔍 Risultati per: `{nome_anime}`\n\nScegli un anime:",
        buttons=buttons_row + [paginazione_buttons, [back_button, back_to_home_button]],
        parse_mode="markdown"
    )

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode("utf-8")
    chat_id = event.chat_id

    # Check if the cache exists for the user
    if chat_id not in cerca_anime_cache:
        await event.answer("❌ Non hai avviato una ricerca anime. Usa il comando /cerca per iniziare.", alert=True)
        return

    if chat_id in cerca_anime_cache:
        risultati = cerca_anime_cache[chat_id]["risultati"]

    for titolo, link, short_hash in risultati:
            if data == short_hash:
                titolo_selezionato = titolo
                cerca_anime_cache[chat_id]["titolo_selezionato"] = titolo
    
    # Handling the "Torna alla schermata precedente"
    if data == "back":
        previous_screen = cerca_anime_cache.get(chat_id, {}).get("previous_screen")

        if previous_screen == "home":
            await show_home(event)
        elif previous_screen == "cerca_anime":
            nome_anime = cerca_anime_cache[chat_id]["nome"]
            risultati, pagina = cerca_anime(nome_anime)

            buttons = [Button.inline(titolo, data=short_hash) for titolo, link, short_hash in risultati]
            buttons_row = [buttons[i:i+2] for i in range(0, len(buttons), 2)]

            paginazione_buttons = []
            if pagina > 1:
                paginazione_buttons.append(Button.inline("⬅️ Precedente", data=f"page_{pagina-1}"))
            paginazione_buttons.append(Button.inline("➡️ Successivo", data=f"page_{pagina+1}"))
            
            # Pulsanti per tornare alla schermata precedente o home
            back_to_home_button = Button.inline("🏠 Torna alla home", data="home")
            back_button = Button.inline("↩️ Torna alla schermata precedente", data="back")

            await event.edit(
                f"🔍 Risultati per: `{nome_anime}`\n\nScegli un anime:",
                buttons=buttons_row + [paginazione_buttons, [back_button, back_to_home_button]],
                parse_mode="markdown"
            )
        else:
            await event.answer("❌ Non è possibile tornare indietro.", alert=True)
        return

    # Handling pagination
    if data.startswith("page_"):
        pagina = int(data.split("_")[1])
        nome_anime = cerca_anime_cache[chat_id]["nome"]
        risultati, _ = cerca_anime(nome_anime, pagina)

        buttons = [Button.inline(titolo, data=short_hash) for titolo, link, short_hash in risultati]
        buttons_row = [buttons[i:i+2] for i in range(0, len(buttons), 2)]

        paginazione_buttons = []
        if pagina > 1:
            paginazione_buttons.append(Button.inline("⬅️ Precedente", data=f"page_{pagina-1}"))
        paginazione_buttons.append(Button.inline("➡️ Successivo", data=f"page_{pagina+1}"))
        
        # Pulsanti per tornare alla schermata precedente o home
        back_to_home_button = Button.inline("🏠 Torna alla home", data="home")
        back_button = Button.inline("↩️ Torna alla schermata precedente", data="back")

        await event.edit(
            f"🔍 Risultati per: `{nome_anime}`\n\nScegli un anime:",
            buttons=buttons_row + [paginazione_buttons, [back_button, back_to_home_button]],
            parse_mode="markdown"
        )

    # Handling selection of an anime
    elif data in [short_hash for _, _, short_hash in cerca_anime_cache[chat_id]["risultati"]]:
        url_anime = None
        for titolo, link, short_hash in cerca_anime_cache[chat_id]["risultati"]:
            if data == short_hash:
                url_anime = link
                break

        if url_anime:
            episodi = trova_episodi(url_anime)
            if not episodi:
                await event.answer("❌ Nessun episodio trovato.", alert=True)
                return

            cerca_anime_cache[chat_id]["episodi"] = episodi

            episodi_row = []
            for ep_numero, link in episodi:
                episodi_row.append([Button.inline(f"{ep_numero}", data=link)])

            nome_anime = cerca_anime_cache.get(chat_id, {}).get("nome", "Anime")

            consiglia_button = [Button.inline("🤖 Consigliami", data=f"consiglio_{nome_anime}")]
            back_button = Button.inline("↩️ Torna alla schermata precedente", data="back")
            back_to_home_button = Button.inline("🏠 Torna alla home", data="home")

            await event.edit(
                "📺 Episodi disponibili:",
                buttons=episodi_row + [consiglia_button, [back_button, back_to_home_button]],
                parse_mode="markdown"
            )

    # Handling the "Consigliami" button
    elif data.startswith("consiglio_"):
        nome_anime = data.replace("consiglio_", "")
        
        await event.answer("⌛ Sto cercando consigli... Attendi un momento.", alert=True)

        suggerimenti = consiglia_anime(nome_anime)
        back_button = Button.inline("↩️ Torna alla schermata precedente", data="back")
        back_to_home_button = Button.inline("🏠 Torna alla home", data="home")

        await event.respond(f"🎌 Ecco alcuni anime simili a '{nome_anime}':\n\n{suggerimenti}",
                            buttons=[[back_button, back_to_home_button]])

    # Handling the creation of M3U file
    elif data.startswith("http"):
        episodi = cerca_anime_cache.get(chat_id, {}).get("episodi", [])
        episode_info = next((ep for ep in episodi if ep[1] == data), None)
        if episode_info:
            ep_numero, ep_url = episode_info
        video_url = trova_video_mp4(ep_url)
        if video_url:
            nome_anime = cerca_anime_cache.get(chat_id, {}).get("nome", "Anime")
            titolo_selezionato = cerca_anime_cache.get(chat_id, {}).get("titolo_selezionato", "Sconosciuto")
            titolo_selezionato = titolo_selezionato.replace(":", "-").replace("?", "").replace("!", "").replace(" ", "_")
            file_name = f"{ep_numero} - {titolo_selezionato}.m3u"

            with open(file_name, "w") as f:
                f.write(f"#EXTM3U\n#EXTINF:-1,{ep_numero} - {titolo_selezionato}\n{video_url}")

            await bot.send_file(chat_id, file_name, caption="🎬 Ecco il file M3U per lo streaming.")
            os.remove(file_name)
        else:
            await event.answer("❌ Nessun link MP4 trovato.", alert=True)
    else:
        await event.answer("❌ Nessuna azione per questo pulsante.", alert=True)

# Avvio del bot
print("✅ Bot avviato! Aspettando messaggi...")

bot.run_until_disconnected()
