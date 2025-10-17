import time
from playwright.sync_api import sync_playwright
import requests
from bs4 import BeautifulSoup
import os # Nodig om de webhook URL veilig in te lezen

# --- CONFIGURATIE ---
# De webhook URL wordt nu veilig ingelezen uit de "Secrets" van GitHub
WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK')
MAX_PRICE = 1200.00
found_deals = set()

def send_discord_notification(message):
    if not WEBHOOK_URL:
        print("FOUT: DISCORD_WEBHOOK is niet ingesteld in GitHub Secrets!")
        return
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
        browser = p.chromium.launch(headless=True) # MOET True zijn voor GitHub Actions
        context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36')
        page = context.new_page()

        url = "https://www.corendon.nl/curacao?departDate=%5B260201,260429%5D&psort=2&tripDuration=10-%2a"
        page.goto(url, timeout=60000)
        
        try:
            cookie_selector = "button:has-text('Accepteren')"
            page.click(cookie_selector, timeout=15000)
            print(f"[{site_name}] Cookie banner weggeklikt.")
            page.wait_for_selector(cookie_selector, state='hidden', timeout=5000)
        except Exception:
            print(f"[{site_name}] Geen cookie banner gevonden of kon niet klikken, ga door.")

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
            print(f"[{site_name}] Browser sessie afgesloten.")

if __name__ == "__main__":
    print("--- Start Curaçao Deal Bot (GitHub Actions) ---")
    with sync_playwright() as p:
        scrape_corendon(p)
    print("--- Check voltooid ---")
