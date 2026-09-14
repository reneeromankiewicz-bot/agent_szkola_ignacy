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
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 1. Logowanie do eduVULCAN
        print("Logowanie...")
        page.goto("https://eduvulcan.pl/logowanie")
        page.wait_for_timeout(2000) # Czekamy 2 sekundy na załadowanie ew. skryptów
        
        # Elastyczne wyszukiwanie pól (jeśli nie email, to text)
        page.locator("input[type='email'], input[name='email'], input[type='text']").first.fill(VULCAN_EMAIL)
        page.locator("input[type='password'], input[name='password']").first.fill(VULCAN_PASSWORD)
        
        # Szukamy przycisku logowania
        page.locator("button[type='submit'], button:has-text('Zaloguj'), button:has-text('Zaloguj się')").first.click()
        
        # Czekamy na załadowanie głównego panelu (np. słowo Tablica)
        print("Czekam na załadowanie panelu...")
        page.wait_for_selector("text=Tablica", timeout=20000)
        
        # 2. Przejście do zadań
        print("Nawigacja do zadań...")
        page.click("text=Sprawdziany i zadania domowe")
        
        page.wait_for_timeout(3000) # Czekamy aż lista zadań się wczyta
        
        # 3. Pobranie całego widocznego tekstu z głównego kontenera
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
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text.strip()

def wyslij_na_slacka(tekst_raportu):
    if tekst_raportu == "BRAK":
        print("Brak nowych zadań - pomijam wysyłkę na Slacka.")
        return
        
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
    requests.post(SLACK_WEBHOOK_URL, json=payload)

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
