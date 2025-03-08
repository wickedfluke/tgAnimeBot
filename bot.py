from telethon import TelegramClient, events, Button
from config import api_id, api_hash, bot_token
from scraping import cerca_anime, trova_episodi, trova_video_mp4
from gemini_ai import consiglia_anime
import os

cerca_anime_cache = {}

bot = TelegramClient("bot_session", api_id, api_hash).start(bot_token=bot_token)

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
    }

    buttons = [Button.inline(titolo, data=short_hash) for titolo, link, short_hash in risultati]
    buttons_row = [buttons[i:i+2] for i in range(0, len(buttons), 2)]

    paginazione_buttons = []
    if pagina > 1:
        paginazione_buttons.append(Button.inline("⬅️ Precedente", data=f"page_{pagina-1}"))
    paginazione_buttons.append(Button.inline("➡️ Successivo", data=f"page_{pagina+1}"))
    
    await event.respond(
        f"🔍 Risultati per: `{nome_anime}`\n\nScegli un anime:",
        buttons=buttons_row + [paginazione_buttons],
        parse_mode="markdown"
    )

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode("utf-8")

    # Gestione della paginazione degli anime
    if data.startswith("page_"):
        pagina = int(data.split("_")[1])
        nome_anime = cerca_anime_cache[event.chat_id]["nome"]
        risultati, _ = cerca_anime(nome_anime, pagina)

        buttons = [Button.inline(titolo, data=short_hash) for titolo, link, short_hash in risultati]
        buttons_row = [buttons[i:i+2] for i in range(0, len(buttons), 2)]

        paginazione_buttons = []
        if pagina > 1:
            paginazione_buttons.append(Button.inline("⬅️ Precedente", data=f"page_{pagina-1}"))
        paginazione_buttons.append(Button.inline("➡️ Successivo", data=f"page_{pagina+1}"))
        
        await event.edit(
            f"🔍 Risultati per: `{nome_anime}`\n\nScegli un anime:",
            buttons=buttons_row + [paginazione_buttons],
            parse_mode="markdown"
        )

    # Gestione della selezione di un anime
    elif data in [short_hash for _, _, short_hash in cerca_anime_cache[event.chat_id]["risultati"]]:
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

            episodi_row = [episodi[i:i+2] for i in range(0, len(episodi), 2)]
            nome_anime = cerca_anime_cache.get(event.chat_id, {}).get("nome", "Anime")

            consiglia_button = [Button.inline("🤖 Consigliami", data=f"consiglio_{nome_anime}")]

            await event.edit(
                "📺 Episodi disponibili:",
                buttons=episodi_row + [consiglia_button],
                parse_mode="markdown"
            )

    # Gestione del pulsante "Consigliami"
    elif data.startswith("consiglio_"):
        nome_anime = data.replace("consiglio_", "")
        
        await event.answer("⌛ Sto cercando consigli... Attendi un momento.", alert=True)

        suggerimenti = consiglia_anime(nome_anime)
        await event.respond(f"🎌 Ecco alcuni anime simili a '{nome_anime}':\n\n{suggerimenti}")

    # Gestione della creazione del file M3U
    elif data.startswith("http"):
        video_url = trova_video_mp4(data)
        if video_url:
            ep_numero = data.split("=")[-1]
            nome_anime = cerca_anime_cache.get(event.chat_id, {}).get("nome", "Anime")
            file_name = f"{ep_numero} - {nome_anime}.m3u"

            with open(file_name, "w") as f:
                f.write(f"#EXTM3U\n#EXTINF:-1,{ep_numero} - {nome_anime}\n{video_url}")

            await bot.send_file(event.chat_id, file_name, caption="🎬 Ecco il file M3U per lo streaming.")
            os.remove(file_name)
        else:
            await event.answer("❌ Nessun link MP4 trovato.", alert=True)
    else:
        await event.answer("❌ Nessuna azione per questo pulsante.", alert=True)

print("✅ Bot avviato! Aspettando messaggi...")

bot.run_until_disconnected()
