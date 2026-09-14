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
        
        print("Wpisuję e-mail i klikam 'Dalej'...")
        # Czekamy ułamek sekundy upewniając się, że formularz jest gotowy
        page.wait_for_selector("input[type='email']", timeout=10000)
        page.locator("input[type='email']").first.fill(VULCAN_EMAIL, force=True)
        page.locator("button:has-text('Dalej')").first.click(force=True)
        
        print("Czekam na pojawienie się pola na hasło...")
        # TO JEST KLUCZOWE: Czekamy aż animacja "kroku 2" całkowicie się zakończy i pole będzie widoczne
        page.wait_for_selector("#Password", state="visible", timeout=10000)
        
        print("Wpisuję hasło i klikam 'Zaloguj'...")
        page.locator("#Password").first.fill(VULCAN_PASSWORD, force=True)
        page.locator("button:has-text('Zaloguj')").first.click(force=True)
        
        print("Weryfikuję logowanie (czekam na załadowanie portalu)...")
        # Czekamy na słowo "Wylogowanie", które oznacza 100% pewności, że jesteśmy w środku!
        page.wait_for_selector("text=Wylogowanie", timeout=15000)
        
        print("Zalogowano pomyślnie! Przechodzę bezpośrednio do dziennika...")
        page.goto("https://eduvulcan.pl/dostep-do-dziennika/")
        page.wait_for_timeout(3000) 
        
        print("Wybieram profil ucznia...")
        try:
            page.locator("text=Ignacy Romankiewicz").first.click(force=True)
            print("Kliknięto w profil. Czekam na załadowanie dziennika...")
            page.wait_for_timeout(5000) 
        except Exception as e:
            print("Nie znalazłem profilu ucznia...")
        
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
        # Klikamy zakładkę z zadaniami
        page.locator("text=Sprawdziany i zadania domowe").first.click(force=True)
        
        # Dajemy stronie 4 sekundy na pobranie listy zadań z serwera
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
