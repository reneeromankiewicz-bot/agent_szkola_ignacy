import os
import json
import requests
from google import genai

# 1. Konfiguracja kluczy (będą bezpiecznie ukryte w chmurze)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

# Inicjalizacja klienta Gemini
client = genai.Client(api_key=GEMINI_API_KEY)

def pobierz_zadania_z_vulcana():
    # Tutaj wpinamy bibliotekę vulcan-api.
    # Na potrzeby tego przykładu symulujemy pobranie świeżego wpisu z dziennika dziecka:
    return [
        {
            "id": "12345",
            "przedmiot": "Chemia",
            "termin": "2026-09-17",
            "tresc": "Przypominam o kartkówce - obowiązuje materiał: otrzymywanie i wzory kwasów, mechanizmy reakcji."
        }
    ]

def analizuj_z_gemini(zadanie):
    prompt = f"""
    Jesteś empatycznym asystentem edukacyjnym i korepetytorem. 
    Oto wpis z e-dziennika: "{zadanie['tresc']}" (Przedmiot: {zadanie['przedmiot']}, Termin: {zadanie['termin']}).
    
    Przygotuj zwięzły raport do wysłania na komunikator w formacie:
    1. 🎯 **Cel:** (krótko co jest do zrobienia/nauczenia)
    2. 📅 **Termin:** (kiedy)
    3. 💡 **Wskazówka od asystenta:** (Napisz jedno zdanie wsparcia ułatwiające start. Jeśli to trudny materiał, podpowiedz na co uważać lub jak to zapamiętać).
    
    Zwróć sam sformatowany tekst.
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

def wyslij_na_slacka(tekst_raportu):
    # Struktura wiadomości Slack z interaktywnym przyciskiem
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
                            "text": "✅ Oznacz jako zrobione"
                        },
                        "style": "primary",
                        "value": "zrobione_12345"
                    }
                ]
            }
        ]
    }
    
    requests.post(SLACK_WEBHOOK_URL, json=payload)

def main():
    zadania = pobierz_zadania_z_vulcana()
    
    for zadanie in zadania:
        print(f"Przetwarzam zadanie: {zadanie['przedmiot']}")
        raport = analizuj_z_gemini(zadanie)
        wyslij_na_slacka(raport)
        print("Wysłano na Slacka!")

if __name__ == "__main__":
    main()
