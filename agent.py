import os
import requests
from google import genai
from playwright.sync_api import sync_playwright

# Konfiguracja z GitHub Secrets
VULCAN_EMAIL = os.environ.get("VULCAN_EMAIL")
VULCAN_PASSWORD = os.environ.get("VULCAN_PASSWORD")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

client = genai.Client(api_key=GEMINI_API_KEY)

def pobierz_dane_z_przegladarki():
    print("Uruchamiam wirtualną przeglądarkę...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        page = browser.new_page()
        
        print("Logowanie: Otwieram stronę...")
        page.goto("https://eduvulcan.pl/logowanie")
        page.wait_for_timeout(3000) # Czekamy "sztywno" 3 sekundy, żeby formularz na pewno się załadował
        
        print("Wpisuję e-mail i klikam 'Dalej'...")
        # Wracamy do elastycznego lokalizatora, który działał wcześniej
        page.locator("input[type='email'], input[name='email'], input[type='text']").first.fill(VULCAN_EMAIL, force=True)
        page.locator("button:has-text('Dalej')").first.evaluate("el => el.click()")
        
        print("Czekam na pojawienie się pola na hasło...")
        page.wait_for_timeout(2000) # Czekamy na animację kroku 2
        
        print("Wpisuję hasło i klikam 'Zaloguj'...")
        page.locator("#Password, input[type='password']").first.fill(VULCAN_PASSWORD, force=True)
        page.locator("button[type='submit'], button:has-text('Zaloguj')").first.evaluate("el => el.click()")
        
        print("Weryfikuję logowanie (czekam na 'Wylogowanie')...")
        # To upewni nas, że hasło zostało przyjęte i jesteśmy w środku
        page.wait_for_selector("text=Wylogowanie", timeout=15000)
        
        print("Zalogowano pomyślnie! Przechodzę bezpośrednio do zakładki wyboru profilu...")
        page.goto("https://eduvulcan.pl/dostep-do-dziennika/")
        page.wait_for_timeout(4000) 
        
        print("Wybieram profil ucznia...")
        try:
            # Używamy evaluate, żeby kliknięcie na pewno weszło, ignorując ewentualne ukryte warstwy CSS
            page.locator("text=Ignacy Romankiewicz").first.evaluate("el => el.click()")
            print("Kliknięto w profil. Czekam na przekierowanie do e-dziennika...")
            page.wait_for_timeout(5000) 
        except Exception as e:
            print("Nie znalazłem profilu ucznia. Lecę dalej...")
        
        try:
            print("Czekam na załadowanie panelu (szukam słowa Tablica)...")
            page.wait_for_selector("text=Tablica", timeout=15000)
        except Exception as e:
            print("\n❌ UWAGA: Nie znalazłem 'Tablicy'. Oto co widzę na ekranie:")
            print("================ POCZĄTEK EKRANU ================")
            print(page.inner_text("body"))
            print("================ KONIEC EKRANU ================\n")
            raise Exception("Zatrzymano skrypt - sprawdź logi.")
            
        print("Nawigacja do zadań...")
        page.locator("text=Sprawdziany i zadania domowe").first.evaluate("el => el.click()")
        
        page.wait_for_timeout(4000) 
        
        print("Kopiuję tekst ze strony...")
        surowy_tekst = page.inner_text("body")
        
        browser.close()
        return surowy_tekst

def analizuj_z_gemini(surowy_tekst):
    print("Przekazuję dane do Gemini...")
    prompt = f"""
    Jesteś asystentem edukacyjnym. Poniżej znajduje się surowy zrzut tekstu z dziennika elektronicznego z zakładki 'Sprawdziany i zadania domowe'.
    
    Twoje zadanie:
    1. Przeskanuj tekst i znajdź wszystkie aktualne zadania domowe i nadchodzące sprawdziany/kartkówki.
    2. Zignoruj elementy menu, stopki, daty przeszłe i elementy nawigacyjne.
    3. Jeśli nie ma nic nowego, zwróć dokładnie jedno słowo: "BRAK".
    4. Jeśli są nadchodzące zadania/sprawdziany (np. chemia, języki obce), przygotuj raport w formacie:
       🎯 **Przedmiot:** [Nazwa]
       📅 **Termin:** [Kiedy]
       💡 **Wskazówka od asystenta:** [Krótka, jednozdaniowa merytoryczna pomoc do nauki tego materiału].
       
    Oto tekst do analizy:
    {surowy_tekst}
    """
    
    # TUTAJ JEST ZMIANA NA WERSJĘ 3.6
    response = client.models.generate_content(
        model="gemini-3.6-flash", 
        contents=prompt
    )
    return response.text.strip()

def wyslij_na_slacka(tekst_raportu):
    # Czasami modele dopisują kropkę lub białe znaki, upewnijmy się
    if "BRAK" in tekst_raportu.upper():
        print("Brak nowych zadań - pomijam wysyłkę na Slacka.")
        return
        
    print("\n--- WYGENEROWANY RAPORT Z GEMINI ---")
    print(tekst_raportu)
    print("------------------------------------\n")
        
    print("Wysyłam raport na Slacka...")
    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": tekst_raportu
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Sprawdzone"
                        },
                        "style": "primary",
                        "value": "zrobione_ok"
                    }
                ]
            }
        ]
    }
    
    # Przechwytujemy odpowiedź od Slacka
    odpowiedz = requests.post(SLACK_WEBHOOK_URL, json=payload)
    
    if odpowiedz.status_code == 200:
        print("✅ Sukces! Slack przyjął wiadomość (Kod 200).")
    else:
        print(f"❌ BŁĄD SLACKA! Odrzucono wiadomość. Kod: {odpowiedz.status_code}")
        print(f"Szczegóły błędu od Slacka: {odpowiedz.text}")

def main():
    try:
        dane = pobierz_dane_z_przegladarki()
        raport = analizuj_z_gemini(dane)
        wyslij_na_slacka(raport)
        print("Proces zakończony sukcesem!")
    except Exception as e:
        print(f"Wystąpił błąd: {e}")

if __name__ == "__main__":
    main()
