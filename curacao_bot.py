import time
from playwright.sync_api import sync_playwright
import requests
from bs4 import BeautifulSoup
import re

# --- CONFIGURATIE ---
WEBHOOK_URL = "https://discord.com/api/webhooks/1428349084304932934/GTcWv8tSDZHdFOusnzv9zXImXeJ2O7ND02vpmbVCW02Xs_P_3byXj-rTgYHvFQdivEH3"
MAX_PRICE = 1015.00
INTERVAL_SECONDS = 900
found_deals = set()

def send_discord_notification(message):
    try:
        requests.post(WEBHOOK_URL, json={"content": message}, timeout=10)
        print("Notificatie succesvol verzonden.")
    except Exception as e:
        print(f"Fout bij verzenden naar Discord: {e}")

def scrape_corendon(p):
    site_name = "Corendon"
    print(f"\n[{site_name}] Start check...")
    browser = None
    try:
        # --- AANGEPAST: De browser is nu onzichtbaar ---
        browser = p.chromium.launch(headless=True) 
        context = browser.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36')
        page = context.new_page()

        url = "https://www.corendon.nl/curacao?departDate=%5B260201,260429%5D&psort=2&tripDuration=10-%2a"
        page.goto(url, timeout=60000)
        
        # De cookie-klik is mogelijk niet nodig, maar we laten hem erin voor de zekerheid.
        # Als hij de knop niet vindt na 5 seconden, gaat hij gewoon door.
        try:
            cookie_selector = "button:has-text('Accepteren')"
            page.click(cookie_selector, timeout=5000)
            print(f"[{site_name}] Cookie banner weggeklikt.")
            page.wait_for_selector(cookie_selector, state='hidden', timeout=5000)
        except Exception:
            print(f"[{site_name}] Geen cookie banner gevonden, ga direct door met zoeken naar deals.")

        results_selector = "article.cor-sr-item"
        page.wait_for_selector(results_selector, timeout=30000)
        print(f"[{site_name}] Deals gevonden. Verwerken van data...")
        
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        accommodations = soup.find_all('article', class_='cor-sr-item')
        deals_found_count = 0
        for acco in accommodations:
            title_element = acco.find('span', itemprop='name')
            price_element = acco.find('div', class_='cor-price-no-info').find('span')
            link_element = acco.find('div', class_='cor-sr-item__title').find('a', href=True)
            header_elements = acco.select('div.cor-results-price-block header span')
            
            departure_date = header_elements[0].text.strip() if len(header_elements) > 0 else "Onbekend"
            duration_text = header_elements[1].text.strip() if len(header_elements) > 1 else "Onbekend"

            if title_element and price_element and link_element:
                name = title_element.text.strip()
                price_pp = float(price_element.text.strip())
                total_price = price_pp * 2

                if price_pp < MAX_PRICE:
                    deals_found_count += 1
                    deal_url = link_element['href']
                    deal_id = f"Corendon-{name}-{price_pp}-{departure_date}"
                    
                    if deal_id not in found_deals:
                        print(f"DEAL GEVONDEN: {name} op {departure_date} voor €{price_pp:.2f}")
                        message = (
                            f"🎉 **DEAL GEVONDEN!** 🎉\n\n"
                            f"**Hotel:** {name}\n"
                            f"**Vertrekdatum:** {departure_date}\n"
                            f"**Reisduur:** {duration_text}\n"
                            f"**Prijs p.p.:** €{price_pp:.2f} (Totaal ca.: €{total_price:.2f})\n\n"
                            f"**Link naar Deal:** {deal_url}\n\n"
                            f"@everyone"
                        )
                        send_discord_notification(message)
                        found_deals.add(deal_id)
        
        if deals_found_count == 0:
            print(f"Geen deals onder de €{MAX_PRICE} gevonden in deze run.")

    except Exception as e:
        print(f"[{site_name}] FOUT: {e}")
    finally:
        if browser:
            browser.close()
            print(f"[{site_name}] Check voltooid, browser sessie afgesloten.")

# --- HOOFDPROGRAMMA ---
if __name__ == "__main__":
    print(f"--- Definitieve Curaçao Deal Bot (Onzichtbare Modus - Max €{MAX_PRICE}) ---")
    try:
        with sync_playwright() as p:
            while True:
                scrape_corendon(p)
                print(f"\n--- Wachten voor {int(INTERVAL_SECONDS / 60)} minuten... ---")
                time.sleep(INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n--- Script gestopt door gebruiker. ---")