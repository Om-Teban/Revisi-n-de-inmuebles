import json
import os
import time
import hashlib
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# ── Configuración ──────────────────────────────────────────────────────────────
with open("config.json") as f:
    CONFIG = json.load(f)

TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
VISTOS_FILE      = "vistos.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# ── Historial de vistos ────────────────────────────────────────────────────────
def cargar_vistos():
    if os.path.exists(VISTOS_FILE):
        with open(VISTOS_FILE) as f:
            return set(json.load(f))
    return set()

def guardar_vistos(vistos: set):
    with open(VISTOS_FILE, "w") as f:
        json.dump(list(vistos), f)

def uid(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()

# ── Scrapers ───────────────────────────────────────────────────────────────────

def scrape_zonaprop() -> list[dict]:
    """Scrapea ZonaProp con los filtros del config."""
    resultados = []
    precio_min = CONFIG["precio_min"]
    precio_max = CONFIG["precio_max"]

    # ZonaProp URL para alquiler monoambiente CABA dueño directo
    # Ejemplo: /alquiler-departamento-1-ambiente-capital-federal-dueno-directo-precio-400000-550000
    url = (
        f"https://www.zonaprop.com.ar/departamentos-alquiler-1-ambiente-capital-federal"
        f"-dueno-directo-precio-{precio_min}-{precio_max}-orden-precio-menor.html"
    )

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        tarjetas = soup.select("div[data-id]")[:20]
        for t in tarjetas:
            try:
                link_tag = t.select_one("a[href*='/propiedades/']")
                if not link_tag:
                    continue
                link = "https://www.zonaprop.com.ar" + link_tag["href"]

                precio_tag = t.select_one("[data-price]")
                precio_txt = precio_tag.get_text(strip=True) if precio_tag else "Sin precio"

                titulo_tag = t.select_one("h2, h3, .postingCardTitle")
                titulo = titulo_tag.get_text(strip=True) if titulo_tag else "Sin título"

                zona_tag = t.select_one(".postingCardLocation, [data-location]")
                zona = zona_tag.get_text(strip=True) if zona_tag else "CABA"

                m2_tag = t.select_one("[data-area], .surface")
                m2_txt = m2_tag.get_text(strip=True) if m2_tag else ""

                resultados.append({
                    "titulo": titulo,
                    "precio": precio_txt,
                    "zona": zona,
                    "m2": m2_txt,
                    "url": link,
                    "fuente": "ZonaProp",
                })
            except Exception:
                continue

    except Exception as e:
        print(f"[ZonaProp] Error: {e}")

    return resultados


def scrape_argenprop() -> list[dict]:
    """Scrapea Argenprop con los filtros del config."""
    resultados = []
    precio_min = CONFIG["precio_min"]
    precio_max = CONFIG["precio_max"]

    url = (
        f"https://www.argenprop.com/departamento/alquiler/capital-federal"
        f"?ambientes=1&precio-desde={precio_min}&precio-hasta={precio_max}"
        f"&solo-dueno=true&orden=menor-precio"
    )

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        tarjetas = soup.select(".listing__item, .card")[:20]
        for t in tarjetas:
            try:
                link_tag = t.select_one("a[href]")
                if not link_tag:
                    continue
                href = link_tag["href"]
                link = href if href.startswith("http") else "https://www.argenprop.com" + href

                precio_tag = t.select_one(".card__price, .price")
                precio_txt = precio_tag.get_text(strip=True) if precio_tag else "Sin precio"

                titulo_tag = t.select_one(".card__title, h2, h3")
                titulo = titulo_tag.get_text(strip=True) if titulo_tag else "Sin título"

                zona_tag = t.select_one(".card__address, .location")
                zona = zona_tag.get_text(strip=True) if zona_tag else "CABA"

                m2_tag = t.select_one(".card__common-data, .surface")
                m2_txt = m2_tag.get_text(strip=True) if m2_tag else ""

                resultados.append({
                    "titulo": titulo,
                    "precio": precio_txt,
                    "zona": zona,
                    "m2": m2_txt,
                    "url": link,
                    "fuente": "Argenprop",
                })
            except Exception:
                continue

    except Exception as e:
        print(f"[Argenprop] Error: {e}")

    return resultados


def scrape_mercadolibre() -> list[dict]:
    """Usa la API pública de MercadoLibre para mayor estabilidad."""
    resultados = []
    precio_min = CONFIG["precio_min"]
    precio_max = CONFIG["precio_max"]

    # MercadoLibre Inmuebles API — alquiler monoambiente CABA
    url = (
        "https://api.mercadolibre.com/sites/MLA/search"
        "?category=MLA1459"                         # Alquileres
        "&state=TUxBUENBUGw3M2JlMjI="               # CABA
        f"&price={precio_min}-{precio_max}"
        "&ROOMS=1"                                   # 1 ambiente
        "&seller_type=owner"                         # Dueño directo
        "&sort=price_asc"
        "&limit=20"
    )

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("results", []):
            atributos = {a["id"]: a.get("value_name", "") for a in item.get("attributes", [])}
            m2 = atributos.get("TOTAL_AREA", atributos.get("COVERED_AREA", ""))
            m2_txt = f"{m2} m²" if m2 else ""

            resultados.append({
                "titulo": item.get("title", "Sin título"),
                "precio": f"$ {item.get('price', 0):,.0f}",
                "zona": item.get("location", {}).get("neighborhood", {}).get("name", "CABA"),
                "m2": m2_txt,
                "url": item.get("permalink", ""),
                "fuente": "MercadoLibre",
            })

    except Exception as e:
        print(f"[MercadoLibre] Error: {e}")

    return resultados

# ── Scoring ────────────────────────────────────────────────────────────────────

def extraer_precio_numerico(precio_txt: str) -> float:
    """Extrae el valor numérico de un string de precio."""
    import re
    numeros = re.findall(r"[\d.]+", precio_txt.replace(",", ""))
    if numeros:
        return float(numeros[0].replace(".", ""))
    return float("inf")

def extraer_m2(m2_txt: str) -> float:
    import re
    numeros = re.findall(r"[\d]+", m2_txt)
    return float(numeros[0]) if numeros else 0.0

def puntaje(inmueble: dict) -> float:
    """
    Cuanto más bajo el precio y mayor el m², mejor el puntaje.
    Métrica principal: m² / precio (valor por m²).
    """
    precio = extraer_precio_numerico(inmueble["precio"])
    m2     = extraer_m2(inmueble["m2"])

    if precio == 0 or precio == float("inf"):
        return 0.0

    score = 0.0

    # 1. Relación m²/precio (principal)
    if m2 > 0:
        score += (m2 / precio) * 1_000_000

    # 2. Precio dentro del rango óptimo
    precio_min = CONFIG["precio_min"]
    precio_max = CONFIG["precio_max"]
    if precio_min <= precio <= precio_max:
        score += 10
        # Bonus si está en la mitad baja del rango
        if precio <= precio_min + (precio_max - precio_min) * 0.4:
            score += 5

    # 3. m² absolutos (más espacio = mejor)
    if m2 >= 35:
        score += 5
    if m2 >= 45:
        score += 5

    return round(score, 4)

# ── Telegram ───────────────────────────────────────────────────────────────────

def enviar_telegram(mensaje: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()

def formatear_mensaje(top5: list[dict]) -> str:
    hoy = datetime.now().strftime("%d/%m/%Y")
    lineas = [f"🏠 <b>Top 5 monoambientes CABA — {hoy}</b>\n"]

    for i, p in enumerate(top5, 1):
        m2_str = f" · {p['m2']}" if p["m2"] else ""
        lineas.append(
            f"<b>{i}. {p['titulo']}</b>\n"
            f"💰 {p['precio']}{m2_str}\n"
            f"📍 {p['zona']} · {p['fuente']}\n"
            f"🔗 {p['url']}\n"
        )

    lineas.append(f"Filtros: $\u20B9{CONFIG['precio_min']:,}–{CONFIG['precio_max']:,} · Dueño directo · 1 ambiente")
    return "\n".join(lineas)

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print(f"[{datetime.now()}] Iniciando búsqueda...")

    vistos = cargar_vistos()

    # Recolectar de las 3 fuentes
    todos = []
    for fn in [scrape_zonaprop, scrape_argenprop, scrape_mercadolibre]:
        resultados = fn()
        print(f"  {fn.__name__}: {len(resultados)} resultados")
        todos.extend(resultados)
        time.sleep(2)  # pausa entre requests

    # Filtrar ya vistos
    nuevos = [p for p in todos if uid(p["url"]) not in vistos]
    print(f"  Nuevos (no vistos): {len(nuevos)}")

    if not nuevos:
        enviar_telegram("🏠 Bot inmobiliario: no hay nuevos monoambientes hoy que no hayas visto ya.")
        return

    # Rankear y tomar top 5
    nuevos.sort(key=puntaje, reverse=True)
    top5 = nuevos[:5]

    # Enviar mensaje
    mensaje = formatear_mensaje(top5)
    enviar_telegram(mensaje)
    print("  Mensaje enviado.")

    # Actualizar vistos
    for p in top5:
        vistos.add(uid(p["url"]))
    guardar_vistos(vistos)
    print("  Vistos actualizados.")

if __name__ == "__main__":
    main()
