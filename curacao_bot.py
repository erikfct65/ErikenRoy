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
    print(f"\n[{site_name}] Start check voor maart/april 2027...")
    browser = None
    try:
        # Weer teruggezet op True, zodat GitHub hem onzichtbaar op de achtergrond kan draaien
        browser = p.chromium.launch(headless=True) 
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()

        # De slimme flexibele URL
        url = "https://www.corendon.nl/search?countryId=74&psort=2&tripDuration=10-*&departDate=%5B270301,270430%5D"
        page.goto(url, timeout=60000)
        
        # Agressieve JavaScript Cookie-Killer
        print("Cookies wegklikken...")
        try:
            page.evaluate("""
                document.querySelectorAll('button').forEach(b => {
                    if(b.innerText.includes('Accepteren') || b.innerText.includes('Akkoord')) {
                        b.click();
                    }
                });
            """)
            time.sleep(2)
        except Exception:
            pass

        print("Wachten op vakanties (Oude óf Nieuwe layout)...")
        # De bot wacht op de oude class (cor-sr-item) OF de nieuwe (data-slot="card")
        page.wait_for_selector('article.cor-sr-item, div[data-slot="card"]', timeout=30000)
        
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # We zoeken naar beide soorten blokken
        old_layout_items = soup.find_all('article', class_='cor-sr-item')
        new_layout_items = soup.find_all('div', attrs={"data-slot": "card"})
        
        deals_found_count = 0
        
        # --- LOGICA VOOR DE NIEUWE LAYOUT ---
        if len(new_layout_items) > 0:
            print(f"✅ NIEUWE layout gedetecteerd! ({len(new_layout_items)} hotels gevonden)")
            for acco in new_layout_items:
                title_el = acco.find('h4', class_='font-heading')
                name = title_el.text.strip() if title_el else "Onbekend Hotel"

                link_el = acco.find('a', href=True)
                deal_url = "https://www.corendon.nl" + link_el['href'] if link_el else ""
                
                price_el = acco.find('span', class_='text-h5')
                if not price_el or not deal_url: continue
                
                try: price_pp = float(price_el.text.strip().replace('.', '').replace(',', '.'))
                except ValueError: continue
                
                departure_date = "Onbekend"
                duration_text = "Onbekend"
                cal_icon = acco.find('span', class_=lambda c: c and 'calendar-today' in c)
                if cal_icon and cal_icon.find_next_sibling('span'): 
                    departure_date = cal_icon.find_next_sibling('span').text.strip()
                night_icon = acco.find('span', class_=lambda c: c and 'clear-night' in c)
                if night_icon and night_icon.find_next_sibling('span'): 
                    duration_text = night_icon.find_next_sibling('span').text.strip()

                if price_pp < MAX_PRICE:
                    deals_found_count += 1
                    deal_id = f"Corendon-{name}-{price_pp}-{departure_date}"
                    if deal_id not in found_deals:
                        message = f"🎉 **DEAL GEVONDEN (MAART/APRIL '27)!** 🎉\n\n**Hotel:** {name}\n**Vertrekdatum:** {departure_date}\n**Reisduur:** {duration_text}\n**Prijs p.p.:** €{price_pp:.2f}\n**Link naar Deal:** {deal_url}\n\n@everyone"
                        send_discord_notification(message)
                        found_deals.add(deal_id)

        # --- LOGICA VOOR DE OUDE LAYOUT ---
        elif len(old_layout_items) > 0:
            print(f"✅ OUDE layout gedetecteerd! ({len(old_layout_items)} hotels gevonden)")
            for acco in old_layout_items:
                title_element = acco.find('span', itemprop='name')
                price_wrapper = acco.find('div', class_='cor-price-no-info')
                price_element = price_wrapper.find('span') if price_wrapper else None
                
                link_wrapper = acco.find('div', class_='cor-sr-item__title')
                link_element = link_wrapper.find('a', href=True) if link_wrapper else None
                
                header_elements = acco.select('div.cor-results-price-block header span')
                departure_date = header_elements[0].text.strip() if len(header_elements) > 0 else "Onbekend"
                duration_text = header_elements[1].text.strip() if len(header_elements) > 1 else "Onbekend"

                if title_element and price_element and link_element:
                    name = title_element.text.strip()
                    try: price_pp = float(price_element.text.strip().replace('.', '').replace(',', '.'))
                    except ValueError: continue
                    
                    deal_url = "https://www.corendon.nl" + link_element['href'] if not link_element['href'].startswith('http') else link_element['href']

                    if price_pp < MAX_PRICE:
                        deals_found_count += 1
                        deal_id = f"Corendon-{name}-{price_pp}-{departure_date}"
                        if deal_id not in found_deals:
                            message = f"🎉 **DEAL GEVONDEN (MAART/APRIL '27)!** 🎉\n\n**Hotel:** {name}\n**Vertrekdatum:** {departure_date}\n**Reisduur:** {duration_text}\n**Prijs p.p.:** €{price_pp:.2f}\n**Link naar Deal:** {deal_url}\n\n@everyone"
                            send_discord_notification(message)
                            found_deals.add(deal_id)

        if deals_found_count == 0:
            print(f"Geen deals onder de €{MAX_PRICE} gevonden.")
        else:
            print(f"Succes! {deals_found_count} deals gevonden en doorgestuurd/opgeslagen.")

    except Exception as e:
        print(f"[{site_name}] SCRAPER GESTOPT: {e}")
    finally:
        if browser:
            browser.close()

if __name__ == "__main__":
    with sync_playwright() as p:
        scrape_corendon(p)
