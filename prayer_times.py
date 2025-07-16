from flask import current_app
import os
import datetime

LOCAL_TIME_OFFSET = datetime.timedelta(hours=2)

# Klassenbasierte Lösung
class PrayerTimes:
    def __init__(self, app=None):
        self.data = {}
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        self.app = app
        self.data = self._load_data()
        
    def _load_data(self):
        prayer_times_data = {}
        try:
            file_path = os.path.join(self.app.static_folder, 'gb.txt')
            
            # Fallback: Versuche verschiedene Pfade
            if not os.path.exists(file_path):
                # Alternativer Pfad im Projektverzeichnis
                file_path = os.path.join(os.path.dirname(__file__), 'static', 'gb.txt')
            
            if not os.path.exists(file_path):
                # Noch ein alternativer Pfad
                file_path = 'gb.txt'
            
            if not os.path.exists(file_path):
                self.app.logger.error(f"gb.txt nicht gefunden. Suchpfade: {file_path}")
                return {}
            
            with open(file_path, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    try:
                        # Beispiel-Format: 2024-01-01,05:30,07:15,12:45,15:30,17:45,19:30
                        parts = line.split()
                        if len(parts) >= 7:
                            date_str = parts[0]
                            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                            
                            prayer_times_data[date_obj] = {
                                "fajr": parts[1],
                                "sunrise": parts[2], 
                                "dhuhr": parts[3],
                                "asr": parts[4],
                                "maghrib": parts[5],
                                "isha": parts[6]
                            }
                    except (ValueError, IndexError) as e:
                        self.app.logger.warning(f"Ungültige Zeile in gb.txt: {line} - Fehler: {e}")
                        continue
                        
            self.app.logger.info(f"Gebetszeiten für {len(prayer_times_data)} Tage geladen")
                        
        except FileNotFoundError:
            self.app.logger.error("gb.txt Datei nicht gefunden")
        except Exception as e:
            self.app.logger.error(f"Fehler beim Laden der Gebetszeiten: {str(e)}")
            
        return prayer_times_data

    def get_for_date(self, date):
        if not self.data:
            return {"error": "Gebetszeiten nicht verfügbar - Datei nicht geladen"}
        
        result = self.data.get(date)
        if result:
            return result
        else:
            # Fallback: Versuche benachbarte Daten
            for i in range(1, 8):  # Suche bis zu 7 Tage vor/nach
                prev_date = date - datetime.timedelta(days=i)
                next_date = date + datetime.timedelta(days=i)
                
                if prev_date in self.data:
                    result = self.data[prev_date].copy()
                    result["note"] = f"Geschätzte Zeiten (von {prev_date})"
                    return result
                    
                if next_date in self.data:
                    result = self.data[next_date].copy()
                    result["note"] = f"Geschätzte Zeiten (von {next_date})"
                    return result
            
            return {
                "error": f"Keine Gebetszeiten für {date} verfügbar",
                "fajr": "--:--",
                "sunrise": "--:--", 
                "dhuhr": "--:--",
                "asr": "--:--",
                "maghrib": "--:--",
                "isha": "--:--"
            }

# Singleton-Instanz
prayer_times = PrayerTimes()

# Legacy-Funktion für Kompatibilität
def get_prayer_times_for_date(date):
    if not prayer_times.data:
        raise RuntimeError("Call prayer_times.init_app() first")
    return prayer_times.get_for_date(date)