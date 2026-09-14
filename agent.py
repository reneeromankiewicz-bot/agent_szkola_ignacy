def pobierz_dane_z_przegladarki():
    print("Uruchamiam wirtualną przeglądarkę...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        page = browser.new_page()
        
        # 1. Logowanie do eduVULCAN
        print("Logowanie: Otwieram stronę...")
        page.goto("https://eduvulcan.pl/logowanie")
        page.wait_for_timeout(2000)
        
        print("Wpisuję e-mail i klikam 'Dalej'...")
        page.locator("input[type='email'], input[name='email'], input[type='text']").first.fill(VULCAN_EMAIL, force=True)
        page.locator("button:has-text('Dalej')").first.evaluate("el => el.click()")
        
        page.wait_for_timeout(2000)
        
        print("Wpisuję hasło i klikam 'Zaloguj'...")
        page.locator("#Password, input[type='password']").first.fill(VULCAN_PASSWORD, force=True)
        page.locator("button[type='submit'], button:has-text('Zaloguj')").first.evaluate("el => el.click()")
        
        page.wait_for_load_state("networkidle", timeout=15000)
        
        # NOWY KROK: Wymuszamy przejście bezpośrednio do widoku wyboru dziennika!
        print("Przechodzę bezpośrednio do zakładki wyboru profilu...")
        page.goto("https://eduvulcan.pl/dostep-do-dziennika/")
        page.wait_for_timeout(3000) # Czekamy na załadowanie listy profili
        
        print("Wybieram profil ucznia...")
        try:
            # Używamy fragmentu tekstu, aby uniknąć problemów z dopiskami (np. 'Akwinata')
            page.locator("text=Ignacy Romankiewicz").first.evaluate("el => el.click()")
            print("Kliknięto w profil. Czekam na przekierowanie do e-dziennika...")
            # Po kliknięciu Vulcan otwiera dziennik, musimy chwilę poczekać
            page.wait_for_timeout(5000) 
        except Exception as e:
            print("Nie znalazłem profilu ucznia - próbuję szukać Tablicy mimo to...")
        
        try:
            print("Czekam na załadowanie panelu (szukam słowa Tablica)...")
            page.wait_for_selector("text=Tablica", timeout=10000)
        except Exception as e:
            print("\n❌ UWAGA: Nie znalazłem 'Tablicy'. Oto co widzę na ekranie:")
            print("================ POCZĄTEK EKRANU ================")
            print(page.inner_text("body"))
            print("================ KONIEC EKRANU ================\n")
            raise Exception("Zatrzymano skrypt - sprawdź logi, aby zobaczyć ekran pośredni.")
            
        # 2. Przejście do zadań
        print("Nawigacja do zadań...")
        page.locator("text=Sprawdziany i zadania domowe").first.evaluate("el => el.click()")
        
        # Dajemy stronie czas na załadowanie listy sprawdzianów
        page.wait_for_timeout(4000) 
        
        # 3. Pobranie tekstu
        print("Kopiuję tekst ze strony...")
        surowy_tekst = page.inner_text("body")
        
        browser.close()
        return surowy_tekst
