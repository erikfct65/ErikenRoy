import time
from playwright.sync_api import sync_playwright
import requests
from bs4 import BeautifulSoup
import os

# --- CONFIGURATIE ---
WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK')
MAX_PRICE = 1200.00
found_deals = set()

def send_discord_notification(message):
    if not WEBHOOK_URL:
        print("FOUT: DISCORD_WEBHOOK is niet ingesteld!")
        return
    try:
        requests.post(WEBHOOK_URL, json={"content": message}, timeout=10)
        print("Notificatie succesvol verzonden.")
    except Exception as e:
        print(f"Fout bij verzenden naar Discord: {e}")

def scrape_corendon(p):
    site_name = "Corendon"
    print(f"\n[{site_name}] Start check voor maart/april 2027 (Nieuwe Layout)...")
    browser = None
    try:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36')
        page = context.new_page()

        # Jouw geniale URL met custom datumbereik voor de flexibele periode!
        url = "https://www.corendon.nl/search?countryId=74&psort=2&tripDuration=10-*&departDate=%5B270301,270430%5D"
        page.goto(url, timeout=60000)
        
        # Probeer cookies te accepteren als die in de weg zitten
        try:
            cookie_selector = "button:has-text('Accepteren')"
            page.click(cookie_selector, timeout=10000)
            page.wait_for_selector(cookie_selector, state='hidden', timeout=5000)
        except Exception:
            pass # Geen cookie pop-up gevonden of al weggeklikt

        # Wacht tot de NIEUWE hotelkaarten geladen zijn
        results_selector = 'div[data-slot="card"]'
        page.wait_for_selector(results_selector, timeout=30000)
        
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        accommodations = soup.find_all('div', attrs={"data-slot": "card"})
        deals_found_count = 0
        
        for acco in accommodations:
            # 1. Titel ophalen
            title_el = acco.find('h4', class_='font-heading')
            name = title_el.text.strip() if title_el else "Onbekend Hotel"

            # 2. Link ophalen
            link_el = acco.find('a', href=True)
            if link_el:
                deal_url = "https://www.corendon.nl" + link_el['href']
            else:
                continue # Geen link? Dan slaan we hem over
            
            # 3. Prijs ophalen
            price_el = acco.find('span', class_='text-h5')
            if price_el:
                price_text = price_el.text.strip().replace('.', '').replace(',', '.')
                try:
                    price_pp = float(price_text)
                except ValueError:
                    continue # Als de prijs geen getal is, sla dan over
            else:
                continue
            
            # 4. Vertrekdatum en Reisduur ophalen via icoontjes
            departure_date = "Onbekend"
            duration_text = "Onbekend"
            
            # Zoek het kalender icoontje en pak de tekst ernaast
            cal_icon = acco.find('span', class_=lambda c: c and 'calendar-today' in c)
            if cal_icon:
                date_span = cal_icon.find_next_sibling('span', attrs={'data-role': 'text'})
                if date_span: departure_date = date_span.text.strip()
                
            # Zoek het maan/nacht icoontje en pak de tekst ernaast
            night_icon = acco.find('span', class_=lambda c: c and 'clear-night' in c)
            if night_icon:
                night_span = night_icon.find_next_sibling('span', attrs={'data-role': 'text'})
                if night_span: duration_text = night_span.text.strip()

            # --- Check de Deal ---
            if price_pp < MAX_PRICE:
                deals_found_count += 1
                deal_id = f"Corendon-{name}-{price_pp}-{departure_date}"
                
                if deal_id not in found_deals:
                    message = (
                        f"🎉 **DEAL GEVONDEN (MAART/APRIL '27)!** 🎉\n\n"
                        f"**Hotel:** {name}\n"
                        f"**Vertrekdatum:** {departure_date}\n"
                        f"**Reisduur:** {duration_text}\n"
                        f"**Prijs p.p.:** €{price_pp:.2f}\n"
                        f"**Link naar Deal:** {deal_url}\n\n"
                        f"@everyone"
                    )
                    send_discord_notification(message)
                    found_deals.add(deal_id)
        
        if deals_found_count == 0:
            print(f"Geen deals onder de €{MAX_PRICE} gevonden.")
        else:
            print(f"Succes! {deals_found_count} deals gevonden en doorgestuurd/opgeslagen.")

    except Exception as e:
        print(f"[{site_name}] FOUT: {e}")
    finally:
        if browser:
            browser.close()

if __name__ == "__main__":
    with sync_playwright() as p:
        scrape_corendon(p)
