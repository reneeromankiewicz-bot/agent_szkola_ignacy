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
        # Uruchamiamy Chromium w tle (headless)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 1. Logowanie do eduVULCAN
        print("Logowanie...")
        page.goto("https://eduvulcan.pl/logowanie")
        
        # Wypełniamy pola (Playwright szuka pól po ich typie lub id)
        page.fill("input[type='email']", VULCAN_EMAIL)
        page.fill("input[type='password']", VULCAN_PASSWORD)
        page.click("button[type='submit']")
        
        # Czekamy na załadowanie głównego panelu (szukamy tekstu "Tablica" z Twojego screena)
        page.wait_for_selector("text=Tablica", timeout=15000)
        
        # 2. Przejście do zadań
        print("Nawigacja do zadań...")
        # Klikamy w element menu na podstawie tekstu
        page.click("text=Sprawdziany i zadania domowe")
        
        # Czekamy chwilę na przeładowanie widoku
        page.wait_for_timeout(3000) 
        
        # 3. Pobranie całego widocznego tekstu z głównego kontenera strony
        # Zamiast parsować HTML, pobieramy czysty tekst, Gemini sobie z tym poradzi
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
