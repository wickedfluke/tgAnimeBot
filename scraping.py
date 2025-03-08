from telethon import Button
import requests
from bs4 import BeautifulSoup
import hashlib

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
            
            short_hash = hashlib.md5(link.encode()).hexdigest()[:8]
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
        
        for a in soup.find_all("a", href=True):
            if a["href"].startswith("https://www.animesaturn.cx/watch?file"):
                return a["href"]
        
    return None

# Funzione per ottenere il video mp4 dalla pagina di streaming
def trova_video_mp4(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        video_tag = soup.find("source", type="video/mp4")
        if video_tag:
            return video_tag["src"]
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
            
            streaming_link = trova_link_streaming(link_ep)
            if streaming_link:
                episodi.append(Button.inline(f"{ep_numero}", data=streaming_link))
            else:
                episodi.append(Button.inline(f"{ep_numero} (Nessun streaming)", data="no_stream"))

        return episodi if episodi else []
    else:
        return []