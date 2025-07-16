from flask import Flask, render_template, request, redirect, url_for, jsonify, abort, send_file, session, flash, make_response
import datetime
import json
import os
import base64
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from io import BytesIO
from collections import defaultdict
from flask_moment import Moment
from matplotlib.backends.backend_pdf import PdfPages
from flask_migrate import Migrate
from sqlalchemy import func, and_, or_, extract
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.units import cm
import qrcode

#from weasyprint import HTML, CSS
# App erstellen
app = Flask(__name__)
app.secret_key = 'dein_geheimer_schlüssel_12345'

# Flask-Moment initialisieren
moment = Moment(app)

# Datenbank konfigurieren (nur SQLite)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///local.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_PATH = os.path.join('static', 'Uploads')
os.makedirs(UPLOAD_PATH, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_PATH

# Datenbankinstanz initialisieren
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Datenbank-Modelle
class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    @property
    def date(self):
        return self.timestamp

class Kommentar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blog_id = db.Column(db.Integer, db.ForeignKey('blog_post.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    blog = db.relationship('BlogPost', backref=db.backref('kommentare', lazy=True))

class ahde_vefa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    birth_date = db.Column(db.String(20))
    death_date = db.Column(db.String(20))
    image_filename = db.Column(db.String(100))

class GalerieAlbum(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    beschreibung = db.Column(db.Text)
    erstellungsdatum = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    bilder = db.relationship('GalerieBild', backref='album', lazy=True, cascade="all, delete-orphan")

class GalerieBild(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    album_id = db.Column(db.Integer, db.ForeignKey('galerie_album.id'), nullable=True)
    dateiname = db.Column(db.String(255), nullable=False)
    titel = db.Column(db.String(100))
    beschreibung = db.Column(db.Text)
    upload_datum = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class AktuellesPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    comments = db.relationship('AktuellesKommentar', backref='post', lazy=True)

class AktuellesKommentar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('aktuelles_post.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class AdminMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_name = db.Column(db.String(100), nullable=False)
    sender_email = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    received_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    admin_response = db.Column(db.Text)
    response_date = db.Column(db.DateTime)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    event_date = db.Column(db.DateTime, nullable=False)
    event_time = db.Column(db.String(20))
    location = db.Column(db.String(200))
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_type = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    @property
    def is_past(self):
        return self.event_date < datetime.datetime.utcnow()


class CostCenter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    # Add this line for the 'code' column
    code = db.Column(db.String(50), unique=True, nullable=False)
    # Define relationships if you have them, e.g., to Process and Transaction
    processes = db.relationship('Process', backref='cost_center', lazy=True, cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='cost_center', lazy=True)

    def __repr__(self):
        return f"<CostCenter {self.code} - {self.name}>"

# Ensure Process and Transaction models are also defined below CostCenter if they refer to it
class Process(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False) # Make sure 'code' is also here for Process
    cost_center_id = db.Column(db.Integer, db.ForeignKey('cost_center.id'), nullable=False)
    transactions = db.relationship('Transaction', backref='process', lazy=True)

    def __repr__(self):
        return f"<Process {self.code} - {self.name}>"

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    beschreibung = db.Column(db.String(255), nullable=False)
    betrag = db.Column(db.Numeric(10, 2), nullable=False)
    typ = db.Column(db.String(50), nullable=False)  # 'einnahme', 'ausgabe'
    kategorie = db.Column(db.String(100))
    buchungsdatum = db.Column(db.Date, nullable=False)
    zahlungsart = db.Column(db.String(50), nullable=False)  # 'ueberweisung', 'bar', 'paypal', etc.
    kostenstelle_id = db.Column(db.Integer, db.ForeignKey('abteilung.id'), nullable=False)
    beleg_pfad = db.Column(db.String(255))
    
    # Erweiterte Felder
    belegnummer = db.Column(db.String(50), unique=True)
    mwst_satz = db.Column(db.Numeric(5, 2), default=0.00)
    mwst_betrag = db.Column(db.Numeric(10, 2), default=0.00)
    netto_betrag = db.Column(db.Numeric(10, 2))
    projekt_id = db.Column(db.Integer, db.ForeignKey('projekt.id'))
    verwendungszweck = db.Column(db.Text)
    
    # Metadaten
    erstellt_von = db.Column(db.Integer, db.ForeignKey('benutzer.id'), nullable=False)
    erstellt_am = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    geaendert_von = db.Column(db.Integer, db.ForeignKey('benutzer.id'))
    geaendert_am = db.Column(db.DateTime)
    genehmigt = db.Column(db.Boolean, default=False)
    genehmigt_von = db.Column(db.Integer, db.ForeignKey('benutzer.id'))
    genehmigt_am = db.Column(db.DateTime)
    
    # Wiederkehrende Buchungen
    ist_wiederkehrend = db.Column(db.Boolean, default=False)
    wiederkehr_intervall = db.Column(db.String(20))  # 'monatlich', 'jaehrlich', etc.
    naechste_buchung = db.Column(db.Date)
    parent_id = db.Column(db.Integer, db.ForeignKey('transaction.id'))  # Für Splitbuchungen
    
    def __repr__(self):
        return f"<Transaction {self.beschreibung}: {self.betrag}€>"

# ===== ERWEITERTE FINANZMODELLE =====

class Abteilung(db.Model):
    """Abteilungen/Kostenstellen der Gemeinde"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    beschreibung = db.Column(db.Text)
    abteilungsleiter_id = db.Column(db.Integer, db.ForeignKey('benutzer.id'))
    aktiv = db.Column(db.Boolean, default=True)
    budget_jaehrlich = db.Column(db.Numeric(12, 2))
    
    # Relationships
    transaktionen = db.relationship('Transaction', backref='abteilung', lazy=True)
    rechnungen = db.relationship('Rechnung', backref='abteilung', lazy=True)
    projekte = db.relationship('Projekt', backref='abteilung', lazy=True)
    
    def __repr__(self):
        return f"<Abteilung {self.code} - {self.name}>"

class Projekt(db.Model):
    """Projekte für Spendenzuordnung"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    beschreibung = db.Column(db.Text)
    abteilung_id = db.Column(db.Integer, db.ForeignKey('abteilung.id'), nullable=False)
    start_datum = db.Column(db.Date)
    end_datum = db.Column(db.Date)
    spendenziel = db.Column(db.Numeric(10, 2))
    aktiv = db.Column(db.Boolean, default=True)
    
    # Relationships
    spenden = db.relationship('Spende', backref='projekt', lazy=True)
    transaktionen = db.relationship('Transaction', backref='projekt', lazy=True)
    
    def gespendeter_betrag(self):
        return sum(spende.betrag for spende in self.spenden)
    
    def __repr__(self):
        return f"<Projekt {self.name}>"

class Spender(db.Model):
    """Spenderverwaltung"""
    id = db.Column(db.Integer, primary_key=True)
    anrede = db.Column(db.String(20))
    vorname = db.Column(db.String(50))
    nachname = db.Column(db.String(50), nullable=False)
    organisation = db.Column(db.String(100))
    strasse = db.Column(db.String(100))
    plz = db.Column(db.String(10))
    ort = db.Column(db.String(50))
    land = db.Column(db.String(50), default='Deutschland')
    telefon = db.Column(db.String(20))
    email = db.Column(db.String(120))
    
    # Spendenpräferenzen
    newsletter = db.Column(db.Boolean, default=False)
    dsgvo_zustimmung = db.Column(db.Boolean, default=False)
    dsgvo_datum = db.Column(db.DateTime)
    
    # Relationships
    spenden = db.relationship('Spende', backref='spender', lazy=True)
    
    @property
    def vollstaendiger_name(self):
        if self.organisation:
            return self.organisation
        return f"{self.vorname} {self.nachname}".strip()
    
    def __repr__(self):
        return f"<Spender {self.vollstaendiger_name}>"

class Spende(db.Model):
    """Spendenverwaltung"""
    id = db.Column(db.Integer, primary_key=True)
    spender_id = db.Column(db.Integer, db.ForeignKey('spender.id'), nullable=False)
    projekt_id = db.Column(db.Integer, db.ForeignKey('projekt.id'))
    betrag = db.Column(db.Numeric(10, 2), nullable=False)
    spende_datum = db.Column(db.Date, nullable=False)
    zahlungsart = db.Column(db.String(50), nullable=False)
    verwendungszweck = db.Column(db.Text)
    
    # Spendenbescheinigung
    quittung_erstellt = db.Column(db.Boolean, default=False)
    quittungsnummer = db.Column(db.String(50), unique=True)
    quittung_datum = db.Column(db.Date)
    quittung_pfad = db.Column(db.String(255))
    per_email_gesendet = db.Column(db.Boolean, default=False)
    
    # Metadaten
    erstellt_am = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<Spende {self.betrag}€ von {self.spender.vollstaendiger_name}>"

class Rechnung(db.Model):
    """Rechnungsstellung"""
    id = db.Column(db.Integer, primary_key=True)
    rechnungsnummer = db.Column(db.String(50), unique=True, nullable=False)
    datum = db.Column(db.Date, nullable=False)
    faelligkeitsdatum = db.Column(db.Date, nullable=False)
    
    # Kunde
    kunde_name = db.Column(db.String(100), nullable=False)
    kunde_strasse = db.Column(db.String(100))
    kunde_plz = db.Column(db.String(10))
    kunde_ort = db.Column(db.String(50))
    kunde_email = db.Column(db.String(120))
    
    # Rechnung
    abteilung_id = db.Column(db.Integer, db.ForeignKey('abteilung.id'), nullable=False)
    netto_betrag = db.Column(db.Numeric(10, 2), nullable=False)
    mwst_betrag = db.Column(db.Numeric(10, 2), default=0.00)
    brutto_betrag = db.Column(db.Numeric(10, 2), nullable=False)
    verwendungszweck = db.Column(db.Text)
    bemerkung = db.Column(db.Text)
    
    # Status
    status = db.Column(db.String(20), default='offen')  # 'offen', 'bezahlt', 'ueberfaellig', 'storniert'
    bezahlt_am = db.Column(db.Date)
    pdf_pfad = db.Column(db.String(255))
    per_email_gesendet = db.Column(db.Boolean, default=False)
    
    # Metadaten
    erstellt_von = db.Column(db.Integer, db.ForeignKey('benutzer.id'), nullable=False)
    erstellt_am = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    positionen = db.relationship('RechnungsPosition', backref='rechnung', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Rechnung {self.rechnungsnummer}: {self.brutto_betrag}€>"

class RechnungsPosition(db.Model):
    """Rechnungspositionen"""
    id = db.Column(db.Integer, primary_key=True)
    rechnung_id = db.Column(db.Integer, db.ForeignKey('rechnung.id'), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    beschreibung = db.Column(db.Text, nullable=False)
    menge = db.Column(db.Numeric(10, 2), default=1.00)
    einheit = db.Column(db.String(20), default='Stück')
    einzelpreis = db.Column(db.Numeric(10, 2), nullable=False)
    mwst_satz = db.Column(db.Numeric(5, 2), default=19.00)
    
    @property
    def netto_betrag(self):
        return self.menge * self.einzelpreis
    
    @property
    def mwst_betrag(self):
        return self.netto_betrag * (self.mwst_satz / 100)
    
    @property
    def brutto_betrag(self):
        return self.netto_betrag + self.mwst_betrag

class Benutzer(db.Model):
    """Erweiterte Benutzerverwaltung für Finanzsystem"""
    id = db.Column(db.Integer, primary_key=True)
    benutzername = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    passwort_hash = db.Column(db.String(256), nullable=False)
    
    # Persönliche Daten
    vorname = db.Column(db.String(50))
    nachname = db.Column(db.String(50))
    telefon = db.Column(db.String(20))
    
    # Berechtigungen
    rolle = db.Column(db.String(20), nullable=False, default='benutzer')  # 'admin', 'buchhalter', 'abteilungsleiter', 'benutzer'
    abteilung_id = db.Column(db.Integer, db.ForeignKey('abteilung.id'))
    aktiv = db.Column(db.Boolean, default=True)
    
    # Metadaten
    erstellt_am = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    letzter_login = db.Column(db.DateTime)
    
    def set_passwort(self, passwort):
        from werkzeug.security import generate_password_hash
        self.passwort_hash = generate_password_hash(passwort)
        
    def check_passwort(self, passwort):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.passwort_hash, passwort)
    
    def __repr__(self):
        return f"<Benutzer {self.benutzername}>"

class AuditLog(db.Model):
    """Revisionssichere Protokollierung aller Änderungen"""
    id = db.Column(db.Integer, primary_key=True)
    benutzer_id = db.Column(db.Integer, db.ForeignKey('benutzer.id'), nullable=False)
    tabelle = db.Column(db.String(50), nullable=False)
    datensatz_id = db.Column(db.Integer, nullable=False)
    aktion = db.Column(db.String(20), nullable=False)  # 'create', 'update', 'delete'
    alte_werte = db.Column(db.Text)  # JSON
    neue_werte = db.Column(db.Text)  # JSON
    zeitstempel = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    ip_adresse = db.Column(db.String(45))
    
    def __repr__(self):
        return f"<AuditLog {self.aktion} auf {self.tabelle}>"

class WiederkehrendeBuchung(db.Model):
    """Template für wiederkehrende Buchungen"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    beschreibung = db.Column(db.String(255), nullable=False)
    betrag = db.Column(db.Numeric(10, 2), nullable=False)
    typ = db.Column(db.String(50), nullable=False)
    kategorie = db.Column(db.String(100))
    zahlungsart = db.Column(db.String(50), nullable=False)
    abteilung_id = db.Column(db.Integer, db.ForeignKey('abteilung.id'), nullable=False)
    
    # Wiederholung
    intervall = db.Column(db.String(20), nullable=False)  # 'monatlich', 'jaehrlich'
    naechste_ausfuehrung = db.Column(db.Date, nullable=False)
    letzte_ausfuehrung = db.Column(db.Date)
    aktiv = db.Column(db.Boolean, default=True)
    
    # Metadaten
    erstellt_von = db.Column(db.Integer, db.ForeignKey('benutzer.id'), nullable=False)
    erstellt_am = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Kassenbuch(db.Model):
    """Kassenmodul für Barzahlungen"""
    id = db.Column(db.Integer, primary_key=True)
    datum = db.Column(db.Date, nullable=False)
    beschreibung = db.Column(db.String(255), nullable=False)
    einnahme = db.Column(db.Numeric(10, 2), default=0.00)
    ausgabe = db.Column(db.Numeric(10, 2), default=0.00)
    kassenstand = db.Column(db.Numeric(10, 2), nullable=False)
    abteilung_id = db.Column(db.Integer, db.ForeignKey('abteilung.id'), nullable=False)
    beleg_nr = db.Column(db.String(50))
    
    # Metadaten
    erfasst_von = db.Column(db.Integer, db.ForeignKey('benutzer.id'), nullable=False)
    erfasst_am = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Budgetplanung(db.Model):
    """Budgetplanung pro Abteilung"""
    id = db.Column(db.Integer, primary_key=True)
    abteilung_id = db.Column(db.Integer, db.ForeignKey('abteilung.id'), nullable=False)
    jahr = db.Column(db.Integer, nullable=False)
    monat = db.Column(db.Integer)  # Null für Jahresbudget
    
    # Geplante Beträge
    geplante_einnahmen = db.Column(db.Numeric(12, 2), default=0.00)
    geplante_ausgaben = db.Column(db.Numeric(12, 2), default=0.00)
    
    # Ist-Werte (werden automatisch berechnet)
    ist_einnahmen = db.Column(db.Numeric(12, 2), default=0.00)
    ist_ausgaben = db.Column(db.Numeric(12, 2), default=0.00)
    
    # Metadaten
    erstellt_von = db.Column(db.Integer, db.ForeignKey('benutzer.id'), nullable=False)
    erstellt_am = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    letzte_aktualisierung = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# MODELS
class Klasse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    schuljahr = db.Column(db.String(9), nullable=False)
    klassenstufe = db.Column(db.Integer)  # z.B. 5, 6, 7, etc.
    klassenlehrer_id = db.Column(db.Integer, db.ForeignKey('lehrer.id'))
    raum = db.Column(db.String(20))
    
    # Relationships
    schueler = db.relationship('Schueler', backref='klasse', lazy=True)
    unterrichtseinheiten = db.relationship('Unterrichtseinheit', backref='klasse', lazy=True)
    stundenplan = db.relationship('Stundenplan', backref='klasse', lazy=True)
    vertretungen = db.relationship('Vertretung', backref='klasse', lazy=True)
    hausaufgaben = db.relationship('Hausaufgabe', backref='klasse', lazy=True)
    lernziele = db.relationship('Lernziel', backref='klasse', lazy=True)
    pruefungen = db.relationship('Pruefung', backref='klasse', lazy=True)

class Schueler(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    nachname = db.Column(db.String(50), nullable=False)
    geburtsdatum = db.Column(db.Date)
    geschlecht = db.Column(db.String(1))
    klasse_id = db.Column(db.Integer, db.ForeignKey('klasse.id'), nullable=False)
    eltern_id = db.Column(db.Integer, db.ForeignKey('eltern.id'))
    email = db.Column(db.String(120))
    telefon = db.Column(db.String(20))
    adresse = db.Column(db.Text)
    eintrittsdatum = db.Column(db.Date)
    austrittsdatum = db.Column(db.Date)
    ist_aktiv = db.Column(db.Boolean, default=True)
    
    # Relationships
    noten = db.relationship('Note', backref='schueler', lazy=True)
    anwesenheiten = db.relationship('Anwesenheit', backref='schueler', lazy=True)
    hausaufgaben_abgaben = db.relationship('HausaufgabenAbgabe', backref='schueler', lazy=True)
    portfolios = db.relationship('Portfolio', backref='schueler', lazy=True)
    verhaltensbewertungen = db.relationship('Verhaltensbewertung', backref='schueler', lazy=True)
    pruefungs_ergebnisse = db.relationship('PruefungsErgebnis', backref='schueler', lazy=True)
    lernziel_fortschritte = db.relationship('LernzielFortschritt', backref='schueler', lazy=True)

class Unterrichtseinheit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datum = db.Column(db.Date, nullable=False)
    stunden = db.Column(db.String(10), nullable=False)
    thema = db.Column(db.String(100), nullable=False)
    inhalte = db.Column(db.Text)
    bemerkung = db.Column(db.Text)
    klasse_id = db.Column(db.Integer, db.ForeignKey('klasse.id'), nullable=False)
    fach_id = db.Column(db.Integer, db.ForeignKey('fach.id'), nullable=False)
    lehrer_id = db.Column(db.Integer, db.ForeignKey('lehrer.id'), nullable=False)
    hausaufgabe = db.Column(db.Text)  # Kurze Hausaufgabe direkt im Unterricht
    erstellt_am = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    anwesenheiten = db.relationship('Anwesenheit', backref='unterrichtseinheit', lazy=True)

class Anwesenheit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schueler_id = db.Column(db.Integer, db.ForeignKey('schueler.id'), nullable=False)
    unterrichtseinheit_id = db.Column(db.Integer, db.ForeignKey('unterrichtseinheit.id'), nullable=False)
    anwesend = db.Column(db.Boolean, default=False)
    entschuldigt = db.Column(db.Boolean, default=False)
    verspaetet = db.Column(db.Boolean, default=False)
    verspaetung_minuten = db.Column(db.Integer, default=0)

# Erweiterte Modelle für vollständiges Klassenbuch

class Fach(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    kuerzel = db.Column(db.String(10), nullable=False)
    farbe = db.Column(db.String(7), default='#007bff')  # Hex-Farbe für UI
    beschreibung = db.Column(db.Text)
    unterrichtseinheiten = db.relationship('Unterrichtseinheit', backref='fach', lazy=True)
    noten = db.relationship('Note', backref='fach', lazy=True)
    hausaufgaben = db.relationship('Hausaufgabe', backref='fach', lazy=True)

class Lehrer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kuerzel = db.Column(db.String(10), unique=True, nullable=False)
    vorname = db.Column(db.String(50), nullable=False)
    nachname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    telefon = db.Column(db.String(20))
    faecher = db.relationship('Fach', secondary='lehrer_fach', backref=db.backref('lehrer', lazy='dynamic'))
    klassen = db.relationship('Klasse', secondary='lehrer_klasse', backref=db.backref('lehrer', lazy='dynamic'))

# Zuordnungstabellen für Many-to-Many Beziehungen
lehrer_fach = db.Table('lehrer_fach',
    db.Column('lehrer_id', db.Integer, db.ForeignKey('lehrer.id'), primary_key=True),
    db.Column('fach_id', db.Integer, db.ForeignKey('fach.id'), primary_key=True)
)

lehrer_klasse = db.Table('lehrer_klasse',
    db.Column('lehrer_id', db.Integer, db.ForeignKey('lehrer.id'), primary_key=True),
    db.Column('klasse_id', db.Integer, db.ForeignKey('klasse.id'), primary_key=True)
)

class Stundenplan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    klasse_id = db.Column(db.Integer, db.ForeignKey('klasse.id'), nullable=False)
    fach_id = db.Column(db.Integer, db.ForeignKey('fach.id'), nullable=False)
    lehrer_id = db.Column(db.Integer, db.ForeignKey('lehrer.id'), nullable=False)
    wochentag = db.Column(db.Integer, nullable=False)  # 0=Montag, 6=Sonntag
    stunde = db.Column(db.Integer, nullable=False)  # 1-10
    raum = db.Column(db.String(20))
    gueltig_ab = db.Column(db.Date, nullable=False)
    gueltig_bis = db.Column(db.Date)
    
class Vertretung(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datum = db.Column(db.Date, nullable=False)
    stunde = db.Column(db.Integer, nullable=False)
    klasse_id = db.Column(db.Integer, db.ForeignKey('klasse.id'), nullable=False)
    original_lehrer_id = db.Column(db.Integer, db.ForeignKey('lehrer.id'), nullable=False)
    vertretung_lehrer_id = db.Column(db.Integer, db.ForeignKey('lehrer.id'))
    fach_id = db.Column(db.Integer, db.ForeignKey('fach.id'), nullable=False)
    art = db.Column(db.String(20), nullable=False)  # 'vertretung', 'ausfall', 'selbststudium'
    raum = db.Column(db.String(20))
    bemerkung = db.Column(db.Text)
    erstellt_am = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Bewertungstyp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # z.B. 'Klassenarbeit', 'Mündlich', 'Hausaufgabe'
    gewichtung = db.Column(db.Float, default=1.0)
    beschreibung = db.Column(db.Text)
    noten = db.relationship('Note', backref='bewertungstyp', lazy=True)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schueler_id = db.Column(db.Integer, db.ForeignKey('schueler.id'), nullable=False)
    fach_id = db.Column(db.Integer, db.ForeignKey('fach.id'), nullable=False)
    bewertungstyp_id = db.Column(db.Integer, db.ForeignKey('bewertungstyp.id'), nullable=False)
    note = db.Column(db.Float)  # Numerische Note (1.0-6.0)
    punkte = db.Column(db.Integer)  # Punkte (0-15 für Oberstufe)
    max_punkte = db.Column(db.Integer)
    kommentar = db.Column(db.Text)
    datum = db.Column(db.Date, nullable=False)
    lehrer_id = db.Column(db.Integer, db.ForeignKey('lehrer.id'), nullable=False)
    erstellt_am = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
class Hausaufgabe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titel = db.Column(db.String(200), nullable=False)
    beschreibung = db.Column(db.Text, nullable=False)
    fach_id = db.Column(db.Integer, db.ForeignKey('fach.id'), nullable=False)
    klasse_id = db.Column(db.Integer, db.ForeignKey('klasse.id'), nullable=False)
    lehrer_id = db.Column(db.Integer, db.ForeignKey('lehrer.id'), nullable=False)
    aufgegeben_am = db.Column(db.Date, nullable=False)
    faellig_am = db.Column(db.Date, nullable=False)
    erstellt_am = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    abgaben = db.relationship('HausaufgabenAbgabe', backref='hausaufgabe', lazy=True)

class HausaufgabenAbgabe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hausaufgabe_id = db.Column(db.Integer, db.ForeignKey('hausaufgabe.id'), nullable=False)
    schueler_id = db.Column(db.Integer, db.ForeignKey('schueler.id'), nullable=False)
    abgegeben_am = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    status = db.Column(db.String(20), default='abgegeben')  # 'abgegeben', 'verspaetet', 'fehlend'
    kommentar = db.Column(db.Text)
    datei_pfad = db.Column(db.String(255))
    bewertung = db.Column(db.String(50))  # 'sehr gut', 'gut', 'befriedigend', etc.

class Nachricht(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    absender_typ = db.Column(db.String(20), nullable=False)  # 'lehrer', 'eltern', 'schueler'
    absender_id = db.Column(db.Integer, nullable=False)
    empfaenger_typ = db.Column(db.String(20), nullable=False)
    empfaenger_id = db.Column(db.Integer, nullable=False)
    betreff = db.Column(db.String(200), nullable=False)
    inhalt = db.Column(db.Text, nullable=False)
    erstellt_am = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    gelesen_am = db.Column(db.DateTime)
    ist_gelesen = db.Column(db.Boolean, default=False)
    antwort_auf_id = db.Column(db.Integer, db.ForeignKey('nachricht.id'))
    
class Lernziel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titel = db.Column(db.String(200), nullable=False)
    beschreibung = db.Column(db.Text, nullable=False)
    fach_id = db.Column(db.Integer, db.ForeignKey('fach.id'), nullable=False)
    klasse_id = db.Column(db.Integer, db.ForeignKey('klasse.id'), nullable=False)
    erstellt_am = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    erreicht_bis = db.Column(db.Date)
    fortschritte = db.relationship('LernzielFortschritt', backref='lernziel', lazy=True)

class LernzielFortschritt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lernziel_id = db.Column(db.Integer, db.ForeignKey('lernziel.id'), nullable=False)
    schueler_id = db.Column(db.Integer, db.ForeignKey('schueler.id'), nullable=False)
    fortschritt = db.Column(db.Integer, default=0)  # 0-100%
    kommentar = db.Column(db.Text)
    aktualisiert_am = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schueler_id = db.Column(db.Integer, db.ForeignKey('schueler.id'), nullable=False)
    titel = db.Column(db.String(200), nullable=False)
    beschreibung = db.Column(db.Text)
    fach_id = db.Column(db.Integer, db.ForeignKey('fach.id'))
    datei_pfad = db.Column(db.String(255))
    typ = db.Column(db.String(50))  # 'projekt', 'arbeit', 'referat', etc.
    erstellt_am = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    oeffentlich = db.Column(db.Boolean, default=False)

class Verhaltensbewertung(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schueler_id = db.Column(db.Integer, db.ForeignKey('schueler.id'), nullable=False)
    lehrer_id = db.Column(db.Integer, db.ForeignKey('lehrer.id'), nullable=False)
    datum = db.Column(db.Date, nullable=False)
    kategorie = db.Column(db.String(50), nullable=False)  # 'positiv', 'neutral', 'negativ'
    beschreibung = db.Column(db.Text, nullable=False)
    massnahme = db.Column(db.Text)
    erstellt_am = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Benachrichtigung(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    empfaenger_typ = db.Column(db.String(20), nullable=False)  # 'lehrer', 'eltern', 'schueler'
    empfaenger_id = db.Column(db.Integer, nullable=False)
    typ = db.Column(db.String(50), nullable=False)  # 'note_neu', 'fehlzeit', 'hausaufgabe', etc.
    titel = db.Column(db.String(200), nullable=False)
    inhalt = db.Column(db.Text, nullable=False)
    erstellt_am = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    gelesen_am = db.Column(db.DateTime)
    ist_gelesen = db.Column(db.Boolean, default=False)
    
class Eltern(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vorname = db.Column(db.String(50), nullable=False)
    nachname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    telefon = db.Column(db.String(20))
    adresse = db.Column(db.Text)
    kinder = db.relationship('Schueler', backref='eltern', lazy=True)

class Pruefung(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titel = db.Column(db.String(200), nullable=False)
    fach_id = db.Column(db.Integer, db.ForeignKey('fach.id'), nullable=False)
    klasse_id = db.Column(db.Integer, db.ForeignKey('klasse.id'), nullable=False)
    lehrer_id = db.Column(db.Integer, db.ForeignKey('lehrer.id'), nullable=False)
    datum = db.Column(db.Date, nullable=False)
    dauer_minuten = db.Column(db.Integer, default=45)
    max_punkte = db.Column(db.Integer)
    themen = db.Column(db.Text)
    erstellt_am = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    ergebnisse = db.relationship('PruefungsErgebnis', backref='pruefung', lazy=True)

class PruefungsErgebnis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pruefung_id = db.Column(db.Integer, db.ForeignKey('pruefung.id'), nullable=False)
    schueler_id = db.Column(db.Integer, db.ForeignKey('schueler.id'), nullable=False)
    punkte = db.Column(db.Integer)
    note = db.Column(db.Float)
    kommentar = db.Column(db.Text)
    erstellt_am = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# Admin Dashboard
# Daten-Updates verwalten
DATA_FILE = "updates.json"
data_storage = []


def save_updates():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data_storage, f)

def load_updates():
    global data_storage
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data_storage = json.load(f)
    except FileNotFoundError:
        data_storage = []
        save_updates()

# Datenbank initialisieren
with app.app_context():
    db.create_all()

load_updates()

@app.context_processor
def inject_today():
    return {'today': datetime.date.today()}

@app.route('/')
def index():
    date_str = request.args.get('date')
    try:
        today = datetime.datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.date.today()
    except ValueError:
        today = datetime.date.today()

    # prayer_times import
    from prayer_times import prayer_times
    prayer_times_data = prayer_times.get_for_date(today)
    now = datetime.datetime.now()
    
    # Posts laden
    latest_posts = BlogPost.query.order_by(BlogPost.timestamp.desc()).all()
    total_posts = len(latest_posts)
    posts_per_slide = 3  # Oder passe diesen Wert an deine Anforderungen an

    # Events laden
    upcoming_events = Event.query.filter(
        Event.event_date >= datetime.datetime.utcnow(),
        Event.is_active == True
    ).order_by(Event.event_date.asc()).limit(5).all()

    # Header-Bilder laden
    header_dir = os.path.join(app.static_folder, 'Uploads', 'header')
    header_images = []
    if os.path.exists(header_dir):
        for file in os.listdir(header_dir):
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
                header_images.append(f'uploads/header/{file}')

    return render_template("index.html", 
                           prayer_times=prayer_times_data,
                           today=today,
                           now=now,
                           latest_posts=latest_posts,
                           upcoming_events=upcoming_events,
                           header_images=header_images,
                           total_posts=total_posts,
                           posts_per_slide=posts_per_slide)


@app.route('/blog')
def blog():
    posts = BlogPost.query.order_by(BlogPost.timestamp.desc()).all()
    upcoming_events = Event.query.filter(
        Event.event_date >= datetime.datetime.utcnow(),
        Event.is_active == True
    ).order_by(Event.event_date.asc()).all()
    return render_template(
        'aktuelles.html',
        blog_posts=posts,
        updates=data_storage,
        upcoming_events=upcoming_events
    )

@app.route('/blog/<int:post_id>', methods=['GET', 'POST'])
def blog_post(post_id):
    post = BlogPost.query.get_or_404(post_id)
    if request.method == 'POST':
        kommentar = request.form.get('kommentar', '').strip()
        if kommentar:
            k = Kommentar(blog_id=post.id, text=kommentar)
            db.session.add(k)
            db.session.commit()
    return render_template('blog_detail.html', post=post)

@app.route('/aktuelles', methods=['GET', 'POST'])
def aktuelles():
    if request.method == 'POST':
        if not session.get('admin'):
            abort(403)
        content = request.form.get('content', '').strip()
        if content:
            post = AktuellesPost(content=content)
            db.session.add(post)
            db.session.commit()
        return redirect(url_for('aktuelles'))

    blog_posts = BlogPost.query.order_by(BlogPost.timestamp.desc()).all()
    upcoming_events = Event.query.filter(
        Event.event_date >= datetime.datetime.utcnow(),
        Event.is_active == True
    ).order_by(Event.event_date.asc()).limit(5).all()

    return render_template('aktuelles.html', blog_posts=blog_posts, upcoming_events=upcoming_events)

@app.route('/aktuelles/<int:post_id>/kommentar', methods=['POST'])
def aktuelles_kommentar(post_id):
    post = AktuellesPost.query.get_or_404(post_id)
    text = request.form.get('kommentar', '').strip()
    if text:
        kommentar = AktuellesKommentar(post_id=post.id, text=text)
        db.session.add(kommentar)
        db.session.commit()
    return redirect(url_for('aktuelles'))

@app.route('/aktuelles/loeschen/<int:post_id>', methods=['POST'])
def aktuelles_loeschen(post_id):
    if not session.get('admin'):
        abort(403)
    post = AktuellesPost.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('aktuelles'))

@app.route('/admin/blog/neu', methods=['GET', 'POST'])
def blog_new_post():
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        image = request.files.get('image')
        filename = None
        if image and image.filename:
            filename = secure_filename(image.filename)
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], 'blog')
            os.makedirs(upload_path, exist_ok=True)
            image.save(os.path.join(upload_path, filename))
        new_post = BlogPost(title=title, content=content, image=filename)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('blog'))
    return render_template('create_post.html')

@app.route('/admin/blog/bearbeiten/<int:post_id>', methods=['GET', 'POST'])
def blog_edit_post(post_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    post = BlogPost.query.get_or_404(post_id)
    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']
        db.session.commit()
        return redirect(url_for('blog'))
    return render_template('edit_post.html', post=post)

@app.route('/admin/blog/loeschen/<int:post_id>', methods=['POST'])
def blog_delete_post(post_id):
    if not session.get('admin'):
        abort(403)
    post = BlogPost.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('blog'))

@app.route('/admin/kommentar/loeschen/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    if not session.get('admin'):
        abort(403)
    comment = Kommentar.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    return redirect(request.referrer or url_for('blog'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    recent_posts = BlogPost.query.order_by(BlogPost.timestamp.desc()).limit(5).all()
    recent_ahde_vefa = ahde_vefa.query.order_by(ahde_vefa.id.desc()).limit(5).all()
    blog_count = BlogPost.query.count()
    ahde_vefa_count = ahde_vefa.query.count()
    alben_count = GalerieAlbum.query.count()
    unread_messages = AdminMessage.query.filter_by(is_read=False).count()
    upcoming_events = Event.query.filter(
        Event.event_date >= datetime.datetime.utcnow(),
        Event.is_active == True
    ).count()
    cost_center_count = CostCenter.query.count()

    return render_template('admin_dashboard.html', 
                           recent_posts=recent_posts,
                           recent_ahde_vefa=recent_ahde_vefa,
                           blog_count=blog_count,
                           ahde_vefa_count=ahde_vefa_count,
                           alben_count=alben_count,
                           unread_messages=unread_messages,
                           upcoming_events=upcoming_events,
                           cost_center_count=cost_center_count)

@app.route('/admin/login', methods=['GET', 'POST'])
def blog_admin_login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template('admin_login_new.html', fehler='Falsche Zugangsdaten')
    return render_template('admin_login_new.html')

@app.route('/admin/logout')
def blog_admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/gemeinde')
def gemeinde():
    return render_template('gemeinde.html')

@app.route('/statistik')
def statistik():
    eintraege = ahde_vefa.query.all()
    statistik = defaultdict(lambda: {'geburten': 0, 'tode': 0})
    for eintrag in eintraege:
        if eintrag.birth_date:
            try:
                jahr = int(eintrag.birth_date[:4])
                statistik[jahr]['geburten'] += 1
            except:
                pass
        if eintrag.death_date:
            try:
                jahr = int(eintrag.death_date[:4])
                statistik[jahr]['tode'] += 1
            except:
                pass
    jahre = sorted(statistik.keys())
    geburten = [statistik[jahr]['geburten'] for jahr in jahre]
    tode = [statistik[jahr]['tode'] for jahr in jahre]
    return render_template("statistik.html", jahre=jahre, geburten=geburten, tode=tode)

@app.route('/download-statistik-pdf')
def download_statistik_pdf():
    eintraege = ahde_vefa.query.all()
    
    # Daten sammeln
    daten = {
        'Geburtsjahr': [], 'Todesjahr': [], 'Alter': [],
        'Sterbemonat': [], 'Geburtsmonat': []
    }
    
    for eintrag in eintraege:
        if eintrag.birth_date and eintrag.death_date:
            try:
                birth_date = datetime.datetime.strptime(eintrag.birth_date, "%Y-%m-%d")
                death_date = datetime.datetime.strptime(eintrag.death_date, "%Y-%m-%d")
                age = (death_date - birth_date).days / 365.25
                
                daten['Geburtsjahr'].append(birth_date.year)
                daten['Todesjahr'].append(death_date.year)
                daten['Alter'].append(age)
                daten['Sterbemonat'].append(death_date.strftime("%B"))
                daten['Geburtsmonat'].append(birth_date.strftime("%B"))
            except:
                continue
    
    df = pd.DataFrame(daten)
    
    # Monatsreihenfolge für Sortierung
    monatsordnung = ['January', 'February', 'March', 'April', 'May', 'June', 
                    'July', 'August', 'September', 'October', 'November', 'December']
    
    # PDF erstellen
    buf = BytesIO()
    
    try:
        with PdfPages(buf) as pdf:
            # Logo laden mit Fallback wenn nicht vorhanden
            logo = None
            try:
                logo_path = os.path.join(current_app.root_path, 'static', 'logo.png')
                if os.path.exists(logo_path):
                    logo = plt.imread(logo_path)
            except:
                pass

            # Erste Seite mit 3 großen Diagrammen
            fig1 = plt.figure(figsize=(15, 18))
            gs = fig1.add_gridspec(4, 1, height_ratios=[0.6, 2, 1, 1])
            
            # Kopfzeile mit Logo, Titel und Quran-Zitat
            ax_header = fig1.add_subplot(gs[0])
            ax_header.axis('off')
            
            if logo is not None:
                ax_header.imshow(logo, aspect='auto', extent=[0.05, 0.15, 0.2, 0.8])
            
            # Titelseite als eigene Seite
            fig_title = plt.figure(figsize=(15, 18))
            ax_title = fig_title.add_subplot(111)
            ax_title.axis('off')
            
            # Logo laden (bereits oben gemacht, wird weiterverwendet)
            if logo is not None:
                ax_title.imshow(logo, aspect='auto', extent=[0.05, 0.15, 0.2, 0.8])
            
            # Titeltext mit Zitat und Moschee
            titeltext = ('Statistische Auswertung der Sterbedaten\n'
                         'Ditib Fatih Moschee Salzgitter-Bad\n\n'
                         '"Kullu nafsin zaikatul maut" – "Jede Seele wird den Tod schmecken"\n'
                         '"Her canlı Ölümü tadacaktır" (Sure Al-Imran 3:185)')
            
            # Mittig zentrierter Text
            ax_title.text(0.5, 0.6, titeltext, ha='center', va='center', fontsize=14, fontweight='bold', linespacing=1.8)
            ax_title.text(0.5, 0.4, f'Erstellt am: {datetime.datetime.now().strftime("%d.%m.%Y %H:%M")}', ha='center', fontsize=12)
            
            # Fußzeile
            fig_title.text(0.5, 0.02, f'Ditib Fatih Moschee Salzgitter-Bad - Generiert am {datetime.datetime.now().strftime("%d.%m.%Y")}',
                           ha='center', va='bottom', fontsize=10)
            
            # Titelseite speichern
            pdf.savefig(fig_title, bbox_inches='tight')
            plt.close(fig_title)
            
            
            
            ax_header.text(0.5, 0.2, f'Erstellt am: {datetime.datetime.now().strftime("%d.%m.%Y %H:%M")}', 
                         ha='center', va='center', fontsize=10)

            # 1. Großes Diagramm: Zeitliche Verteilung
            ax1 = fig1.add_subplot(gs[1])
            sns.histplot(df['Geburtsjahr'], bins=50, color='blue', alpha=0.6, label='Geburten', ax=ax1)
            sns.histplot(df['Todesjahr'], bins=50, color='red', alpha=0.6, label='Todesfälle', ax=ax1)
            ax1.set_title('Verteilung von Geburten und Todesfällen über die Zeit', pad=15)
            ax1.set_xlabel('Jahr')
            ax1.set_ylabel('Anzahl')
            ax1.legend()
            
            # 2. Diagramm: Altersverteilung
            ax2 = fig1.add_subplot(gs[2])
            sns.histplot(df['Alter'], bins=30, kde=True, color='purple', ax=ax2)
            ax2.set_title('Altersverteilung der Verstorbenen', pad=15)
            ax2.set_xlabel('Alter bei Tod')
            
            # 3. Diagramm: Erweiterte statistische Kennzahlen
            ax3 = fig1.add_subplot(gs[3])
            ax3.axis('off')
            
            # Zusätzliche Kennzahlen berechnen
            stats_data = [
                ["Anzahl Datensätze", f"{len(df):,}"],
                ["Jüngster Verstorbener", f"{df['Alter'].min():.1f} Jahre"],
                ["Ältester Verstorbener", f"{df['Alter'].max():.1f} Jahre"],
                ["Durchschnittsalter", f"{df['Alter'].mean():.1f} Jahre"],
                ["Medianalter", f"{df['Alter'].median():.1f} Jahre"],
                ["Standardabweichung", f"{df['Alter'].std():.1f} Jahre"],
                ["Erste Quartil (Q1)", f"{df['Alter'].quantile(0.25):.1f} Jahre"],
                ["Dritte Quartil (Q3)", f"{df['Alter'].quantile(0.75):.1f} Jahre"]
            ]
            
            # Tabelle mit erweiterten Kennzahlen
            table = ax3.table(cellText=stats_data,
                            colLabels=["Kennzahl", "Wert"],
                            loc='center',
                            cellLoc='center',
                            bbox=[0.1, 0.1, 0.8, 0.8])
            
            table.auto_set_font_size(False)
            table.set_fontsize(11)
            table.scale(1.2, 1.8)
            
            # Fußzeile
            fig1.text(0.5, 0.02, f'Ditib Fatih Moschee Salzgitter-Bad - Generiert am {datetime.datetime.now().strftime("%d.%m.%Y")}', 
                    ha='center', va='bottom', fontsize=9)
            
            fig1.tight_layout()
            pdf.savefig(fig1, bbox_inches='tight')
            plt.close(fig1)
            
            # Zweite Seite mit weiteren Diagrammen
            fig2 = plt.figure(figsize=(15, 15))
            
            # Kopfzeile mit Quran-Zitat
            fig2.text(0.5, 0.97, 'Detaillierte Statistiken\n', 
                     ha='center', va='center', fontsize=14, fontweight='bold',
                     linespacing=1.5)
            
            # 1. Saisonale Verteilung der Todesfälle
            ax1 = plt.subplot(2, 2, 1)
            monat_count = df['Sterbemonat'].value_counts().reindex(monatsordnung)
            sns.barplot(x=monat_count.index, y=monat_count.values, palette='Reds', ax=ax1)
            ax1.set_title('Todesfälle nach Monat', pad=15)
            ax1.set_xlabel('Monat')
            ax1.set_ylabel('Anzahl')
            ax1.tick_params(axis='x', rotation=45)
            
            # 2. Saisonale Verteilung der Geburten
            ax2 = plt.subplot(2, 2, 2)
            monat_count = df['Geburtsmonat'].value_counts().reindex(monatsordnung)
            sns.barplot(x=monat_count.index, y=monat_count.values, palette='Blues', ax=ax2)
            ax2.set_title('Geburten nach Monat', pad=15)
            ax2.set_xlabel('Monat')
            ax2.set_ylabel('Anzahl')
            ax2.tick_params(axis='x', rotation=45)
            
            # 3. Lebenserwartung über die Zeit
            ax3 = plt.subplot(2, 2, 3)
            sns.regplot(x='Todesjahr', y='Alter', data=df, 
                       scatter_kws={'alpha':0.3, 'color':'gray'},
                       line_kws={'color':'red'}, ax=ax3)
            ax3.set_title('Entwicklung der Lebenserwartung', pad=15)
            ax3.set_xlabel('Todesjahr')
            ax3.set_ylabel('Alter bei Tod')
            
            # 4. Lebensspanne Visualisierung
            ax4 = plt.subplot(2, 2, 4)
            sample = df.sample(min(100, len(df)))
            for i, (_, row) in enumerate(sample.iterrows()):
                ax4.plot([row['Geburtsjahr'], row['Todesjahr']], [i, i], 
                        color=plt.cm.viridis(row['Alter']/df['Alter'].max()))
            
            norm = plt.Normalize(vmin=df['Alter'].min(), vmax=df['Alter'].max())
            sm = plt.cm.ScalarMappable(cmap='viridis', norm=norm)
            sm.set_array([])
            fig2.colorbar(sm, ax=ax4, label='Alter bei Tod')
            ax4.set_title('Lebensspanne (Sample von 100 Personen)', pad=15)
            ax4.set_xlabel('Jahr')
            ax4.set_ylabel('Individuen')
            
            # Fußzeile
            fig2.text(0.5, 0.02, f'Ditib Fatih Moschee Salzgitter-Bad - Generiert am {datetime.datetime.now().strftime("%d.%m.%Y")}', 
                     ha='center', va='bottom', fontsize=9)
            
            fig2.tight_layout()
            pdf.savefig(fig2, bbox_inches='tight')
            plt.close(fig2)
            
    except Exception as e:
        plt.close('all')
        raise e
    
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="Sterbestatistik_Ditib_Fatih.pdf", mimetype='application/pdf')

@app.route('/galarie')
def galarie():
    alben = GalerieAlbum.query.order_by(GalerieAlbum.erstellungsdatum.desc()).all()
    einzelbilder = GalerieBild.query.filter(GalerieBild.album_id == None).order_by(GalerieBild.upload_datum.desc()).all()
    return render_template("galarie.html", alben=alben, einzelbilder=einzelbilder)

@app.route('/galarie/album/<int:album_id>')
def galarie_album(album_id):
    album = GalerieAlbum.query.get_or_404(album_id)
    bilder = GalerieBild.query.filter_by(album_id=album_id).order_by(GalerieBild.upload_datum.desc()).all()
    return render_template("galarie_album.html", album=album, bilder=bilder)

@app.route('/admin/galerie')
def admin_galerie():
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    alben = GalerieAlbum.query.order_by(GalerieAlbum.erstellungsdatum.desc()).all()
    einzelbilder = GalerieBild.query.filter(GalerieBild.album_id == None).order_by(GalerieBild.upload_datum.desc()).all()
    return render_template("admin_galerie.html", alben=alben, einzelbilder=einzelbilder)

@app.route('/admin/galerie/album_erstellen', methods=['POST'])
def admin_galerie_album_erstellen():
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    name = request.form.get('album_name', '').strip()
    beschreibung = request.form.get('album_beschreibung', '').strip()
    if name:
        album = GalerieAlbum(name=name, beschreibung=beschreibung)
        db.session.add(album)
        db.session.commit()
        flash('Album erfolgreich erstellt!', 'success')
    else:
        flash('Bitte geben Sie einen Namen für das Album ein.', 'danger')
    return redirect(url_for('admin_galerie'))

@app.route('/admin/galerie/album/<int:album_id>')
def admin_galerie_album(album_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    album = GalerieAlbum.query.get_or_404(album_id)
    bilder = GalerieBild.query.filter_by(album_id=album_id).order_by(GalerieBild.upload_datum.desc()).all()
    return render_template('admin_galerie_album.html', album=album, bilder=bilder)

@app.template_filter('nl2br')
def nl2br_filter(s):
    return s.replace('\n', '<br>\n') if s else ''

@app.route('/admin/galerie/album/bearbeiten/<int:album_id>', methods=['GET', 'POST'])
def admin_galerie_album_bearbeiten(album_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    album = GalerieAlbum.query.get_or_404(album_id)
    if request.method == 'POST':
        name = request.form.get('album_name', '').strip()
        beschreibung = request.form.get('album_beschreibung', '').strip()
        if name:
            album.name = name
            album.beschreibung = beschreibung
            db.session.commit()
            flash('Album erfolgreich aktualisiert!', 'success')
            return redirect(url_for('admin_galerie'))
        else:
            flash('Bitte geben Sie einen Namen für das Album ein.', 'danger')
    return render_template('admin_galerie_album_bearbeiten.html', album=album)

@app.route('/admin/galerie/album/loeschen/<int:album_id>', methods=['POST'])
def admin_galerie_album_loeschen(album_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    album = GalerieAlbum.query.get_or_404(album_id)
    for bild in album.bilder:
        try:
            bildpfad = os.path.join(app.config['UPLOAD_FOLDER'], 'galerie', bild.dateiname)
            if os.path.exists(bildpfad):
                os.remove(bildpfad)
        except Exception as e:
            app.logger.error(f"Fehler beim Löschen der Bilddatei: {e}")
    db.session.delete(album)
    db.session.commit()
    flash('Album und alle dazugehörigen Bilder wurden gelöscht!', 'success')
    return redirect(url_for('admin_galerie'))

@app.route('/admin/galerie/bild/upload', methods=['POST'])
def admin_galerie_bild_upload():
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    album_id = request.form.get('album_id')
    album = None
    if album_id:
        album = GalerieAlbum.query.get_or_404(album_id)
    if 'bilder' not in request.files:
        flash('Keine Bilddateien ausgewählt.', 'danger')
        return redirect(url_for('admin_galerie'))
    bilder = request.files.getlist('bilder')
    titel = request.form.get('titel', '').strip()
    beschreibung = request.form.get('beschreibung', '').strip()
    upload_pfad = os.path.join(app.config['UPLOAD_FOLDER'], 'galerie')
    os.makedirs(upload_pfad, exist_ok=True)
    anzahl_uploads = 0
    for bild in bilder:
        if bild and bild.filename:
            dateiname = secure_filename(bild.filename)
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            dateiname = f"{timestamp}_{dateiname}"
            bild.save(os.path.join(upload_pfad, dateiname))
            db_bild = GalerieBild(
                album_id=album.id if album else None,
                dateiname=dateiname,
                titel=titel or os.path.splitext(bild.filename)[0],
                beschreibung=beschreibung
            )
            db.session.add(db_bild)
            anzahl_uploads += 1
    if anzahl_uploads > 0:
        db.session.commit()
        flash(f'{anzahl_uploads} Bilder erfolgreich hochgeladen!', 'success')
    else:
        flash('Keine gültigen Bilder zum Hochladen gefunden.', 'warning')
    if album:
        return redirect(url_for('admin_galerie_album', album_id=album.id))
    else:
        return redirect(url_for('admin_galerie'))

@app.route('/admin/galerie/bild/loeschen/<int:bild_id>', methods=['POST'])
def admin_galerie_bild_loeschen(bild_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    bild = GalerieBild.query.get_or_404(bild_id)
    album_id = bild.album_id
    try:
        bildpfad = os.path.join(app.config['UPLOAD_FOLDER'], 'galerie', bild.dateiname)
        if os.path.exists(bildpfad):
            os.remove(bildpfad)
    except Exception as e:
        app.logger.error(f"Fehler beim Löschen der Bilddatei: {e}")
    db.session.delete(bild)
    db.session.commit()
    flash('Bild erfolgreich gelöscht!', 'success')
    return redirect(url_for('admin_galerie_album', album_id=album_id))

@app.route('/islam')
def islam():
    return render_template("islam.html")

@app.route('/kontakt', methods=['GET', 'POST'])
def kontakt():
    message_sent = False
    errors = {}
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', 'Kein Betreff').strip()
        message = request.form.get('message', '').strip()
        if not name:
            errors['name'] = 'Bitte geben Sie Ihren Namen ein.'
        if not email:
            errors['email'] = 'Bitte geben Sie Ihre E-Mail-Adresse ein.'
        elif '@' not in email or '.' not in email:
            errors['email'] = 'Bitte geben Sie eine gültige E-Mail-Adresse ein.'
        if not message:
            errors['message'] = 'Bitte geben Sie eine Nachricht ein.'
        if not errors:
            new_message = AdminMessage(
                sender_name=name,
                sender_email=email,
                subject=subject,
                message=message
            )
            db.session.add(new_message)
            db.session.commit()
            message_sent = True
    return render_template("kontakt.html", message_sent=message_sent, errors=errors)

@app.route('/impressum')
def impressum():
    return render_template("impressum.html")

@app.route('/datenschutz')
def datenschutz():
    return render_template("datenschutz.html")

# prayer_times import
from prayer_times import prayer_times

@app.route('/api/prayer-times', methods=['GET'])
def api_prayer_times():
    date_str = request.args.get('date')
    try:
        if date_str:
            date_parts = date_str.split('-')
            date = datetime.date(int(date_parts[0]), int(date_parts[1]), int(date_parts[2]))
        else:
            date = datetime.date.today()
        prayer_times_data = prayer_times.get_for_date(date)
        return jsonify(prayer_times_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/gb.txt')
def serve_gb_file():
    return send_file(os.path.join(app.static_folder, 'gb.txt'))

@app.route('/bearbeite_eintrag/<int:eintrag_id>', methods=['GET', 'POST'])
def bearbeite_eintrag(eintrag_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    eintrag = ahde_vefa.query.get_or_404(eintrag_id)
    if request.method == 'POST':
        if request.form.get('aktion') == 'bearbeiten':
            eintrag.name = request.form['name']
            eintrag.birth_date = request.form['birth_date']
            eintrag.death_date = request.form['death_date']
            image = request.files.get('image')
            if image and image.filename:
                filename = secure_filename(image.filename)
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                image.save(upload_path)
                eintrag.image_filename = filename
            db.session.commit()
            return redirect(url_for('admin_ahde_vefa'))
        elif request.form.get('aktion') == 'loeschen':
            db.session.delete(eintrag)
            db.session.commit()
            return redirect(url_for('admin_ahde_vefa'))
    return render_template('bearbeite_eintrag.html', eintrag=eintrag)

@app.route('/ahde-vefa', methods=['GET', 'POST'])
def ahde_vefa_view():
    if request.method == 'POST' and session.get('admin'):
        name = request.form['name']
        birth_date = request.form['birth_date']
        death_date = request.form['death_date']
        image = request.files['image']
        filename = None
        if image and image.filename:
            filename = secure_filename(image.filename)
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            image.save(upload_path)
        eintrag = ahde_vefa(name=name, birth_date=birth_date, death_date=death_date, image_filename=filename)
        db.session.add(eintrag)
        db.session.commit()

    search_name = request.args.get('search_name')
    search_death = request.args.get('search_death')
    query = ahde_vefa.query
    if search_name:
        query = query.filter(ahde_vefa.name.contains(search_name))
    if search_death:
        query = query.filter(ahde_vefa.death_date == search_death)
    eintraege = query.all()

    statistik = defaultdict(float)
    for eintrag in eintraege:
        if eintrag.birth_date:
            try:
                jahr = int(eintrag.birth_date.split("-")[0])
                statistik[jahr] += 1
            except:
                pass

    show_form = session.get('admin', False)
    return render_template('ahde_vefa.html', eintraege=eintraege, statistik=dict(statistik), show_form=show_form)

@app.route('/admin/ahde-vefa')
def admin_ahde_vefa():
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    eintraege = ahde_vefa.query.order_by(ahde_vefa.name).all()
    return render_template('admin_ahde_vefa.html', eintraege=eintraege)

@app.route('/admin/nachrichten')
def admin_nachrichten():
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    nachrichten = AdminMessage.query.order_by(AdminMessage.received_at.desc()).all()
    return render_template('admin_nachrichten.html', nachrichten=nachrichten)

@app.route('/admin/nachrichten/<int:message_id>')
def admin_nachricht_detail(message_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    nachricht = AdminMessage.query.get_or_404(message_id)
    if not nachricht.is_read:
        nachricht.is_read = True
        db.session.commit()
    return render_template('admin_nachricht_detail.html', nachricht=nachricht)

@app.route('/admin/nachrichten/<int:message_id>/antworten', methods=['POST'])
def admin_nachricht_antworten(message_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    nachricht = AdminMessage.query.get_or_404(message_id)
    antwort = request.form.get('antwort', '').strip()
    if antwort:
        nachricht.admin_response = antwort
        nachricht.response_date = datetime.datetime.utcnow()
        db.session.commit()
        flash('Antwort erfolgreich gespeichert!', 'success')
    return redirect(url_for('admin_nachricht_detail', message_id=message_id))

@app.route('/admin/nachrichten/<int:message_id>/pdf')
def admin_nachricht_pdf(message_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    nachricht = AdminMessage.query.get_or_404(message_id)
    pdf_html = f"""
    <h2>Nachricht von {nachricht.sender_name}</h2>
    <p><strong>Email:</strong> {nachricht.sender_email}</p>
    <p><strong>Betreff:</strong> {nachricht.subject}</p>
    <p><strong>Datum:</strong> {nachricht.received_at.strftime('%d.%m.%Y %H:%M')}</p>
    <h3>Nachricht:</h3>
    <p>{nachricht.message}</p>
    """
    if nachricht.admin_response:
        pdf_html += f"""
        <hr>
        <h3>Admin Antwort ({nachricht.response_date.strftime('%d.%m.%Y %H:%M')}):</h3>
        <p>{nachricht.admin_response}</p>
        """
    return render_template('admin_nachricht_pdf.html', nachricht=nachricht, pdf_content=pdf_html)

@app.route('/admin/veranstaltungen')
def admin_veranstaltungen():
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    aktuelle_veranstaltungen = Event.query.filter(
        Event.event_date >= datetime.datetime.utcnow(),
        Event.is_active == True
    ).order_by(Event.event_date.asc()).all()

    vergangene_veranstaltungen = Event.query.filter(
        Event.event_date < datetime.datetime.utcnow()
    ).order_by(Event.event_date.desc()).limit(10).all()

    return render_template('admin_veranstaltungen.html', 
                           aktuelle_veranstaltungen=aktuelle_veranstaltungen,
                           vergangene_veranstaltungen=vergangene_veranstaltungen)

@app.route('/admin/veranstaltung_neu', methods=['GET', 'POST'])
def admin_veranstaltung_neu():
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        event_date_str = request.form.get('event_date')
        event_time = request.form.get('event_time', '').strip()
        location = request.form.get('location', '').strip()
        is_recurring = 'is_recurring' in request.form
        recurrence_type = request.form.get('recurrence_type', '').strip()
        if title and event_date_str:
            try:
                event_datetime = datetime.datetime.strptime(event_date_str, '%Y-%m-%d')
                veranstaltung = Event(
                    title=title,
                    description=description,
                    event_date=event_datetime,
                    event_time=event_time,
                    location=location,
                    is_recurring=is_recurring,
                    recurrence_type=recurrence_type if is_recurring else None
                )
                db.session.add(veranstaltung)
                db.session.commit()
                flash('Veranstaltung erfolgreich erstellt!', 'success')
                return redirect(url_for('admin_veranstaltungen'))
            except ValueError:
                flash('Ungültiges Datum format!', 'danger')
        else:
            flash('Titel und Datum sind erforderlich!', 'danger')
    return render_template('admin_veranstaltung_neu.html')

@app.route('/admin/veranstaltungen/<int:event_id>/bearbeiten', methods=['GET', 'POST'])
def admin_veranstaltung_bearbeiten(event_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    veranstaltung = Event.query.get_or_404(event_id)
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        event_date_str = request.form.get('event_date')
        event_time = request.form.get('event_time', '').strip()
        location = request.form.get('location', '').strip()
        is_recurring = 'is_recurring' in request.form
        recurrence_type = request.form.get('recurrence_type', '').strip()
        if title and event_date_str:
            try:
                event_datetime = datetime.datetime.strptime(event_date_str, '%Y-%m-%d')
                veranstaltung.title = title
                veranstaltung.description = description
                veranstaltung.event_date = event_datetime
                veranstaltung.event_time = event_time
                veranstaltung.location = location
                veranstaltung.is_recurring = is_recurring
                veranstaltung.recurrence_type = recurrence_type if is_recurring else None
                db.session.commit()
                flash('Veranstaltung erfolgreich aktualisiert!', 'success')
                return redirect(url_for('admin_veranstaltungen'))
            except ValueError:
                flash('Ungültiges Datum format!', 'danger')
        else:
            flash('Titel und Datum sind erforderlich!', 'danger')
    return render_template('admin_veranstaltung_bearbeiten.html', veranstaltung=veranstaltung)

@app.route('/admin/veranstaltungen/<int:event_id>/loeschen', methods=['POST'])
def admin_veranstaltung_loeschen(event_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    veranstaltung = Event.query.get_or_404(event_id)
    db.session.delete(veranstaltung)
    db.session.commit()
    flash('Veranstaltung gelöscht!', 'success')
    return redirect(url_for('admin_veranstaltungen'))

@app.route('/veranstaltungen')
def veranstaltungen():
    upcoming_events = Event.query.filter(
        Event.event_date >= datetime.datetime.utcnow(),
        Event.is_active == True
    ).order_by(Event.event_date.asc()).all()
    return render_template('veranstaltungen.html', veranstaltungen=upcoming_events)

@app.route('/admin/kontakt/nachrichten', methods=['POST'])
def admin_kontakt_nachricht():
    sender_name = request.form.get('name', '').strip()
    sender_email = request.form.get('email', '').strip()
    subject = request.form.get('subject', '').strip()
    message = request.form.get('message', '').strip()
    if sender_name and sender_email and subject and message:
        admin_message = AdminMessage(
            sender_name=sender_name,
            sender_email=sender_email,
            subject=subject,
            message=message
        )
        db.session.add(admin_message)
        db.session.commit()
        flash('Ihre Nachricht wurde erfolgreich gesendet! Wir melden uns bald.', 'success')
    else:
        flash('Bitte füllen Sie alle Felder aus.', 'danger')
    return redirect(request.referrer or url_for('index'))

# Neue Routen für Kostenstellen und Vorgänge

@app.route('/admin/cost_centers/<int:cost_center_id>/processes.json', methods=['GET'])
def get_processes_for_cost_center(cost_center_id):
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        cost_center = CostCenter.query.get(cost_center_id)
        if not cost_center:
            return jsonify({'error': 'Cost center not found'}), 404
        
        processes = Process.query.filter_by(cost_center_id=cost_center_id).order_by(Process.name).all()
        
        processes_data = []
        for process in processes:
            processes_data.append({
                'id': process.id,
                'name': process.name,
                'description': process.description or '',
                'created_at': process.created_at.strftime('%Y-%m-%d %H:%M:%S') if process.created_at else None
            })
        
        return jsonify({'processes': processes_data})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/cost_centers/<int:cost_center_id>/edit', methods=['GET', 'POST'])
def admin_cost_center_edit(cost_center_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    cost_center = CostCenter.query.get_or_404(cost_center_id)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        if not name:
            flash('Name der Kostenstelle ist erforderlich.', 'danger')
        else:
            cost_center.name = name
            cost_center.description = description
            db.session.commit()
            flash('Kostenstelle erfolgreich aktualisiert!', 'success')
            return redirect(url_for('admin_cost_centers'))
    return render_template('admin_cost_center_edit.html', cost_center=cost_center)

@app.route('/admin/cost_centers/<int:cost_center_id>/delete', methods=['POST'])
def admin_cost_center_delete(cost_center_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    cost_center = CostCenter.query.get_or_404(cost_center_id)
    db.session.delete(cost_center)
    db.session.commit()
    flash('Kostenstelle erfolgreich gelöscht!', 'success')
    return redirect(url_for('admin_cost_centers'))

@app.route('/admin/cost_centers/<int:cost_center_id>/processes', methods=['GET', 'POST'])
def admin_processes(cost_center_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    cost_center = CostCenter.query.get_or_404(cost_center_id)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        if not name:
            flash('Name des Vorgangs ist erforderlich.', 'danger')
        else:
            process = Process(cost_center_id=cost_center_id, name=name, description=description)
            db.session.add(process)
            db.session.commit()
            flash('Vorgang erfolgreich erstellt!', 'success')
            return redirect(url_for('admin_processes', cost_center_id=cost_center_id))
    
    processes = Process.query.filter_by(cost_center_id=cost_center_id).order_by(Process.created_at.desc()).all()
    return render_template('admin_processes.html', cost_center=cost_center, processes=processes)

@app.route('/admin/processes/<int:process_id>/edit', methods=['GET', 'POST'])
def admin_process_edit(process_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    process = Process.query.get_or_404(process_id)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        if not name:
            flash('Name des Vorgangs ist erforderlich.', 'danger')
        else:
            process.name = name
            process.description = description
            db.session.commit()
            flash('Vorgang erfolgreich aktualisiert!', 'success')
            return redirect(url_for('admin_processes', cost_center_id=process.cost_center_id))
    return render_template('admin_process_edit.html', process=process)

@app.route('/admin/processes/<int:process_id>/delete', methods=['POST'])
def admin_process_delete(process_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    process = Process.query.get_or_404(process_id)
    cost_center_id = process.cost_center_id
    db.session.delete(process)
    db.session.commit()
    flash('Vorgang erfolgreich gelöscht!', 'success')
    return redirect(url_for('admin_processes', cost_center_id=cost_center_id))

@app.route('/admin/finanzen', methods=['GET', 'POST'])
def admin_finanzen():
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))

    today_date = datetime.date.today().strftime('%Y-%m-%d')
    current_cost_center_id = None
    current_process_id = None

    # Load ALL cost centers and ALL processes for general use and forms
    # 'cost_centers' will be used by the "Neue Transaktion" form
    cost_centers = CostCenter.query.order_by(CostCenter.name).all()
    # 'all_processes' is the comprehensive list of all processes
    all_processes = Process.query.order_by(Process.name).all()

    if request.method == 'POST':
        aktion = request.form.get('aktion')

        if aktion == 'hinzufuegen_transaktion':
            description = request.form.get('description', '').strip()
            amount_str = request.form.get('amount', '').strip()
            transaction_type_ = request.form.get('type', '').strip()
            category = request.form.get('category', '').strip()
            date_str = request.form.get('date', '').strip()
            cost_center_id = request.form.get('cost_center_id')
            process_id = request.form.get('process_id')
            document = request.files.get('document')

            errors = []
            if not description:
                errors.append('Beschreibung ist erforderlich.')

            amount = None
            if transaction_type_ != 'note':
                try:
                    amount = float(amount_str)
                    if amount <= 0:
                        errors.append('Betrag muss größer als 0 sein für Einnahmen/Ausgaben.')
                except ValueError:
                    errors.append('Ungültiger Betrag.')

            if transaction_type_ not in ['Einnahme', 'Ausgabe', 'note']:
                errors.append('Ungültiger Transaktionstyp.')
            if not date_str:
                errors.append('Datum ist erforderlich.')

            # Validierung der Kostenstelle
            if cost_center_id:
                try:
                    cost_center_id = int(cost_center_id)
                    cost_center = CostCenter.query.get(cost_center_id)
                    if not cost_center:
                        errors.append('Ungültige Kostenstelle.')
                except (ValueError, TypeError):
                    errors.append('Ungültige Kostenstellen-ID.')
                    cost_center_id = None

            # Validierung des Vorgangs
            if process_id:
                try:
                    process_id = int(process_id)
                    process = Process.query.get(process_id)
                    if not process:
                        errors.append('Ungültiger Vorgang.')
                    elif cost_center_id and process.cost_center_id != cost_center_id:
                        errors.append('Der Vorgang gehört nicht zur ausgewählten Kostenstelle.')
                except (ValueError, TypeError):
                    errors.append('Ungültige Vorgangs-ID.')
                    process_id = None

            document_filename = None
            if document and document.filename:
                document_filename = secure_filename(document.filename)
                document_path = os.path.join(app.config['UPLOAD_FOLDER'], document_filename)
                document.save(document_path)

            if not errors:
                try:
                    date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                    transaction = Transaction(
                        description=description,
                        amount=amount,
                        type=transaction_type_,
                        category=category or None,
                        date=date,
                        cost_center_id=cost_center_id if cost_center_id else None,
                        process_id=process_id if process_id else None,
                        document_filename=document_filename
                    )
                    db.session.add(transaction)
                    db.session.commit()
                    flash('Transaktion erfolgreich hinzugefügt!', 'success')
                    return redirect(url_for('admin_finanzen'))
                except ValueError:
                    errors.append('Ungültiges Datumsformat.')

            for error in errors:
                flash(error, 'danger')

        elif aktion == 'loeschen_transaktion':
            transaction_id = request.form.get('transaction_id')
            transaction_to_delete = Transaction.query.get_or_404(transaction_id)
            if transaction_to_delete.document_filename:
                try:
                    # Ensure the UPLOAD_FOLDER exists and path is correct
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], transaction_to_delete.document_filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except OSError as e:
                    print(f"Error deleting file: {e}") # Log error for debugging
                    flash('Fehler beim Löschen der Datei.', 'warning')
            db.session.delete(transaction_to_delete)
            db.session.commit()
            flash('Transaktion erfolgreich gelöscht!', 'success')
            return redirect(url_for('admin_finanzen'))

        # Add logic for editing transaction, adding cost center, adding process here if they submit to this route
        # Based on your HTML, 'hinzufuegen_kostenstelle' and 'hinzufuegen_vorgang' forms also submit to this route
        elif aktion == 'hinzufuegen_kostenstelle':
            name = request.form.get('name')
            code = request.form.get('code')
            if name and code:
                new_cost_center = CostCenter(name=name, code=code)
                db.session.add(new_cost_center)
                db.session.commit()
                flash('Kostenstelle erfolgreich hinzugefügt!', 'success')
            else:
                flash('Name und Code der Kostenstelle sind erforderlich.', 'danger')
            return redirect(url_for('admin_finanzen')) # Or admin_cost_centers if that's the primary view

        elif aktion == 'hinzufuegen_vorgang':
            name = request.form.get('name')
            code = request.form.get('code')
            cost_center_id_for_process = request.form.get('cost_center_id')
            if name and code and cost_center_id_for_process:
                try:
                    cost_center_id_for_process = int(cost_center_id_for_process)
                    cost_center_obj = CostCenter.query.get(cost_center_id_for_process)
                    if cost_center_obj:
                        new_process = Process(name=name, code=code, cost_center_id=cost_center_id_for_process)
                        db.session.add(new_process)
                        db.session.commit()
                        flash('Vorgang erfolgreich hinzugefügt!', 'success')
                    else:
                        flash('Ungültige Kostenstelle für den Vorgang.', 'danger')
                except (ValueError, TypeError):
                    flash('Ungültige Kostenstellen-ID für den Vorgang.', 'danger')
            else:
                flash('Name, Code und Kostenstelle des Vorgangs sind erforderlich.', 'danger')
            return redirect(url_for('admin_finanzen')) # Or admin_cost_centers

    # --- Data for GET requests and initial page load ---
    filter_cost_center_id = request.args.get('filter_cost_center_id', type=int)
    filter_process_id = request.args.get('filter_process_id', type=int)

    transactions_query = Transaction.query

    processes_for_current_cc = [] # Processes for the filter dropdown based on selected cost center
    if filter_cost_center_id:
        transactions_query = transactions_query.filter_by(cost_center_id=filter_cost_center_id)
        current_cost_center_id = filter_cost_center_id
        # Load processes specific to the filtered cost center for the filter dropdown
        processes_for_current_cc = Process.query.filter_by(cost_center_id=filter_cost_center_id).all()
        if filter_process_id:
            transactions_query = transactions_query.filter_by(process_id=filter_process_id)
            current_process_id = filter_process_id
    else:
        # If no cost center filter, show all processes in the filter dropdown
        processes_for_current_cc = all_processes # This ensures the filter dropdown for processes is populated

    transactions = transactions_query.order_by(Transaction.date.desc()).all()

    # Cost center and process summaries
    # This logic assumes you want to calculate sums for each CC and Process
    for cc in cost_centers:
        cc_transactions = Transaction.query.filter_by(cost_center_id=cc.id).all()
        cc.total_income = sum(t.amount for t in cc_transactions if t.type == 'Einnahme' and t.amount is not None)
        cc.total_expense = sum(t.amount for t in cc_transactions if t.type == 'Ausgabe' and t.amount is not None)
        cc.total_balance = cc.total_income - cc.total_expense

        # Ensure processes within cost centers are also calculated
        cc.processes = Process.query.filter_by(cost_center_id=cc.id).all()
        for p in cc.processes:
            p_transactions = Transaction.query.filter_by(process_id=p.id).all()
            p.total_income = sum(t.amount for t in p_transactions if t.type == 'Einnahme' and t.amount is not None)
            p.total_expense = sum(t.amount for t in p_transactions if t.type == 'Ausgabe' and t.amount is not None)
            p.total_balance = p.total_income - p.total_expense

    # Chart data: Monthly summary
    monthly_summary = defaultdict(lambda: {'income': 0, 'expense': 0})
    for transaction in Transaction.query.all():
        month_year = transaction.date.strftime('%Y-%m')
        if transaction.type == 'Einnahme' and transaction.amount is not None:
            monthly_summary[month_year]['income'] += float(transaction.amount)
        elif transaction.type == 'Ausgabe' and transaction.amount is not None:
            monthly_summary[month_year]['expense'] += float(transaction.amount)

    sorted_monthly_summary = sorted(monthly_summary.items())

    # Pie chart by category
    category_data = db.session.query(
        Transaction.category,
        func.sum(Transaction.amount)
    ).filter(Transaction.type == 'Ausgabe').group_by(Transaction.category).all()

    category_labels = [row[0] or 'Ohne Kategorie' for row in category_data]
    category_data_values = [float(row[1]) for row in category_data]

    # Totals
    total_income = db.session.query(func.sum(Transaction.amount)).filter_by(type='Einnahme').scalar() or 0
    total_expense = db.session.query(func.sum(Transaction.amount)).filter_by(type='Ausgabe').scalar() or 0
    total_balance = total_income - total_expense

    # Categories for the Datalist
    categories = db.session.query(Transaction.category).distinct().filter(Transaction.category != None).all()
    categories = [category[0] for category in categories]

    return render_template('admin_finanzen.html',
                            cost_centers=cost_centers, # For 'Neue Transaktion' form and filter
                            processes=all_processes, # <--- Used by 'Neue Transaktion' form
                            transactions=transactions,
                            today_date=today_date,
                            current_cost_center_id=current_cost_center_id,
                            current_process_id=current_process_id,
                            processes_for_current_cc=processes_for_current_cc, # Used by the filter dropdown
                            all_processes=all_processes, # A comprehensive list, might be used by edit modal or other parts
                            monthly_summary=sorted_monthly_summary,
                            total_income=total_income,
                            total_expense=total_expense,
                            total_balance=total_balance,
                            category_labels=category_labels,
                            category_data=category_data_values,
                            categories=categories,
                            all_cost_centers=cost_centers # For 'editTransactionModal' as per your HTML
                           )



@app.route('/admin/cost_centers/<int:cost_center_id>/processes.json')
def get_processes_json(cost_center_id):
    processes = Process.query.filter_by(cost_center_id=cost_center_id).order_by(Process.name).all()
    return jsonify(processes=[{'id': p.id, 'name': p.name} for p in processes])

@app.route('/download_document/<int:id>')
def download_document(id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    transaction = Transaction.query.get_or_404(id)
    if not transaction.document_filename:
        flash('Kein Beleg für diese Transaktion vorhanden.', 'danger')
        return redirect(url_for('admin_finanzen'))
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], transaction.document_filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    flash('Belegdatei nicht gefunden.', 'danger')
    return redirect(url_for('admin_finanzen'))

@app.route('/generate_receipt/<int:id>')
def generate_receipt(id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))

    transaction = Transaction.query.options(
        db.joinedload(Transaction.cost_center),
        db.joinedload(Transaction.process)
    ).get_or_404(id)

    # Check if the transaction is an income (donation)
    if transaction.type != 'Einnahme':
        flash('Nur Einnahmen können als Spendenquittung generiert werden.', 'danger')
        return redirect(url_for('admin_finanzen'))

    # Render HTML template to a string
    html_string = render_template('receipt_template.html', transaction=transaction)

    # Convert HTML to PDF
    pdf_file = HTML(string=html_string).write_pdf()

    # Create a BytesIO buffer to serve the PDF
    buf = io.BytesIO(pdf_file)
    buf.seek(0)

    filename = f"Spendenbescheinigung_{transaction.id}_{transaction.date.strftime('%Y%m%d')}.pdf"

    flash('Spendenbescheinigung erfolgreich generiert!', 'success')
    return send_file(buf, as_attachment=True, download_name=filename, mimetype='application/pdf')

@app.route('/donate', methods=['GET', 'POST'])
def public_donate():
    cost_centers = CostCenter.query.order_by(CostCenter.name).all()
    # Processes would likely be loaded dynamically via AJAX based on selected cost center
    if request.method == 'POST':
        # ... process donation form submission, create Transaction
        # Ensure description, amount, type='Einnahme', category='Spende', date,
        # cost_center_id, and process_id are captured and saved.
        # You might need to handle payment gateway integration here (PayPal/Sofort).
        flash('Vielen Dank für Ihre Spende!', 'success')
        return redirect(url_for('public_donate'))
    return render_template('public_donation_form.html', cost_centers=cost_centers) # New template

@app.route('/admin/finanzen/edit/<int:transaction_id>', methods=['GET', 'POST'])
def admin_finanzen_edit(transaction_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    
    transaction = Transaction.query.get_or_404(transaction_id)
    cost_centers = CostCenter.query.order_by(CostCenter.name).all()
    processes = Process.query.all()
    
    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        amount = request.form.get('amount', '0').strip()
        type_ = request.form.get('type', '').strip()
        date_str = request.form.get('date', '').strip()
        cost_center_id = request.form.get('cost_center_id', '').strip()
        process_id = request.form.get('process_id', '').strip()
        is_approved = 'is_approved' in request.form
        
        errors = []
        
        if not description:
            errors.append('Beschreibung ist erforderlich')
            
        try:
            amount_float = float(amount) if amount else 0.0
            if type_ != 'note' and amount_float <= 0:
                errors.append('Betrag muss größer als 0 sein')
        except ValueError:
            errors.append('Ungültiger Betrag')
            
        if type_ not in ['Einnahme', 'Ausgabe', 'note']:
            errors.append('Ungültiger Transaktionstyp')
            
        try:
            date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            errors.append('Ungültiges Datumsformat')
            
        if cost_center_id and not CostCenter.query.get(cost_center_id):
            errors.append('Ungültige Kostenstelle')
            
        if process_id and not Process.query.get(process_id):
            errors.append('Ungültiger Vorgang')
            
        if not errors:
            try:
                transaction.description = description
                transaction.amount = amount_float if type_ != 'note' else None
                transaction.type = type_
                transaction.date = date
                transaction.cost_center_id = cost_center_id if cost_center_id else None
                transaction.process_id = process_id if process_id else None
                transaction.is_approved = is_approved
                
                if 'document' in request.files:
                    file = request.files['document']
                    if file and file.filename:
                        filename = secure_filename(file.filename)
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        transaction.document_filename = filename
                
                db.session.commit()
                flash('Transaktion erfolgreich aktualisiert', 'success')
                return redirect(url_for('admin_finanzen'))
            except Exception as e:
                db.session.rollback()
                flash(f'Fehler beim Speichern: {str(e)}', 'danger')
        else:
            for error in errors:
                flash(error, 'danger')
    
    return render_template('transaction_edit.html', 
                         transaction=transaction,
                         cost_centers=cost_centers, # Keep if used elsewhere
                        # all_cost_centers=cost_centers # Add this line to pass it as all_cost_centers
                         processes=processes,
                         today=datetime.date.today())

@app.route('/admin/finanzen/loeschen/<int:transaction_id>', methods=['POST'])
def admin_finanzen_loeschen(transaction_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    transaction = Transaction.query.get_or_404(transaction_id)
    db.session.delete(transaction)
    db.session.commit()
    flash('Transaktion erfolgreich gelöscht!', 'success')
    return redirect(url_for('admin_finanzen'))

@app.route('/admin/finanzen/export/<int:cost_center_id>', methods=['GET'])
def admin_finanzen_export(cost_center_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    cost_center = CostCenter.query.get_or_404(cost_center_id)
    transactions = Transaction.query.filter_by(cost_center_id=cost_center_id).all()
    df = pd.DataFrame([{
        'ID': t.id,
        'Beschreibung': t.description,
        'Betrag': t.amount,
        'Typ': t.type,
        'Kategorie': t.category or 'Keine',
        'Datum': t.date.strftime('%d.%m.%Y'),
        'Vorgang': Process.query.get(t.process_id).name if t.process_id else 'Keiner'
    } for t in transactions])
    
    buf = BytesIO()
    df.to_excel(buf, index=False, sheet_name='Finanzbericht')
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=f"Finanzbericht_{cost_center.name}.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/admin/transactions/<int:transaction_id>', methods=['GET'])
def get_transaction_details(transaction_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))

    transactions = Transaction.query.options(
        db.joinedload(Transaction.cost_center),
        db.joinedload(Transaction.process)
    ).order_by(Transaction.date.desc()).all()

    unique_categories = db.session.query(Transaction.category).distinct().all()
    categories_list = [c[0] for c in unique_categories if c[0]]

    return render_template('admin_all_transactions.html',
                         transactions=transactions,
                         today=datetime.date.today(),
                         categories=categories_list)

@app.route('/admin/finanzen/export_all', methods=['GET'])
def admin_finanzen_export_all():
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))

    transactions = Transaction.query.options(
        db.joinedload(Transaction.cost_center),
        db.joinedload(Transaction.process)
    ).order_by(Transaction.date.desc()).all()

    data = []
    for t in transactions:
        cost_center_name = t.cost_center.name if t.cost_center else "Nicht zugewiesen"
        process_name = t.process.name if t.process else "Nicht zugewiesen"

        data.append({
            'ID': t.id,
            'Beschreibung': t.description,
            'Betrag': float(t.amount) if t.amount is not None else 0.0,
            'Typ': t.type,
            'Kategorie': t.category or 'Keine',
            'Datum': t.date.strftime('%d.%m.%Y') if t.date else 'N/A',
            'Kostenstelle': cost_center_name,
            'Vorgang': process_name
        })

    df = pd.DataFrame(data)

    buf = BytesIO()
    df.to_excel(buf, index=False, sheet_name='Alle Buchungen')
    buf.seek(0)

    return send_file(buf, 
                   as_attachment=True, 
                   download_name=f"Alle_Buchungen_{datetime.date.today().strftime('%Y%m%d')}.xlsx", 
                   mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')



@app.route("/klassenbuch")
def klassenbuch():
    klassen = Klasse.query.all()
    return render_template("virtuelles_klassenbuch.html", klassen=klassen)


@app.route("/klasse_erstellen", methods=["GET", "POST"])
def klasse_erstellen():
    schuljahr_vorschlag = f"{datetime.datetime.now().year}/{datetime.datetime.now().year + 1}"
    if request.method == "POST":
        name = request.form.get("name")
        schuljahr = request.form.get("schuljahr")
        if not name or not schuljahr:
            flash("Klassenname und Schuljahr sind erforderlich.", "danger")
            return render_template("klasse_erstellen.html", schuljahr_vorschlag=schuljahr_vorschlag)

        # Überprüfen, ob die Klasse bereits existiert
        existing_klasse = Klasse.query.filter_by(name=name, schuljahr=schuljahr).first()
        if existing_klasse:
            flash("Eine Klasse mit diesem Namen und Schuljahr existiert bereits.", "danger")
            return render_template("klasse_erstellen.html", schuljahr_vorschlag=schuljahr_vorschlag)

        neue_klasse = Klasse(name=name, schuljahr=schuljahr)
        db.session.add(neue_klasse)
        db.session.commit()
        flash("Klasse erfolgreich erstellt!", "success")
        return redirect(url_for("klassenbuch"))
    return render_template("klasse_erstellen.html", schuljahr_vorschlag=schuljahr_vorschlag)


@app.route("/klasse_bearbeiten/<int:klasse_id>", methods=["GET", "POST"])
def klasse_bearbeiten(klasse_id):
    klasse = Klasse.query.get_or_404(klasse_id)
    if request.method == "POST":
        name = request.form.get("name")
        schuljahr = request.form.get("schuljahr")

        if not name or not schuljahr:
            flash("Klassenname und Schuljahr dürfen nicht leer sein.", "danger")
            return render_template("klasse_bearbeiten.html", klasse=klasse)

        # Überprüfen, ob der neue Name/Schuljahr bereits für eine andere Klasse existiert
        existing_klasse = Klasse.query.filter(
            Klasse.name == name, Klasse.schuljahr == schuljahr, Klasse.id != klasse_id
        ).first()
        if existing_klasse:
            flash("Eine andere Klasse mit diesem Namen und Schuljahr existiert bereits.", "danger")
            return render_template("klasse_bearbeiten.html", klasse=klasse)

        klasse.name = name
        klasse.schuljahr = schuljahr
        db.session.commit()
        flash("Klasse erfolgreich aktualisiert.", "success")
        return redirect(url_for("klassenbuch"))
    return render_template("klasse_bearbeiten.html", klasse=klasse)


@app.route("/klasse_loeschen/<int:klasse_id>", methods=["POST"])
def klasse_loeschen(klasse_id):
    klasse = Klasse.query.get_or_404(klasse_id)
    # Optional: Vor dem Löschen prüfen, ob verknüpfte Schüler oder Unterrichtseinheiten existieren
    if klasse.schueler or klasse.unterrichtseinheiten:
        flash(
            "Klasse kann nicht gelöscht werden, da noch Schüler oder Unterrichtseinheiten zugewiesen sind.",
            "danger",
        )
        return redirect(url_for("klassenbuch"))
    db.session.delete(klasse)
    db.session.commit()
    flash("Klasse erfolgreich gelöscht.", "success")
    return redirect(url_for("klassenbuch"))


@app.route("/klassenbuch_details/<int:klasse_id>")
def klassenbuch_details(klasse_id):
    klasse = Klasse.query.get_or_404(klasse_id)
    schueler = Schueler.query.filter_by(klasse_id=klasse_id).order_by(Schueler.nachname).all()
    # Unterrichtseinheiten sortiert nach Datum (neueste zuerst), dann Stunden
    unterrichtseinheiten = (
        Unterrichtseinheit.query.filter_by(klasse_id=klasse_id)
        .order_by(Unterrichtseinheit.datum.desc(), Unterrichtseinheit.stunden.asc())
        .all()
    )

    # Anwesenheitsdaten abrufen
    anwesenheits_data = defaultdict(lambda: defaultdict(dict))
    for anwesenheit in Anwesenheit.query.filter(
        Anwesenheit.unterrichtseinheit_id.in_([ue.id for ue in unterrichtseinheiten])
    ).all():
        anwesenheits_data[anwesenheit.unterrichtseinheit_id][anwesenheit.schueler_id][
            "anwesend"
        ] = anwesenheit.anwesend
        anwesenheits_data[anwesenheit.unterrichtseinheit_id][anwesenheit.schueler_id][
            "entschuldigt"
        ] = anwesenheit.entschuldigt

    return render_template(
        "klassenbuch_details.html",
        klasse=klasse,
        schueler=schueler,
        unterrichtseinheiten=unterrichtseinheiten,
        anwesenheits_data=anwesenheits_data,
    )


@app.route("/schueler_erstellen/<int:klasse_id>", methods=["GET", "POST"])
def schueler_erstellen(klasse_id):
    klasse = Klasse.query.get_or_404(klasse_id)
    if request.method == "POST":
        name = request.form.get("name")
        nachname = request.form.get("nachname")
        geburtsdatum_str = request.form.get("geburtsdatum")
        geschlecht = request.form.get("geschlecht")

        if not all([name, nachname]):
            flash("Vorname und Nachname sind erforderlich.", "danger")
            return render_template("schueler_erstellen.html", klasse=klasse)

        geburtsdatum = None
        if geburtsdatum_str:
            try:
                geburtsdatum = datetime.datetime.strptime(geburtsdatum_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Ungültiges Datumsformat für Geburtsdatum.", "danger")
                return render_template("schueler_erstellen.html", klasse=klasse)

        neuer_schueler = Schueler(
            name=name,
            nachname=nachname,
            geburtsdatum=geburtsdatum,
            geschlecht=geschlecht,
            klasse_id=klasse.id,
        )
        db.session.add(neuer_schueler)
        db.session.commit()
        flash("Schüler erfolgreich hinzugefügt!", "success")
        return redirect(url_for("klassenbuch_details", klasse_id=klasse.id))
    return render_template("schueler_erstellen.html", klasse=klasse)


@app.route("/schueler_bearbeiten/<int:schueler_id>", methods=["GET", "POST"])
def schueler_bearbeiten(schueler_id):
    schueler = Schueler.query.get_or_404(schueler_id)
    klassen = Klasse.query.all()  # Für die Auswahl der Klasse
    if request.method == "POST":
        schueler.name = request.form["name"]
        schueler.nachname = request.form["nachname"]
        schueler.geschlecht = request.form["geschlecht"]
        schueler.klasse_id = request.form["klasse_id"]

        geburtsdatum_str = request.form.get("geburtsdatum")
        if geburtsdatum_str:
            try:
                schueler.geburtsdatum = datetime.datetime.strptime(
                    geburtsdatum_str, "%Y-%m-%d"
                ).date()
            except ValueError:
                flash("Ungültiges Datumsformat für Geburtsdatum.", "danger")
                return render_template(
                    "schueler_bearbeiten.html", schueler=schueler, klassen=klassen
                )
        else:
            schueler.geburtsdatum = None

        db.session.commit()
        flash("Schülerdaten erfolgreich aktualisiert.", "success")
        return redirect(url_for("klassenbuch_details", klasse_id=schueler.klasse_id))
    return render_template("schueler_bearbeiten.html", schueler=schueler, klassen=klassen)


@app.route("/schueler_loeschen/<int:schueler_id>", methods=["POST"])
def schueler_loeschen(schueler_id):
    schueler = Schueler.query.get_or_404(schueler_id)
    klasse_id = schueler.klasse_id
    db.session.delete(schueler)
    db.session.commit()
    flash("Schüler erfolgreich gelöscht.", "success")
    return redirect(url_for("klassenbuch_details", klasse_id=klasse_id))


@app.route('/klassenbuch/<int:klasse_id>/schueler_hinzufuegen', methods=['GET', 'POST'])
def schueler_hinzufuegen(klasse_id):
    klasse = Klasse.query.get_or_404(klasse_id)
    if request.method == 'POST':
        name = request.form['name'].strip()
        nachname = request.form['nachname'].strip()
        geburtsdatum_str = request.form.get('geburtsdatum')
        geschlecht = request.form.get('geschlecht')

        if not name or not nachname:
            flash('Vorname und Nachname sind Pflichtfelder.', 'danger')
            return redirect(url_for('klassenbuch_details', klasse_id=klasse_id))

        geburtsdatum = None
        if geburtsdatum_str:
            try:
                geburtsdatum = datetime.datetime.strptime(geburtsdatum_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Ungültiges Geburtsdatum-Format. Bitte YYYY-MM-DD verwenden.', 'danger')
                return redirect(url_for('klassenbuch_details', klasse_id=klasse_id))

        # Überprüfen, ob Schüler bereits existiert (optional, aber empfohlen)
        existing_schueler = Schueler.query.filter_by(
            name=name,
            nachname=nachname,
            klasse_id=klasse.id
        ).first()
        if existing_schueler:
            flash('Ein Schüler mit diesem Namen und Nachnamen existiert bereits in dieser Klasse.', 'warning')
            return redirect(url_for('klassenbuch_details', klasse_id=klasse_id))

        new_schueler = Schueler(
            name=name,
            nachname=nachname,
            geburtsdatum=geburtsdatum,
            geschlecht=geschlecht,
            klasse_id=klasse.id
        )
        db.session.add(new_schueler)
        db.session.commit()
        flash('Schüler erfolgreich hinzugefügt!', 'success')
        return redirect(url_for('klassenbuch_details', klasse_id=klasse_id))

    # If it's a GET request, render the template (you might need a separate template for adding a student or integrate it into klassenbuch_details.html)
    return render_template('klassenbuch_details.html', klasse=klasse) # Or a dedicated schueler_hinzufuegen.html if you prefer.

@app.route("/unterricht_erstellen", methods=["GET", "POST"])
def unterricht_erstellen():
    klassen = Klasse.query.all()
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    if request.method == "POST":
        datum_str = request.form.get("datum")
        klasse_id = request.form.get("klasse_id")
        stunden_list = request.form.getlist("stunden[]")
        themen_list = request.form.getlist("themen[]")
        inhalte_list = request.form.getlist("inhalte[]")

        if not datum_str or not klasse_id:
            flash("Datum und Klasse sind erforderlich.", "danger")
            return render_template(
                "unterricht_erstellen.html", klassen=klassen, current_date=current_date
            )

        try:
            datum = datetime.datetime.strptime(datum_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Ungültiges Datumsformat.", "danger")
            return render_template(
                "unterricht_erstellen.html", klassen=klassen, current_date=current_date
            )

        # Validate that at least one lesson entry is provided
        if not stunden_list or not themen_list:
            flash("Bitte geben Sie mindestens eine Unterrichtseinheit ein.", "danger")
            return render_template(
                "unterricht_erstellen.html", klassen=klassen, current_date=current_date
            )

        # Handle potentially missing 'inhalte' entries for new rows
        # Ensure inhalte_list has the same length as themen_list, fill with empty string if shorter
        inhalte_list = inhalte_list + [''] * (len(stunden_list) - len(inhalte_list))

        successful_entries = 0
        for i in range(len(stunden_list)):
            stunden_raw = stunden_list[i].strip()
            thema = themen_list[i].strip()
            inhalte = inhalte_list[i].strip()

            if not stunden_raw or not thema:
                flash(f"Stunde und Thema für Eintrag {i+1} sind erforderlich und können nicht leer sein. Dieser Eintrag wurde übersprungen.", "warning")
                continue

            hours_to_add = []
            if '-' in stunden_raw:
                try:
                    start_hour, end_hour = map(int, stunden_raw.split('-'))
                    if start_hour > end_hour:
                        flash(f"Ungültiger Stundenbereich '{stunden_raw}' für Eintrag {i+1}. Startstunde muss kleiner oder gleich der Endstunde sein. Dieser Eintrag wurde übersprungen.", "warning")
                        continue
                    hours_to_add.extend(str(h) for h in range(start_hour, end_hour + 1))
                except ValueError:
                    flash(f"Ungültiges Stundenbereichsformat '{stunden_raw}' für Eintrag {i+1}. Erwartet wird 'X-Y' (z.B. '1-3'). Dieser Eintrag wurde übersprungen.", "warning")
                    continue
            else:
                try:
                    # Validate individual hour is an integer
                    int(stunden_raw)
                    hours_to_add.append(stunden_raw)
                except ValueError:
                    flash(f"Ungültiges Stundenformat '{stunden_raw}' für Eintrag {i+1}. Erwartet wird eine Zahl oder ein Bereich (z.B. '1' oder '1-3'). Dieser Eintrag wurde übersprungen.", "warning")
                    continue

            for hour in hours_to_add:
                # Check for existing entry for the same class, date, and hour
                existing_ue = Unterrichtseinheit.query.filter_by(
                    klasse_id=klasse_id,
                    datum=datum,
                    stunden=hour
                ).first()

                if existing_ue:
                    flash(f"Unterrichtseinheit für Klasse {Klasse.query.get(klasse_id).name} am {datum.strftime('%d.%m.%Y')} für Stunde {hour} existiert bereits und wurde übersprungen.", "warning")
                    continue

                neue_unterrichtseinheit = Unterrichtseinheit(
                    datum=datum,
                    stunden=hour,
                    thema=thema,
                    inhalte=inhalte,
                    klasse_id=klasse_id,
                )
                db.session.add(neue_unterrichtseinheit)
                successful_entries += 1
        
        if successful_entries > 0:
            db.session.commit()
            flash(f"{successful_entries} Unterrichtseinheit(en) erfolgreich erstellt!", "success")
            return redirect(url_for("unterricht_details"))
        else:
            flash("Keine Unterrichtseinheiten erfolgreich erstellt. Bitte überprüfen Sie Ihre Eingaben.", "danger")
            db.session.rollback() # Rollback if no successful entries after some failed
            return render_template(
                "unterricht_erstellen.html", klassen=klassen, current_date=current_date
            )

    return render_template("unterricht_erstellen.html", klassen=klassen, current_date=current_date)



@app.route('/unterricht_details') # Standardmäßig GET erlaubt
def unterricht_details():
    # ...
    # Sort by date (descending) and then by stunden (ascending)
    unterrichtseinheiten = (
        Unterrichtseinheit.query.order_by(
            Unterrichtseinheit.datum.desc(), Unterrichtseinheit.stunden.asc()
        )
        .join(Klasse)
        .all()
    )
    return render_template("unterricht_details.html", unterrichtseinheiten=unterrichtseinheiten)


@app.route("/unterricht_einheit/<int:unterricht_id>", methods=["GET"])
def unterricht_einheit(unterricht_id):
    unterrichtseinheit = Unterrichtseinheit.query.get_or_404(unterricht_id)
    klasse = Klasse.query.get_or_404(unterrichtseinheit.klasse_id)
    schueler = Schueler.query.filter_by(klasse_id=klasse.id).order_by(Schueler.nachname).all()

    # Anwesenheitsdaten für diese Unterrichtseinheit laden
    anwesenheit_status = {
        a.schueler_id: {"anwesend": a.anwesend, "entschuldigt": a.entschuldigt}
        for a in Anwesenheit.query.filter_by(unterrichtseinheit_id=unterricht_id).all()
    }

    return render_template(
        "unterricht_einheit.html",
        unterrichtseinheit=unterrichtseinheit,
        klasse=klasse,
        schueler=schueler,
        anwesenheit_status=anwesenheit_status,
    )


@app.route("/anwesenheit_verwalten/<int:unterricht_id>", methods=["POST"])
def anwesenheit_verwalten(unterricht_id):
    unterrichtseinheit = Unterrichtseinheit.query.get_or_404(unterricht_id)
    klasse_id = unterrichtseinheit.klasse_id

    schueler_der_klasse = Schueler.query.filter_by(klasse_id=klasse_id).all()

    for schueler in schueler_der_klasse:
        anwesend_key = f"anwesend_{schueler.id}"
        entschuldigt_key = f"entschuldigt_{schueler.id}"

        anwesend = anwesend_key in request.form
        entschuldigt = entschuldigt_key in request.form

        anwesenheit_eintrag = Anwesenheit.query.filter_by(
            schueler_id=schueler.id, unterrichtseinheit_id=unterricht_id
        ).first()

        if anwesenheit_eintrag:
            anwesenheit_eintrag.anwesend = anwesend
            anwesenheit_eintrag.entschuldigt = entschuldigt
        else:
            neuer_eintrag = Anwesenheit(
                schueler_id=schueler.id,
                unterrichtseinheit_id=unterricht_id,
                anwesend=anwesend,
                entschuldigt=entschuldigt,
            )
            db.session.add(neuer_eintrag)

    db.session.commit()
    flash("Anwesenheit erfolgreich gespeichert.", "success")
    return redirect(url_for("unterricht_einheit", unterricht_id=unterricht_id))


@app.route("/unterricht_bearbeiten/<int:unterricht_id>", methods=["GET", "POST"])
def unterricht_bearbeiten(unterricht_id):
    unterrichtseinheit = Unterrichtseinheit.query.get_or_404(unterricht_id)
    klassen = Klasse.query.all()
    if request.method == "POST":
        datum_str = request.form["datum"]
        stunden = request.form["stunden"]
        thema = request.form["thema"]
        inhalte = request.form.get("inhalte", "")
        klasse_id = request.form["klasse_id"]

        try:
            datum = datetime.datetime.strptime(datum_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Ungültiges Datumsformat.", "danger")
            return render_template(
                "unterricht_bearbeiten.html",
                unterrichtseinheit=unterrichtseinheit,
                klassen=klassen,
            )

        # Check for overlaps: Does another Unterrichtseinheit exist for the same class, date, and hour, excluding the current one being edited?
        existing_ue = Unterrichtseinheit.query.filter(
            Unterrichtseinheit.klasse_id == klasse_id,
            Unterrichtseinheit.datum == datum,
            Unterrichtseinheit.stunden == stunden,
            Unterrichtseinheit.id != unterricht_id,
        ).first()
        if existing_ue:
            flash(
                "Eine Unterrichtseinheit für diese Klasse, dieses Datum und diese Stunde existiert bereits.",
                "danger",
            )
            return render_template(
                "unterricht_bearbeiten.html",
                unterrichtseinheit=unterrichtseinheit,
                klassen=klassen,
            )

        unterrichtseinheit.datum = datum
        unterrichtseinheit.stunden = stunden
        unterrichtseinheit.thema = thema
        unterrichtseinheit.inhalte = inhalte
        unterrichtseinheit.klasse_id = klasse_id
        db.session.commit()
        flash("Unterrichtseinheit erfolgreich aktualisiert.", "success")
        return redirect(url_for("klassenbuch_details", klasse_id=klasse_id))
    return render_template(
        "unterricht_bearbeiten.html", unterrichtseinheit=unterrichtseinheit, klassen=klassen
    )


@app.route("/unterricht_loeschen/<int:unterricht_id>", methods=["POST"])
def unterricht_loeschen(unterricht_id):
    unterrichtseinheit = Unterrichtseinheit.query.get_or_404(unterricht_id)
    klasse_id = unterrichtseinheit.klasse_id
    db.session.delete(unterrichtseinheit)
    db.session.commit()
    flash("Unterrichtseinheit erfolgreich gelöscht.", "success")
    return redirect(url_for("klassenbuch_details", klasse_id=klasse_id))


@app.route("/klassenbuch_pdf/<int:klasse_id>")
def klassenbuch_pdf(klasse_id):
    klasse = Klasse.query.get_or_404(klasse_id)
    schueler = Schueler.query.filter_by(klasse_id=klasse_id).order_by(Schueler.nachname).all()
    unterrichtseinheiten = (
        Unterrichtseinheit.query.filter_by(klasse_id=klasse_id)
        .order_by(Unterrichtseinheit.datum.asc(), Unterrichtseinheit.stunden.asc())
        .all()
    )

    anwesenheits_data = defaultdict(lambda: defaultdict(dict))
    for ue in unterrichtseinheiten:
        for anwesenheit in Anwesenheit.query.filter_by(unterrichtseinheit_id=ue.id).all():
            anwesenheits_data[ue.id][anwesenheit.schueler_id][
                "anwesend"
            ] = anwesenheit.anwesend
            anwesenheits_data[ue.id][anwesenheit.schueler_id][
                "entschuldigt"
            ] = anwesenheit.entschuldigt

    rendered_html = render_template(
        "klassenbuch_pdf_template.html",
        klasse=klasse,
        schueler=schueler,
        unterrichtseinheiten=unterrichtseinheiten,
        anwesenheits_data=anwesenheits_data,
        current_date=datetime.date.today().strftime("%d.%m.%Y"),
    )

    # WeasyPrint expects bytes for HTML input
    # HTML(string=rendered_html).write_pdf('klassenbuch.pdf')
    # return send_file('klassenbuch.pdf', as_attachment=True, mimetype='application/pdf')
    flash("PDF-Generierung ist derzeit deaktiviert.", "info")
    return redirect(url_for("klassenbuch_details", klasse_id=klasse_id))


@app.route("/statistik/<int:klasse_id>")
def statistik2(klasse_id):
    klasse = Klasse.query.get_or_404(klasse_id)
    schueler = Schueler.query.filter_by(klasse_id=klasse_id).all()

    if not schueler:
        flash("Keine Schüler in dieser Klasse für die Statistik.", "warning")
        return redirect(url_for("klassenbuch_details", klasse_id=klasse_id))

    # Gesamtanzahl der Unterrichtseinheiten für diese Klasse
    total_unterrichtseinheiten = Unterrichtseinheit.query.filter_by(klasse_id=klasse_id).count()

    anwesenheits_counts = defaultdict(lambda: {"anwesend": 0, "entschuldigt": 0, "unentschuldigt": 0})
    for s in schueler:
        # Anwesenheiten pro Schüler
        anwesenheiten_pro_schueler = Anwesenheit.query.filter_by(schueler_id=s.id).all()
        for anw in anwesenheiten_pro_schueler:
            if anw.anwesend:
                anwesenheits_counts[s.id]["anwesend"] += 1
            elif anw.entschuldigt:
                anwesenheits_counts[s.id]["entschuldigt"] += 1
            else:
                anwesenheits_counts[s.id]["unentschuldigt"] += 1

    # Diagramm für Anwesenheitsstatistik pro Schüler
    labels = [f"{s.name} {s.nachname}" for s in schueler]
    anwesend_data = [anwesenheits_counts[s.id]["anwesend"] for s in schueler]
    entschuldigt_data = [anwesenheits_counts[s.id]["entschuldigt"] for s in schueler]
    unentschuldigt_data = [anwesenheits_counts[s.id]["unentschuldigt"] for s in schueler]

    # Erstellen eines gestapelten Balkendiagramms
    fig, ax = plt.subplots(figsize=(12, 6))

    bar_width = 0.6
    indices = range(len(labels))

    p1 = ax.bar(indices, anwesend_data, bar_width, label="Anwesend", color="green")
    p2 = ax.bar(
        indices,
        entschuldigt_data,
        bar_width,
        bottom=anwesend_data,
        label="Entschuldigt",
        color="orange",
    )
    p3 = ax.bar(
        indices,
        unentschuldigt_data,
        bar_width,
        bottom=[i + j for i, j in zip(anwesend_data, entschuldigt_data)],
        label="Unentschuldigt",
        color="red",
    )

    ax.set_ylabel("Anzahl der Unterrichtseinheiten")
    ax.set_title(f"Anwesenheitsstatistik für Klasse: {klasse.name}")
    ax.set_xticks(indices)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    # Diagramm in BytesIO speichern
    buf = BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    plt.close(fig)
    chart_image = "data:image/png;base64," + (base64.b64encode(buf.getvalue())).decode("utf-8")

    return render_template(
        "statistik.html",
        klasse=klasse,
        schueler=schueler,
        anwesenheits_counts=anwesenheits_counts,
        total_unterrichtseinheiten=total_unterrichtseinheiten,
        chart_image=chart_image,
    )

# ===== ERWEITERTE KLASSENBUCH-FUNKTIONEN =====

# === Fächer- und Lehrerverwaltung ===

@app.route('/admin/faecher')
def faecher_verwalten():
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    faecher = Fach.query.all()
    return render_template('admin/faecher.html', faecher=faecher)

@app.route('/admin/fach/neu', methods=['GET', 'POST'])
def fach_neu():
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    if request.method == 'POST':
        name = request.form['name']
        kuerzel = request.form['kuerzel']
        farbe = request.form.get('farbe', '#007bff')
        beschreibung = request.form.get('beschreibung', '')
        
        fach = Fach(name=name, kuerzel=kuerzel, farbe=farbe, beschreibung=beschreibung)
        db.session.add(fach)
        db.session.commit()
        flash('Fach erfolgreich erstellt!', 'success')
        return redirect(url_for('faecher_verwalten'))
    return render_template('admin/fach_form.html')

@app.route('/admin/fach/<int:fach_id>/bearbeiten', methods=['GET', 'POST'])
def fach_bearbeiten(fach_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    fach = Fach.query.get_or_404(fach_id)
    if request.method == 'POST':
        fach.name = request.form['name']
        fach.kuerzel = request.form['kuerzel']
        fach.farbe = request.form.get('farbe', fach.farbe)
        fach.beschreibung = request.form.get('beschreibung', '')
        db.session.commit()
        flash('Fach erfolgreich aktualisiert!', 'success')
        return redirect(url_for('faecher_verwalten'))
    return render_template('admin/fach_form.html', fach=fach)

@app.route('/admin/lehrer')
def lehrer_verwalten():
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    lehrer = Lehrer.query.all()
    return render_template('admin/lehrer.html', lehrer=lehrer)

@app.route('/admin/lehrer/neu', methods=['GET', 'POST'])
def lehrer_neu():
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    faecher = Fach.query.all()
    klassen = Klasse.query.all()
    
    if request.method == 'POST':
        kuerzel = request.form['kuerzel']
        vorname = request.form['vorname']
        nachname = request.form['nachname']
        email = request.form['email']
        telefon = request.form.get('telefon', '')
        
        lehrer = Lehrer(kuerzel=kuerzel, vorname=vorname, nachname=nachname, 
                       email=email, telefon=telefon)
        
        # Fächer zuordnen
        fach_ids = request.form.getlist('faecher')
        for fach_id in fach_ids:
            fach = Fach.query.get(fach_id)
            if fach:
                lehrer.faecher.append(fach)
        
        # Klassen zuordnen
        klasse_ids = request.form.getlist('klassen')
        for klasse_id in klasse_ids:
            klasse = Klasse.query.get(klasse_id)
            if klasse:
                lehrer.klassen.append(klasse)
        
        db.session.add(lehrer)
        db.session.commit()
        flash('Lehrer erfolgreich erstellt!', 'success')
        return redirect(url_for('lehrer_verwalten'))
    
    return render_template('admin/lehrer_form.html', faecher=faecher, klassen=klassen)

# === Notenverwaltung ===

@app.route('/noten/<int:klasse_id>')
def noten_uebersicht(klasse_id):
    klasse = Klasse.query.get_or_404(klasse_id)
    schueler = Schueler.query.filter_by(klasse_id=klasse_id).order_by(Schueler.nachname).all()
    faecher = Fach.query.all()
    bewertungstypen = Bewertungstyp.query.all()
    
    # Noten laden - gruppiert nach Schüler und Fach
    noten_data = defaultdict(lambda: defaultdict(list))
    for note in Note.query.join(Schueler).filter(Schueler.klasse_id == klasse_id).all():
        noten_data[note.schueler_id][note.fach_id].append(note)
    
    return render_template('noten/uebersicht.html', 
                         klasse=klasse, 
                         schueler=schueler, 
                         faecher=faecher,
                         bewertungstypen=bewertungstypen,
                         noten_data=noten_data)

@app.route('/note/neu', methods=['GET', 'POST'])
def note_neu():
    if request.method == 'POST':
        schueler_id = request.form['schueler_id']
        fach_id = request.form['fach_id']
        bewertungstyp_id = request.form['bewertungstyp_id']
        note_wert = request.form.get('note')
        punkte = request.form.get('punkte')
        max_punkte = request.form.get('max_punkte')
        kommentar = request.form.get('kommentar', '')
        datum = datetime.datetime.strptime(request.form['datum'], '%Y-%m-%d').date()
        lehrer_id = 1  # TODO: Aus Session/Login
        
        note = Note(
            schueler_id=schueler_id,
            fach_id=fach_id,
            bewertungstyp_id=bewertungstyp_id,
            note=float(note_wert) if note_wert else None,
            punkte=int(punkte) if punkte else None,
            max_punkte=int(max_punkte) if max_punkte else None,
            kommentar=kommentar,
            datum=datum,
            lehrer_id=lehrer_id
        )
        
        db.session.add(note)
        db.session.commit()
        
        # Benachrichtigung erstellen
        schueler = Schueler.query.get(schueler_id)
        fach = Fach.query.get(fach_id)
        if schueler.eltern_id:
            benachrichtigung = Benachrichtigung(
                empfaenger_typ='eltern',
                empfaenger_id=schueler.eltern_id,
                typ='note_neu',
                titel=f'Neue Note in {fach.name}',
                inhalt=f'{schueler.name} {schueler.nachname} hat eine neue Note in {fach.name}: {note_wert if note_wert else f"{punkte}/{max_punkte} Punkte"}'
            )
            db.session.add(benachrichtigung)
            db.session.commit()
        
        flash('Note erfolgreich hinzugefügt!', 'success')
        return redirect(url_for('noten_uebersicht', klasse_id=schueler.klasse_id))
    
    # GET Request - Formular anzeigen
    klasse_id = request.args.get('klasse_id')
    klasse = Klasse.query.get_or_404(klasse_id) if klasse_id else None
    schueler = Schueler.query.filter_by(klasse_id=klasse_id).all() if klasse_id else Schueler.query.all()
    faecher = Fach.query.all()
    bewertungstypen = Bewertungstyp.query.all()
    
    return render_template('noten/note_form.html', 
                         klasse=klasse,
                         schueler=schueler, 
                         faecher=faecher, 
                         bewertungstypen=bewertungstypen)

# === Stundenplan ===

@app.route('/stundenplan/<int:klasse_id>')
def stundenplan_anzeigen(klasse_id):
    klasse = Klasse.query.get_or_404(klasse_id)
    stundenplan = Stundenplan.query.filter_by(klasse_id=klasse_id).all()
    
    # Stundenplan in Matrix organisieren (Wochentag x Stunde)
    stundenplan_matrix = {}
    for sp in stundenplan:
        if sp.wochentag not in stundenplan_matrix:
            stundenplan_matrix[sp.wochentag] = {}
        stundenplan_matrix[sp.wochentag][sp.stunde] = sp
    
    wochentage = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag']
    stunden = list(range(1, 11))  # 1-10 Stunden
    
    return render_template('stundenplan/anzeigen.html', 
                         klasse=klasse,
                         stundenplan_matrix=stundenplan_matrix,
                         wochentage=wochentage,
                         stunden=stunden)

@app.route('/admin/stundenplan/<int:klasse_id>/bearbeiten', methods=['GET', 'POST'])
def stundenplan_bearbeiten(klasse_id):
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    
    klasse = Klasse.query.get_or_404(klasse_id)
    faecher = Fach.query.all()
    lehrer = Lehrer.query.all()
    
    if request.method == 'POST':
        # Alten Stundenplan löschen
        Stundenplan.query.filter_by(klasse_id=klasse_id).delete()
        
        # Neuen Stundenplan erstellen
        for wochentag in range(5):  # Mo-Fr
            for stunde in range(1, 11):  # 1-10
                fach_id = request.form.get(f'fach_{wochentag}_{stunde}')
                lehrer_id = request.form.get(f'lehrer_{wochentag}_{stunde}')
                raum = request.form.get(f'raum_{wochentag}_{stunde}')
                
                if fach_id and lehrer_id:
                    stundenplan_eintrag = Stundenplan(
                        klasse_id=klasse_id,
                        fach_id=fach_id,
                        lehrer_id=lehrer_id,
                        wochentag=wochentag,
                        stunde=stunde,
                        raum=raum,
                        gueltig_ab=datetime.date.today()
                    )
                    db.session.add(stundenplan_eintrag)
        
        db.session.commit()
        flash('Stundenplan erfolgreich aktualisiert!', 'success')
        return redirect(url_for('stundenplan_anzeigen', klasse_id=klasse_id))
    
    # Aktuellen Stundenplan laden
    stundenplan = Stundenplan.query.filter_by(klasse_id=klasse_id).all()
    stundenplan_matrix = {}
    for sp in stundenplan:
        if sp.wochentag not in stundenplan_matrix:
            stundenplan_matrix[sp.wochentag] = {}
        stundenplan_matrix[sp.wochentag][sp.stunde] = sp
    
    return render_template('stundenplan/bearbeiten.html',
                         klasse=klasse,
                         faecher=faecher,
                         lehrer=lehrer,
                         stundenplan_matrix=stundenplan_matrix)

# === Hausaufgabenverwaltung ===

@app.route('/hausaufgaben/<int:klasse_id>')
def hausaufgaben_uebersicht(klasse_id):
    klasse = Klasse.query.get_or_404(klasse_id)
    heute = datetime.date.today()
    
    # Aktuelle Hausaufgaben (noch nicht fällig)
    aktuelle_hausaufgaben = Hausaufgabe.query.filter(
        Hausaufgabe.klasse_id == klasse_id,
        Hausaufgabe.faellig_am >= heute
    ).order_by(Hausaufgabe.faellig_am).all()
    
    # Vergangene Hausaufgaben (letzte 30 Tage)
    vor_30_tagen = heute - datetime.timedelta(days=30)
    vergangene_hausaufgaben = Hausaufgabe.query.filter(
        Hausaufgabe.klasse_id == klasse_id,
        Hausaufgabe.faellig_am < heute,
        Hausaufgabe.faellig_am >= vor_30_tagen
    ).order_by(Hausaufgabe.faellig_am.desc()).all()
    
    return render_template('hausaufgaben/uebersicht.html',
                         klasse=klasse,
                         aktuelle_hausaufgaben=aktuelle_hausaufgaben,
                         vergangene_hausaufgaben=vergangene_hausaufgaben)

@app.route('/hausaufgabe/neu', methods=['GET', 'POST'])
def hausaufgabe_neu():
    if request.method == 'POST':
        titel = request.form['titel']
        beschreibung = request.form['beschreibung']
        fach_id = request.form['fach_id']
        klasse_id = request.form['klasse_id']
        aufgegeben_am = datetime.datetime.strptime(request.form['aufgegeben_am'], '%Y-%m-%d').date()
        faellig_am = datetime.datetime.strptime(request.form['faellig_am'], '%Y-%m-%d').date()
        lehrer_id = 1  # TODO: Aus Session
        
        hausaufgabe = Hausaufgabe(
            titel=titel,
            beschreibung=beschreibung,
            fach_id=fach_id,
            klasse_id=klasse_id,
            lehrer_id=lehrer_id,
            aufgegeben_am=aufgegeben_am,
            faellig_am=faellig_am
        )
        
        db.session.add(hausaufgabe)
        db.session.commit()
        
        # Benachrichtigungen an Schüler/Eltern
        klasse = Klasse.query.get(klasse_id)
        fach = Fach.query.get(fach_id)
        for schueler in klasse.schueler:
            if schueler.eltern_id:
                benachrichtigung = Benachrichtigung(
                    empfaenger_typ='eltern',
                    empfaenger_id=schueler.eltern_id,
                    typ='hausaufgabe',
                    titel=f'Neue Hausaufgabe in {fach.name}',
                    inhalt=f'Neue Hausaufgabe für {schueler.name}: {titel}. Fällig am: {faellig_am.strftime("%d.%m.%Y")}'
                )
                db.session.add(benachrichtigung)
        
        db.session.commit()
        flash('Hausaufgabe erfolgreich erstellt!', 'success')
        return redirect(url_for('hausaufgaben_uebersicht', klasse_id=klasse_id))
    
    klasse_id = request.args.get('klasse_id')
    klasse = Klasse.query.get_or_404(klasse_id) if klasse_id else None
    faecher = Fach.query.all()
    klassen = Klasse.query.all()
    
    return render_template('hausaufgaben/hausaufgabe_form.html',
                         klasse=klasse,
                         faecher=faecher,
                         klassen=klassen)

# === Kommunikationssystem ===

@app.route('/nachrichten')
def nachrichten_uebersicht():
    # TODO: Benutzerauthentifizierung implementieren
    empfaenger_typ = 'lehrer'  # Placeholder
    empfaenger_id = 1  # Placeholder
    
    nachrichten = Nachricht.query.filter_by(
        empfaenger_typ=empfaenger_typ,
        empfaenger_id=empfaenger_id
    ).order_by(Nachricht.erstellt_am.desc()).all()
    
    return render_template('kommunikation/nachrichten.html', nachrichten=nachrichten)

@app.route('/nachricht/neu', methods=['GET', 'POST'])
def nachricht_neu():
    if request.method == 'POST':
        empfaenger_typ = request.form['empfaenger_typ']
        empfaenger_id = request.form['empfaenger_id']
        betreff = request.form['betreff']
        inhalt = request.form['inhalt']
        
        # TODO: Absender aus Session
        absender_typ = 'lehrer'
        absender_id = 1
        
        nachricht = Nachricht(
            absender_typ=absender_typ,
            absender_id=absender_id,
            empfaenger_typ=empfaenger_typ,
            empfaenger_id=empfaenger_id,
            betreff=betreff,
            inhalt=inhalt
        )
        
        db.session.add(nachricht)
        db.session.commit()
        flash('Nachricht erfolgreich gesendet!', 'success')
        return redirect(url_for('nachrichten_uebersicht'))
    
    # Listen für Empfängerauswahl
    lehrer = Lehrer.query.all()
    eltern = Eltern.query.all()
    schueler = Schueler.query.all()
    
    return render_template('kommunikation/nachricht_form.html',
                         lehrer=lehrer,
                         eltern=eltern,
                         schueler=schueler)

# === Berichte und Auswertungen ===

@app.route('/berichte/<int:schueler_id>')
def schueler_bericht(schueler_id):
    schueler = Schueler.query.get_or_404(schueler_id)
    
    # Noten des Schülers
    noten = Note.query.filter_by(schueler_id=schueler_id).order_by(Note.datum.desc()).all()
    
    # Notendurchschnitt pro Fach
    fach_durchschnitte = {}
    for fach in Fach.query.all():
        fach_noten = [n.note for n in noten if n.fach_id == fach.id and n.note]
        if fach_noten:
            fach_durchschnitte[fach.name] = sum(fach_noten) / len(fach_noten)
    
    # Anwesenheitsstatistik
    anwesenheiten = Anwesenheit.query.filter_by(schueler_id=schueler_id).all()
    anwesenheits_stats = {
        'anwesend': len([a for a in anwesenheiten if a.anwesend]),
        'entschuldigt': len([a for a in anwesenheiten if a.entschuldigt and not a.anwesend]),
        'unentschuldigt': len([a for a in anwesenheiten if not a.anwesend and not a.entschuldigt])
    }
    
    # Verhaltensbewertungen
    verhalten = Verhaltensbewertung.query.filter_by(schueler_id=schueler_id).order_by(Verhaltensbewertung.datum.desc()).limit(10).all()
    
    return render_template('berichte/schueler_bericht.html',
                         schueler=schueler,
                         noten=noten,
                         fach_durchschnitte=fach_durchschnitte,
                         anwesenheits_stats=anwesenheits_stats,
                         verhalten=verhalten)

# Hilfsfunktionen

def benachrichtigung_senden(empfaenger_typ, empfaenger_id, typ, titel, inhalt):
    """Hilfsfunktion zum Senden von Benachrichtigungen"""
    benachrichtigung = Benachrichtigung(
        empfaenger_typ=empfaenger_typ,
        empfaenger_id=empfaenger_id,
        typ=typ,
        titel=titel,
        inhalt=inhalt
    )
    db.session.add(benachrichtigung)
    db.session.commit()

def notendurchschnitt_berechnen(schueler_id, fach_id=None):
    """Berechnet den Notendurchschnitt eines Schülers (optional für ein Fach)"""
    query = Note.query.filter_by(schueler_id=schueler_id)
    if fach_id:
        query = query.filter_by(fach_id=fach_id)
    
    noten = [n.note for n in query.all() if n.note]
    return sum(noten) / len(noten) if noten else None

# ===== ERWEITERTE FINANZBUCHHALTUNG =====

# Hilfsfunktionen für Finanzsystem

def log_audit(benutzer_id, tabelle, datensatz_id, aktion, alte_werte=None, neue_werte=None):
    """Protokolliert alle Änderungen für Revisionssicherheit"""
    log = AuditLog(
        benutzer_id=benutzer_id,
        tabelle=tabelle,
        datensatz_id=datensatz_id,
        aktion=aktion,
        alte_werte=json.dumps(alte_werte) if alte_werte else None,
        neue_werte=json.dumps(neue_werte) if neue_werte else None,
        ip_adresse=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()

def generate_belegnummer():
    """Generiert eine eindeutige Belegnummer"""
    import uuid
    heute = datetime.date.today()
    return f"BEL-{heute.strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

def generate_rechnungsnummer():
    """Generiert eine eindeutige Rechnungsnummer"""
    heute = datetime.date.today()
    jahr = heute.year
    letzte_rechnung = Rechnung.query.filter(
        extract('year', Rechnung.datum) == jahr
    ).order_by(Rechnung.id.desc()).first()
    
    if letzte_rechnung:
        nummer = int(letzte_rechnung.rechnungsnummer.split('-')[-1]) + 1
    else:
        nummer = 1
    
    return f"RE-{jahr}-{nummer:04d}"

def generate_spenden_quittungsnummer():
    """Generiert eine eindeutige Spenden-Quittungsnummer"""
    heute = datetime.date.today()
    jahr = heute.year
    letzte_spende = Spende.query.filter(
        extract('year', Spende.spende_datum) == jahr,
        Spende.quittungsnummer.isnot(None)
    ).order_by(Spende.id.desc()).first()
    
    if letzte_spende:
        nummer = int(letzte_spende.quittungsnummer.split('-')[-1]) + 1
    else:
        nummer = 1
    
    return f"SQ-{jahr}-{nummer:04d}"

def berechne_abteilungs_saldo(abteilung_id, von_datum=None, bis_datum=None):
    """Berechnet das Saldo einer Abteilung für einen Zeitraum"""
    query = Transaction.query.filter_by(kostenstelle_id=abteilung_id)
    
    if von_datum:
        query = query.filter(Transaction.buchungsdatum >= von_datum)
    if bis_datum:
        query = query.filter(Transaction.buchungsdatum <= bis_datum)
    
    transaktionen = query.all()
    
    einnahmen = sum(t.betrag for t in transaktionen if t.typ == 'einnahme')
    ausgaben = sum(t.betrag for t in transaktionen if t.typ == 'ausgabe')
    
    return {
        'einnahmen': einnahmen,
        'ausgaben': ausgaben,
        'saldo': einnahmen - ausgaben
    }

# ===== DASHBOARD UND HAUPTSEITEN =====

@app.route('/finanzen')
def finanzen_dashboard():
    """Hauptdashboard für Finanzbuchhaltung"""
    if not session.get('benutzer_id'):
        return redirect(url_for('finanzen_login'))
    
    benutzer = Benutzer.query.get(session['benutzer_id'])
    if not benutzer or not benutzer.aktiv:
        return redirect(url_for('finanzen_login'))
    
    # Dashboard-Daten sammeln
    heute = datetime.date.today()
    monat_start = heute.replace(day=1)
    jahr_start = heute.replace(month=1, day=1)
    
    # Gesamtsaldo aller Abteilungen
    if benutzer.rolle in ['admin', 'buchhalter']:
        abteilungen = Abteilung.query.filter_by(aktiv=True).all()
    else:
        abteilungen = [benutzer.abteilung] if benutzer.abteilung else []
    
    gesamt_saldo = {'einnahmen': 0, 'ausgaben': 0, 'saldo': 0}
    monats_saldo = {'einnahmen': 0, 'ausgaben': 0, 'saldo': 0}
    
    for abteilung in abteilungen:
        # Gesamtsaldo
        saldo = berechne_abteilungs_saldo(abteilung.id)
        gesamt_saldo['einnahmen'] += saldo['einnahmen']
        gesamt_saldo['ausgaben'] += saldo['ausgaben']
        gesamt_saldo['saldo'] += saldo['saldo']
        
        # Monatssaldo
        monat_saldo = berechne_abteilungs_saldo(abteilung.id, monat_start, heute)
        monats_saldo['einnahmen'] += monat_saldo['einnahmen']
        monats_saldo['ausgaben'] += monat_saldo['ausgaben']
        monats_saldo['saldo'] += monat_saldo['saldo']
    
    # Offene Rechnungen
    offene_rechnungen = Rechnung.query.filter_by(status='offen').count()
    ueberfaellige_rechnungen = Rechnung.query.filter(
        Rechnung.status == 'offen',
        Rechnung.faelligkeitsdatum < heute
    ).count()
    
    # Letzte Transaktionen
    if benutzer.rolle in ['admin', 'buchhalter']:
        letzte_transaktionen = Transaction.query.order_by(Transaction.erstellt_am.desc()).limit(10).all()
    else:
        letzte_transaktionen = Transaction.query.filter_by(
            kostenstelle_id=benutzer.abteilung_id
        ).order_by(Transaction.erstellt_am.desc()).limit(10).all()
    
    # Wiederkehrende Buchungen, die ausgeführt werden müssen
    faellige_buchungen = WiederkehrendeBuchung.query.filter(
        WiederkehrendeBuchung.aktiv == True,
        WiederkehrendeBuchung.naechste_ausfuehrung <= heute
    ).count()
    
    return render_template('finanzen/dashboard.html',
                         benutzer=benutzer,
                         abteilungen=abteilungen,
                         gesamt_saldo=gesamt_saldo,
                         monats_saldo=monats_saldo,
                         offene_rechnungen=offene_rechnungen,
                         ueberfaellige_rechnungen=ueberfaellige_rechnungen,
                         letzte_transaktionen=letzte_transaktionen,
                         faellige_buchungen=faellige_buchungen)

@app.route('/finanzen/login', methods=['GET', 'POST'])
def finanzen_login():
    """Login für Finanzsystem"""
    if request.method == 'POST':
        benutzername = request.form['benutzername']
        passwort = request.form['passwort']
        
        benutzer = Benutzer.query.filter_by(benutzername=benutzername, aktiv=True).first()
        
        if benutzer and benutzer.check_passwort(passwort):
            session['benutzer_id'] = benutzer.id
            session['benutzer_rolle'] = benutzer.rolle
            
            # Letzten Login aktualisieren
            benutzer.letzter_login = datetime.datetime.utcnow()
            db.session.commit()
            
            flash('Erfolgreich angemeldet!', 'success')
            return redirect(url_for('finanzen_dashboard'))
        else:
            flash('Ungültige Anmeldedaten!', 'danger')
    
    return render_template('finanzen/login.html')

@app.route('/finanzen/logout')
def finanzen_logout():
    """Logout aus Finanzsystem"""
    session.pop('benutzer_id', None)
    session.pop('benutzer_rolle', None)
    flash('Erfolgreich abgemeldet!', 'info')
    return redirect(url_for('finanzen_login'))

# ===== BUCHUNGEN UND TRANSAKTIONEN =====

@app.route('/finanzen/buchungen')
def buchungen_liste():
    """Liste aller Buchungen"""
    if not session.get('benutzer_id'):
        return redirect(url_for('finanzen_login'))
    
    benutzer = Benutzer.query.get(session['benutzer_id'])
    
    # Filter
    seite = request.args.get('seite', 1, type=int)
    abteilung_id = request.args.get('abteilung_id', type=int)
    von_datum = request.args.get('von_datum')
    bis_datum = request.args.get('bis_datum')
    typ = request.args.get('typ')
    
    # Query aufbauen
    if benutzer.rolle in ['admin', 'buchhalter']:
        query = Transaction.query
    else:
        query = Transaction.query.filter_by(kostenstelle_id=benutzer.abteilung_id)
    
    if abteilung_id:
        query = query.filter_by(kostenstelle_id=abteilung_id)
    
    if von_datum:
        query = query.filter(Transaction.buchungsdatum >= datetime.datetime.strptime(von_datum, '%Y-%m-%d').date())
    
    if bis_datum:
        query = query.filter(Transaction.buchungsdatum <= datetime.datetime.strptime(bis_datum, '%Y-%m-%d').date())
    
    if typ:
        query = query.filter_by(typ=typ)
    
    # Paginierung
    buchungen = query.order_by(Transaction.buchungsdatum.desc()).paginate(
        page=seite, per_page=50, error_out=False
    )
    
    # Abteilungen für Filter
    if benutzer.rolle in ['admin', 'buchhalter']:
        abteilungen = Abteilung.query.filter_by(aktiv=True).all()
    else:
        abteilungen = [benutzer.abteilung] if benutzer.abteilung else []
    
    return render_template('finanzen/buchungen.html',
                         buchungen=buchungen,
                         abteilungen=abteilungen,
                         benutzer=benutzer)

@app.route('/finanzen/buchung/neu', methods=['GET', 'POST'])
def buchung_neu():
    """Neue Buchung erstellen"""
    if not session.get('benutzer_id'):
        return redirect(url_for('finanzen_login'))
    
    benutzer = Benutzer.query.get(session['benutzer_id'])
    
    if request.method == 'POST':
        # Formular verarbeiten
        beschreibung = request.form['beschreibung']
        betrag = Decimal(request.form['betrag'])
        typ = request.form['typ']
        kategorie = request.form.get('kategorie', '')
        buchungsdatum = datetime.datetime.strptime(request.form['buchungsdatum'], '%Y-%m-%d').date()
        zahlungsart = request.form['zahlungsart']
        kostenstelle_id = request.form['kostenstelle_id']
        verwendungszweck = request.form.get('verwendungszweck', '')
        projekt_id = request.form.get('projekt_id') or None
        
        # MwSt berechnen
        mwst_satz = Decimal(request.form.get('mwst_satz', '0'))
        if mwst_satz > 0:
            netto_betrag = betrag / (1 + mwst_satz / 100)
            mwst_betrag = betrag - netto_betrag
        else:
            netto_betrag = betrag
            mwst_betrag = Decimal('0')
        
        # Berechtigung prüfen
        if benutzer.rolle not in ['admin', 'buchhalter']:
            if int(kostenstelle_id) != benutzer.abteilung_id:
                flash('Keine Berechtigung für diese Abteilung!', 'danger')
                return redirect(url_for('buchung_neu'))
        
        # Buchung erstellen
        buchung = Transaction(
            beschreibung=beschreibung,
            betrag=betrag,
            typ=typ,
            kategorie=kategorie,
            buchungsdatum=buchungsdatum,
            zahlungsart=zahlungsart,
            kostenstelle_id=kostenstelle_id,
            verwendungszweck=verwendungszweck,
            projekt_id=projekt_id,
            belegnummer=generate_belegnummer(),
            mwst_satz=mwst_satz,
            mwst_betrag=mwst_betrag,
            netto_betrag=netto_betrag,
            erstellt_von=benutzer.id
        )
        
        # Beleg hochladen
        if 'beleg' in request.files:
            beleg = request.files['beleg']
            if beleg.filename:
                filename = secure_filename(beleg.filename)
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], 'belege')
                os.makedirs(upload_path, exist_ok=True)
                beleg_pfad = os.path.join(upload_path, f"{buchung.belegnummer}_{filename}")
                beleg.save(beleg_pfad)
                buchung.beleg_pfad = beleg_pfad
        
        db.session.add(buchung)
        db.session.commit()
        
        # Audit Log
        log_audit(benutzer.id, 'transaction', buchung.id, 'create', 
                 neue_werte={'beschreibung': beschreibung, 'betrag': str(betrag)})
        
        flash('Buchung erfolgreich erstellt!', 'success')
        return redirect(url_for('buchungen_liste'))
    
    # Abteilungen laden
    if benutzer.rolle in ['admin', 'buchhalter']:
        abteilungen = Abteilung.query.filter_by(aktiv=True).all()
    else:
        abteilungen = [benutzer.abteilung] if benutzer.abteilung else []
    
    # Projekte laden
    projekte = Projekt.query.filter_by(aktiv=True).all()
    
    return render_template('finanzen/buchung_form.html',
                         abteilungen=abteilungen,
                         projekte=projekte,
                         benutzer=benutzer)

# ===== ABTEILUNGSVERWALTUNG =====

@app.route('/finanzen/admin/abteilungen')
def abteilungen_verwalten():
    """Abteilungsverwaltung"""
    if not session.get('benutzer_id'):
        return redirect(url_for('finanzen_login'))
    
    benutzer = Benutzer.query.get(session['benutzer_id'])
    if benutzer.rolle != 'admin':
        abort(403)
    
    abteilungen = Abteilung.query.all()
    return render_template('finanzen/admin/abteilungen.html', abteilungen=abteilungen)

@app.route('/finanzen/admin/abteilung/neu', methods=['GET', 'POST'])
def abteilung_neu():
    """Neue Abteilung erstellen"""
    if not session.get('benutzer_id'):
        return redirect(url_for('finanzen_login'))
    
    benutzer = Benutzer.query.get(session['benutzer_id'])
    if benutzer.rolle != 'admin':
        abort(403)
    
    if request.method == 'POST':
        name = request.form['name']
        code = request.form['code']
        beschreibung = request.form.get('beschreibung', '')
        abteilungsleiter_id = request.form.get('abteilungsleiter_id') or None
        budget_jaehrlich = Decimal(request.form.get('budget_jaehrlich', '0'))
        
        abteilung = Abteilung(
            name=name,
            code=code,
            beschreibung=beschreibung,
            abteilungsleiter_id=abteilungsleiter_id,
            budget_jaehrlich=budget_jaehrlich
        )
        
        db.session.add(abteilung)
        db.session.commit()
        
        flash('Abteilung erfolgreich erstellt!', 'success')
        return redirect(url_for('abteilungen_verwalten'))
    
    # Verfügbare Abteilungsleiter
    leiter = Benutzer.query.filter(Benutzer.rolle.in_(['admin', 'abteilungsleiter']), Benutzer.aktiv == True).all()
    
    return render_template('finanzen/admin/abteilung_form.html', leiter=leiter)

# ===== SPENDENVERWALTUNG =====

@app.route('/finanzen/spenden')
def spenden_liste():
    """Liste aller Spenden"""
    if not session.get('benutzer_id'):
        return redirect(url_for('finanzen_login'))
    
    benutzer = Benutzer.query.get(session['benutzer_id'])
    
    # Filter
    seite = request.args.get('seite', 1, type=int)
    projekt_id = request.args.get('projekt_id', type=int)
    von_datum = request.args.get('von_datum')
    bis_datum = request.args.get('bis_datum')
    
    query = Spende.query
    
    if projekt_id:
        query = query.filter_by(projekt_id=projekt_id)
    
    if von_datum:
        query = query.filter(Spende.spende_datum >= datetime.datetime.strptime(von_datum, '%Y-%m-%d').date())
    
    if bis_datum:
        query = query.filter(Spende.spende_datum <= datetime.datetime.strptime(bis_datum, '%Y-%m-%d').date())
    
    spenden = query.order_by(Spende.spende_datum.desc()).paginate(
        page=seite, per_page=50, error_out=False
    )
    
    projekte = Projekt.query.filter_by(aktiv=True).all()
    
    return render_template('finanzen/spenden.html',
                         spenden=spenden,
                         projekte=projekte,
                         benutzer=benutzer)

@app.route('/finanzen/spende/neu', methods=['GET', 'POST'])
def spende_neu():
    """Neue Spende erfassen"""
    if not session.get('benutzer_id'):
        return redirect(url_for('finanzen_login'))
    
    benutzer = Benutzer.query.get(session['benutzer_id'])
    
    if request.method == 'POST':
        # Spender prüfen/erstellen
        spender_id = request.form.get('spender_id')
        if not spender_id:
            # Neuen Spender erstellen
            spender = Spender(
                anrede=request.form.get('anrede'),
                vorname=request.form.get('vorname'),
                nachname=request.form['nachname'],
                organisation=request.form.get('organisation'),
                strasse=request.form.get('strasse'),
                plz=request.form.get('plz'),
                ort=request.form.get('ort'),
                email=request.form.get('email'),
                telefon=request.form.get('telefon'),
                dsgvo_zustimmung=True,
                dsgvo_datum=datetime.datetime.utcnow()
            )
            db.session.add(spender)
            db.session.flush()  # Um ID zu erhalten
            spender_id = spender.id
        
        # Spende erstellen
        betrag = Decimal(request.form['betrag'])
        spende_datum = datetime.datetime.strptime(request.form['spende_datum'], '%Y-%m-%d').date()
        zahlungsart = request.form['zahlungsart']
        verwendungszweck = request.form.get('verwendungszweck', '')
        projekt_id = request.form.get('projekt_id') or None
        
        spende = Spende(
            spender_id=spender_id,
            projekt_id=projekt_id,
            betrag=betrag,
            spende_datum=spende_datum,
            zahlungsart=zahlungsart,
            verwendungszweck=verwendungszweck
        )
        
        db.session.add(spende)
        db.session.commit()
        
        flash('Spende erfolgreich erfasst!', 'success')
        return redirect(url_for('spenden_liste'))
    
    spender = Spender.query.all()
    projekte = Projekt.query.filter_by(aktiv=True).all()
    
    return render_template('finanzen/spende_form.html',
                         spender=spender,
                         projekte=projekte)

@app.route('/finanzen/spende/<int:spende_id>/quittung')
def spenden_quittung_erstellen(spende_id):
    """Spendenbescheinigung erstellen"""
    if not session.get('benutzer_id'):
        return redirect(url_for('finanzen_login'))
    
    spende = Spende.query.get_or_404(spende_id)
    
    if not spende.quittungsnummer:
        spende.quittungsnummer = generate_spenden_quittungsnummer()
        spende.quittung_datum = datetime.date.today()
        spende.quittung_erstellt = True
        db.session.commit()
    
    # PDF generieren
    pdf_pfad = erstelle_spenden_pdf(spende)
    spende.quittung_pfad = pdf_pfad
    db.session.commit()
    
    return send_file(pdf_pfad, as_attachment=True, 
                    download_name=f"Spendenbescheinigung_{spende.quittungsnummer}.pdf")

def erstelle_spenden_pdf(spende):
    """Erstellt PDF für Spendenbescheinigung"""
    filename = f"spendenbescheinigung_{spende.quittungsnummer}.pdf"
    pdf_pfad = os.path.join(app.config['UPLOAD_FOLDER'], 'spenden', filename)
    os.makedirs(os.path.dirname(pdf_pfad), exist_ok=True)
    
    doc = SimpleDocTemplate(pdf_pfad, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Header
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Center
    )
    
    story.append(Paragraph("SPENDENBESCHEINIGUNG", header_style))
    story.append(Spacer(1, 20))
    
    # Gemeinde-Info (hier sollten echte Daten stehen)
    gemeinde_info = """
    <b>Islamische Gemeinde Musterstadt e.V.</b><br/>
    Musterstraße 123<br/>
    12345 Musterstadt<br/>
    Tel: 0123/456789<br/>
    Steuernummer: 12/345/67890
    """
    story.append(Paragraph(gemeinde_info, styles['Normal']))
    story.append(Spacer(1, 30))
    
    # Spender-Info
    spender_info = f"""
    <b>Spender:</b><br/>
    {spende.spender.vollstaendiger_name}<br/>
    {spende.spender.strasse}<br/>
    {spende.spender.plz} {spende.spender.ort}
    """
    story.append(Paragraph(spender_info, styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Spenden-Details
    spenden_data = [
        ['Quittungsnummer:', spende.quittungsnummer],
        ['Spendenbetrag:', f"{spende.betrag:.2f} €"],
        ['Spendendatum:', spende.spende_datum.strftime('%d.%m.%Y')],
        ['Verwendungszweck:', spende.verwendungszweck or 'Allgemeine Spende']
    ]
    
    if spende.projekt:
        spenden_data.append(['Projekt:', spende.projekt.name])
    
    spenden_table = Table(spenden_data, colWidths=[4*cm, 10*cm])
    spenden_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    
    story.append(spenden_table)
    story.append(Spacer(1, 30))
    
    # Bestätigung
    bestaetigung = """
    Hiermit wird bestätigt, dass die oben genannte Spende ausschließlich für 
    gemeinnützige Zwecke im Sinne der Abgabenordnung verwendet wird.
    """
    story.append(Paragraph(bestaetigung, styles['Normal']))
    story.append(Spacer(1, 30))
    
    # Unterschrift
    datum_ort = f"Musterstadt, {datetime.date.today().strftime('%d.%m.%Y')}"
    story.append(Paragraph(datum_ort, styles['Normal']))
    story.append(Spacer(1, 40))
    story.append(Paragraph("_" * 40, styles['Normal']))
    story.append(Paragraph("Unterschrift Vorstand", styles['Normal']))
    
    doc.build(story)
    return pdf_pfad

# ===== RECHNUNGSSTELLUNG =====

@app.route('/finanzen/rechnungen')
def rechnungen_liste():
    """Liste aller Rechnungen"""
    if not session.get('benutzer_id'):
        return redirect(url_for('finanzen_login'))
    
    benutzer = Benutzer.query.get(session['benutzer_id'])
    
    # Filter
    seite = request.args.get('seite', 1, type=int)
    status = request.args.get('status')
    abteilung_id = request.args.get('abteilung_id', type=int)
    
    if benutzer.rolle in ['admin', 'buchhalter']:
        query = Rechnung.query
    else:
        query = Rechnung.query.filter_by(abteilung_id=benutzer.abteilung_id)
    
    if status:
        query = query.filter_by(status=status)
    
    if abteilung_id:
        query = query.filter_by(abteilung_id=abteilung_id)
    
    rechnungen = query.order_by(Rechnung.datum.desc()).paginate(
        page=seite, per_page=50, error_out=False
    )
    
    if benutzer.rolle in ['admin', 'buchhalter']:
        abteilungen = Abteilung.query.filter_by(aktiv=True).all()
    else:
        abteilungen = [benutzer.abteilung] if benutzer.abteilung else []
    
    return render_template('finanzen/rechnungen.html',
                         rechnungen=rechnungen,
                         abteilungen=abteilungen,
                         benutzer=benutzer)

@app.route('/finanzen/rechnung/neu', methods=['GET', 'POST'])
def rechnung_neu():
    """Neue Rechnung erstellen"""
    if not session.get('benutzer_id'):
        return redirect(url_for('finanzen_login'))
    
    benutzer = Benutzer.query.get(session['benutzer_id'])
    
    if request.method == 'POST':
        # Rechnung erstellen
        kunde_name = request.form['kunde_name']
        kunde_strasse = request.form.get('kunde_strasse', '')
        kunde_plz = request.form.get('kunde_plz', '')
        kunde_ort = request.form.get('kunde_ort', '')
        kunde_email = request.form.get('kunde_email', '')
        
        datum = datetime.datetime.strptime(request.form['datum'], '%Y-%m-%d').date()
        zahlungsziel = int(request.form.get('zahlungsziel', 14))
        faelligkeitsdatum = datum + datetime.timedelta(days=zahlungsziel)
        
        abteilung_id = request.form['abteilung_id']
        verwendungszweck = request.form.get('verwendungszweck', '')
        bemerkung = request.form.get('bemerkung', '')
        
        # Berechtigung prüfen
        if benutzer.rolle not in ['admin', 'buchhalter']:
            if int(abteilung_id) != benutzer.abteilung_id:
                flash('Keine Berechtigung für diese Abteilung!', 'danger')
                return redirect(url_for('rechnung_neu'))
        
        rechnung = Rechnung(
            rechnungsnummer=generate_rechnungsnummer(),
            datum=datum,
            faelligkeitsdatum=faelligkeitsdatum,
            kunde_name=kunde_name,
            kunde_strasse=kunde_strasse,
            kunde_plz=kunde_plz,
            kunde_ort=kunde_ort,
            kunde_email=kunde_email,
            abteilung_id=abteilung_id,
            verwendungszweck=verwendungszweck,
            bemerkung=bemerkung,
            netto_betrag=Decimal('0'),
            mwst_betrag=Decimal('0'),
            brutto_betrag=Decimal('0'),
            erstellt_von=benutzer.id
        )
        
        db.session.add(rechnung)
        db.session.flush()  # Um ID zu erhalten
        
        # Positionen verarbeiten
        positionen = request.form.getlist('positionen')
        mengen = request.form.getlist('mengen')
        einheiten = request.form.getlist('einheiten')
        einzelpreise = request.form.getlist('einzelpreise')
        mwst_saetze = request.form.getlist('mwst_saetze')
        
        netto_gesamt = Decimal('0')
        mwst_gesamt = Decimal('0')
        
        for i, beschreibung in enumerate(positionen):
            if beschreibung.strip():
                menge = Decimal(mengen[i])
                einzelpreis = Decimal(einzelpreise[i])
                mwst_satz = Decimal(mwst_saetze[i])
                
                position = RechnungsPosition(
                    rechnung_id=rechnung.id,
                    position=i + 1,
                    beschreibung=beschreibung,
                    menge=menge,
                    einheit=einheiten[i],
                    einzelpreis=einzelpreis,
                    mwst_satz=mwst_satz
                )
                
                db.session.add(position)
                
                netto_gesamt += position.netto_betrag
                mwst_gesamt += position.mwst_betrag
        
        # Rechnung aktualisieren
        rechnung.netto_betrag = netto_gesamt
        rechnung.mwst_betrag = mwst_gesamt
        rechnung.brutto_betrag = netto_gesamt + mwst_gesamt
        
        db.session.commit()
        
        flash('Rechnung erfolgreich erstellt!', 'success')
        return redirect(url_for('rechnungen_liste'))
    
    # Abteilungen laden
    if benutzer.rolle in ['admin', 'buchhalter']:
        abteilungen = Abteilung.query.filter_by(aktiv=True).all()
    else:
        abteilungen = [benutzer.abteilung] if benutzer.abteilung else []
    
    return render_template('finanzen/rechnung_form.html',
                         abteilungen=abteilungen,
                         benutzer=benutzer)

@app.route('/finanzen/rechnung/<int:rechnung_id>/pdf')
def rechnung_pdf_erstellen(rechnung_id):
    """Rechnung als PDF erstellen"""
    if not session.get('benutzer_id'):
        return redirect(url_for('finanzen_login'))
    
    rechnung = Rechnung.query.get_or_404(rechnung_id)
    
    # PDF generieren
    pdf_pfad = erstelle_rechnungs_pdf(rechnung)
    rechnung.pdf_pfad = pdf_pfad
    db.session.commit()
    
    return send_file(pdf_pfad, as_attachment=True, 
                    download_name=f"Rechnung_{rechnung.rechnungsnummer}.pdf")

def erstelle_rechnungs_pdf(rechnung):
    """Erstellt PDF für Rechnung"""
    filename = f"rechnung_{rechnung.rechnungsnummer}.pdf"
    pdf_pfad = os.path.join(app.config['UPLOAD_FOLDER'], 'rechnungen', filename)
    os.makedirs(os.path.dirname(pdf_pfad), exist_ok=True)
    
    doc = SimpleDocTemplate(pdf_pfad, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Header mit Logo-Platzhalter
    header_data = [
        ["ISLAMISCHE GEMEINDE MUSTERSTADT E.V.", ""],
        ["Musterstraße 123", f"Rechnung Nr.: {rechnung.rechnungsnummer}"],
        ["12345 Musterstadt", f"Datum: {rechnung.datum.strftime('%d.%m.%Y')}"],
        ["Tel: 0123/456789", f"Fällig: {rechnung.faelligkeitsdatum.strftime('%d.%m.%Y')}"]
    ]
    
    header_table = Table(header_data, colWidths=[10*cm, 8*cm])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 30))
    
    # Kundenadresse
    kunde_adresse = f"""
    <b>{rechnung.kunde_name}</b><br/>
    {rechnung.kunde_strasse}<br/>
    {rechnung.kunde_plz} {rechnung.kunde_ort}
    """
    story.append(Paragraph(kunde_adresse, styles['Normal']))
    story.append(Spacer(1, 30))
    
    # Rechnungspositionen
    pos_data = [['Pos.', 'Beschreibung', 'Menge', 'Einheit', 'Einzelpreis', 'MwSt.', 'Betrag']]
    
    for position in rechnung.positionen:
        pos_data.append([
            str(position.position),
            position.beschreibung,
            f"{position.menge:.2f}",
            position.einheit,
            f"{position.einzelpreis:.2f} €",
            f"{position.mwst_satz:.0f}%",
            f"{position.brutto_betrag:.2f} €"
        ])
    
    # Summen
    pos_data.extend([
        ['', '', '', '', '', 'Netto:', f"{rechnung.netto_betrag:.2f} €"],
        ['', '', '', '', '', 'MwSt.:', f"{rechnung.mwst_betrag:.2f} €"],
        ['', '', '', '', '', 'Gesamt:', f"{rechnung.brutto_betrag:.2f} €"]
    ])
    
    pos_table = Table(pos_data, colWidths=[1*cm, 6*cm, 2*cm, 2*cm, 2.5*cm, 1.5*cm, 3*cm])
    pos_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -4), 1, colors.black),
        ('LINEBELOW', (4, -3), (-1, -1), 1, colors.black),
        ('FONTNAME', (5, -3), (-1, -1), 'Helvetica-Bold'),
    ]))
    
    story.append(pos_table)
    story.append(Spacer(1, 30))
    
    # Zahlungshinweise
    if rechnung.verwendungszweck:
        story.append(Paragraph(f"<b>Verwendungszweck:</b> {rechnung.verwendungszweck}", styles['Normal']))
    
    zahlungshinweis = """
    <b>Zahlungshinweise:</b><br/>
    Bitte überweisen Sie den Betrag bis zum Fälligkeitsdatum unter Angabe der Rechnungsnummer.
    """
    story.append(Paragraph(zahlungshinweis, styles['Normal']))
    
    if rechnung.bemerkung:
        story.append(Spacer(1, 20))
        story.append(Paragraph(f"<b>Bemerkung:</b> {rechnung.bemerkung}", styles['Normal']))
    
    doc.build(story)
    return pdf_pfad

# ===== BERICHTE UND AUSWERTUNGEN =====

@app.route('/finanzen/berichte')
def berichte_uebersicht():
    """Übersicht der verfügbaren Berichte"""
    if not session.get('benutzer_id'):
        return redirect(url_for('finanzen_login'))
    
    benutzer = Benutzer.query.get(session['benutzer_id'])
    
    return render_template('finanzen/berichte.html', benutzer=benutzer)

@app.route('/finanzen/bericht/jahresabschluss')
def jahresabschluss():
    """Jahresabschluss-Bericht"""
    if not session.get('benutzer_id'):
        return redirect(url_for('finanzen_login'))
    
    benutzer = Benutzer.query.get(session['benutzer_id'])
    
    jahr = request.args.get('jahr', datetime.date.today().year, type=int)
    abteilung_id = request.args.get('abteilung_id', type=int)
    
    jahr_start = datetime.date(jahr, 1, 1)
    jahr_ende = datetime.date(jahr, 12, 31)
    
    # Abteilungen bestimmen
    if benutzer.rolle in ['admin', 'buchhalter']:
        if abteilung_id:
            abteilungen = [Abteilung.query.get(abteilung_id)]
        else:
            abteilungen = Abteilung.query.filter_by(aktiv=True).all()
    else:
        abteilungen = [benutzer.abteilung] if benutzer.abteilung else []
    
    # Berichte erstellen
    abteilungs_berichte = []
    gesamt_einnahmen = Decimal('0')
    gesamt_ausgaben = Decimal('0')
    
    for abteilung in abteilungen:
        saldo = berechne_abteilungs_saldo(abteilung.id, jahr_start, jahr_ende)
        
        # Monatliche Aufschlüsselung
        monats_daten = []
        for monat in range(1, 13):
            monat_start = datetime.date(jahr, monat, 1)
            if monat == 12:
                monat_ende = datetime.date(jahr + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                monat_ende = datetime.date(jahr, monat + 1, 1) - datetime.timedelta(days=1)
            
            monat_saldo = berechne_abteilungs_saldo(abteilung.id, monat_start, monat_ende)
            monats_daten.append({
                'monat': monat,
                'monat_name': datetime.date(jahr, monat, 1).strftime('%B'),
                'einnahmen': monat_saldo['einnahmen'],
                'ausgaben': monat_saldo['ausgaben'],
                'saldo': monat_saldo['saldo']
            })
        
        abteilungs_berichte.append({
            'abteilung': abteilung,
            'einnahmen': saldo['einnahmen'],
            'ausgaben': saldo['ausgaben'],
            'saldo': saldo['saldo'],
            'monate': monats_daten
        })
        
        gesamt_einnahmen += saldo['einnahmen']
        gesamt_ausgaben += saldo['ausgaben']
    
    # Verfügbare Abteilungen für Filter
    if benutzer.rolle in ['admin', 'buchhalter']:
        alle_abteilungen = Abteilung.query.filter_by(aktiv=True).all()
    else:
        alle_abteilungen = [benutzer.abteilung] if benutzer.abteilung else []
    
    return render_template('finanzen/jahresabschluss.html',
                         abteilungs_berichte=abteilungs_berichte,
                         jahr=jahr,
                         gesamt_einnahmen=gesamt_einnahmen,
                         gesamt_ausgaben=gesamt_ausgaben,
                         gesamt_saldo=gesamt_einnahmen - gesamt_ausgaben,
                         alle_abteilungen=alle_abteilungen,
                         ausgewaehlte_abteilung=abteilung_id,
                         benutzer=benutzer)

# === Vertretungsplan ===

@app.route('/vertretung/<int:klasse_id>')
def vertretungsplan(klasse_id):
    klasse = Klasse.query.get_or_404(klasse_id)
    heute = datetime.date.today()
    
    # Vertretungen für die nächsten 7 Tage
    naechste_woche = heute + datetime.timedelta(days=7)
    vertretungen = Vertretung.query.filter(
        Vertretung.klasse_id == klasse_id,
        Vertretung.datum >= heute,
        Vertretung.datum <= naechste_woche
    ).order_by(Vertretung.datum, Vertretung.stunde).all()
    
    return render_template('vertretung/plan.html', klasse=klasse, vertretungen=vertretungen)

@app.route('/admin/vertretung/neu', methods=['GET', 'POST'])
def vertretung_neu():
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
        
    if request.method == 'POST':
        datum = datetime.datetime.strptime(request.form['datum'], '%Y-%m-%d').date()
        stunde = int(request.form['stunde'])
        klasse_id = request.form['klasse_id']
        original_lehrer_id = request.form['original_lehrer_id']
        vertretung_lehrer_id = request.form.get('vertretung_lehrer_id')
        fach_id = request.form['fach_id']
        art = request.form['art']
        raum = request.form.get('raum', '')
        bemerkung = request.form.get('bemerkung', '')
        
        vertretung = Vertretung(
            datum=datum,
            stunde=stunde,
            klasse_id=klasse_id,
            original_lehrer_id=original_lehrer_id,
            vertretung_lehrer_id=vertretung_lehrer_id if vertretung_lehrer_id else None,
            fach_id=fach_id,
            art=art,
            raum=raum,
            bemerkung=bemerkung
        )
        
        db.session.add(vertretung)
        db.session.commit()
        
        # Benachrichtigungen senden
        klasse = Klasse.query.get(klasse_id)
        for schueler in klasse.schueler:
            if schueler.eltern_id:
                benachrichtigung_senden(
                    'eltern', schueler.eltern_id, 'vertretung',
                    f'Vertretung in Klasse {klasse.name}',
                    f'Am {datum.strftime("%d.%m.%Y")} in der {stunde}. Stunde: {art}'
                )
        
        flash('Vertretung erfolgreich erstellt!', 'success')
        return redirect(url_for('vertretungsplan', klasse_id=klasse_id))
    
    klassen = Klasse.query.all()
    lehrer = Lehrer.query.all()
    faecher = Fach.query.all()
    
    return render_template('vertretung/form.html', 
                         klassen=klassen, 
                         lehrer=lehrer, 
                         faecher=faecher)

# === Bewertungstypen-Verwaltung ===

@app.route('/admin/bewertungstypen')
def bewertungstypen_verwalten():
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    bewertungstypen = Bewertungstyp.query.all()
    return render_template('admin/bewertungstypen.html', bewertungstypen=bewertungstypen)

@app.route('/admin/bewertungstyp/neu', methods=['GET', 'POST'])
def bewertungstyp_neu():
    if not session.get('admin'):
        return redirect(url_for('blog_admin_login'))
    if request.method == 'POST':
        name = request.form['name']
        gewichtung = float(request.form.get('gewichtung', 1.0))
        beschreibung = request.form.get('beschreibung', '')
        
        bewertungstyp = Bewertungstyp(name=name, gewichtung=gewichtung, beschreibung=beschreibung)
        db.session.add(bewertungstyp)
        db.session.commit()
        flash('Bewertungstyp erfolgreich erstellt!', 'success')
        return redirect(url_for('bewertungstypen_verwalten'))
    
    return render_template('admin/bewertungstyp_form.html')

# === Portfolio und Lernziele ===

@app.route('/portfolio/<int:schueler_id>')
def portfolio_anzeigen(schueler_id):
    schueler = Schueler.query.get_or_404(schueler_id)
    portfolios = Portfolio.query.filter_by(schueler_id=schueler_id).order_by(Portfolio.erstellt_am.desc()).all()
    return render_template('portfolio/anzeigen.html', schueler=schueler, portfolios=portfolios)

@app.route('/portfolio/neu', methods=['GET', 'POST'])
def portfolio_neu():
    if request.method == 'POST':
        schueler_id = request.form['schueler_id']
        titel = request.form['titel']
        beschreibung = request.form.get('beschreibung', '')
        fach_id = request.form.get('fach_id')
        typ = request.form.get('typ', 'projekt')
        oeffentlich = 'oeffentlich' in request.form
        
        # Datei-Upload verarbeiten
        datei_pfad = None
        if 'datei' in request.files:
            datei = request.files['datei']
            if datei.filename:
                filename = secure_filename(datei.filename)
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], 'portfolio')
                os.makedirs(upload_path, exist_ok=True)
                datei_pfad = os.path.join(upload_path, filename)
                datei.save(datei_pfad)
        
        portfolio = Portfolio(
            schueler_id=schueler_id,
            titel=titel,
            beschreibung=beschreibung,
            fach_id=fach_id if fach_id else None,
            datei_pfad=datei_pfad,
            typ=typ,
            oeffentlich=oeffentlich
        )
        
        db.session.add(portfolio)
        db.session.commit()
        flash('Portfolio-Eintrag erfolgreich erstellt!', 'success')
        return redirect(url_for('portfolio_anzeigen', schueler_id=schueler_id))
    
    schueler_id = request.args.get('schueler_id')
    schueler = Schueler.query.get_or_404(schueler_id) if schueler_id else None
    alle_schueler = Schueler.query.all()
    faecher = Fach.query.all()
    
    return render_template('portfolio/form.html', 
                         schueler=schueler, 
                         alle_schueler=alle_schueler,
                         faecher=faecher)

@app.route('/lernziele/<int:klasse_id>')
def lernziele_uebersicht(klasse_id):
    klasse = Klasse.query.get_or_404(klasse_id)
    lernziele = Lernziel.query.filter_by(klasse_id=klasse_id).order_by(Lernziel.erstellt_am.desc()).all()
    
    # Fortschritte für jeden Schüler laden
    fortschritte = {}
    for lernziel in lernziele:
        fortschritte[lernziel.id] = {}
        for schueler in klasse.schueler:
            fortschritt = LernzielFortschritt.query.filter_by(
                lernziel_id=lernziel.id, 
                schueler_id=schueler.id
            ).first()
            fortschritte[lernziel.id][schueler.id] = fortschritt.fortschritt if fortschritt else 0
    
    return render_template('lernziele/uebersicht.html', 
                         klasse=klasse, 
                         lernziele=lernziele, 
                         fortschritte=fortschritte)

# === Verhaltensbeobachtungen ===

@app.route('/verhalten/<int:schueler_id>')
def verhalten_uebersicht(schueler_id):
    schueler = Schueler.query.get_or_404(schueler_id)
    bewertungen = Verhaltensbewertung.query.filter_by(schueler_id=schueler_id).order_by(Verhaltensbewertung.datum.desc()).all()
    return render_template('verhalten/uebersicht.html', schueler=schueler, bewertungen=bewertungen)

@app.route('/verhalten/neu', methods=['GET', 'POST'])
def verhalten_neu():
    if request.method == 'POST':
        schueler_id = request.form['schueler_id']
        datum = datetime.datetime.strptime(request.form['datum'], '%Y-%m-%d').date()
        kategorie = request.form['kategorie']
        beschreibung = request.form['beschreibung']
        massnahme = request.form.get('massnahme', '')
        lehrer_id = 1  # TODO: Aus Session
        
        bewertung = Verhaltensbewertung(
            schueler_id=schueler_id,
            lehrer_id=lehrer_id,
            datum=datum,
            kategorie=kategorie,
            beschreibung=beschreibung,
            massnahme=massnahme
        )
        
        db.session.add(bewertung)
        db.session.commit()
        
        # Benachrichtigung an Eltern bei negativem Verhalten
        if kategorie == 'negativ':
            schueler = Schueler.query.get(schueler_id)
            if schueler.eltern_id:
                benachrichtigung_senden(
                    'eltern', schueler.eltern_id, 'verhalten',
                    'Verhaltensbeobachtung',
                    f'Verhaltensbeobachtung für {schueler.name}: {beschreibung}'
                )
        
        flash('Verhaltensbewertung erfolgreich erstellt!', 'success')
        return redirect(url_for('verhalten_uebersicht', schueler_id=schueler_id))
    
    schueler_id = request.args.get('schueler_id')
    schueler = Schueler.query.get_or_404(schueler_id) if schueler_id else None
    alle_schueler = Schueler.query.all()
    
    return render_template('verhalten/form.html', schueler=schueler, alle_schueler=alle_schueler)

# === Erweiterte Klassenbuch-Übersicht ===

@app.route('/klassenbuch_erweitert/<int:klasse_id>')
def klassenbuch_erweitert(klasse_id):
    klasse = Klasse.query.get_or_404(klasse_id)
    
    # Dashboard-Daten sammeln
    schueler_anzahl = len(klasse.schueler)
    aktuelle_hausaufgaben = Hausaufgabe.query.filter(
        Hausaufgabe.klasse_id == klasse_id,
        Hausaufgabe.faellig_am >= datetime.date.today()
    ).count()
    
    # Letzte Unterrichtseinheiten
    letzte_stunden = Unterrichtseinheit.query.filter_by(klasse_id=klasse_id).order_by(
        Unterrichtseinheit.datum.desc()
    ).limit(5).all()
    
    # Anwesenheitsstatistik der letzten 30 Tage
    vor_30_tagen = datetime.date.today() - datetime.timedelta(days=30)
    anwesenheiten = db.session.query(Anwesenheit).join(Unterrichtseinheit).filter(
        Unterrichtseinheit.klasse_id == klasse_id,
        Unterrichtseinheit.datum >= vor_30_tagen
    ).all()
    
    anwesenheits_stats = {
        'anwesend': len([a for a in anwesenheiten if a.anwesend]),
        'entschuldigt': len([a for a in anwesenheiten if a.entschuldigt and not a.anwesend]),
        'unentschuldigt': len([a for a in anwesenheiten if not a.anwesend and not a.entschuldigt])
    }
    
    # Kommende Termine
    heute = datetime.date.today()
    naechste_woche = heute + datetime.timedelta(days=7)
    kommende_termine = []
    
    # Hausaufgaben
    hausaufgaben = Hausaufgabe.query.filter(
        Hausaufgabe.klasse_id == klasse_id,
        Hausaufgabe.faellig_am >= heute,
        Hausaufgabe.faellig_am <= naechste_woche
    ).all()
    for ha in hausaufgaben:
        kommende_termine.append({
            'typ': 'Hausaufgabe',
            'titel': ha.titel,
            'datum': ha.faellig_am,
            'fach': ha.fach.name if ha.fach else ''
        })
    
    # Prüfungen
    pruefungen = Pruefung.query.filter(
        Pruefung.klasse_id == klasse_id,
        Pruefung.datum >= heute,
        Pruefung.datum <= naechste_woche
    ).all()
    for p in pruefungen:
        kommende_termine.append({
            'typ': 'Prüfung',
            'titel': p.titel,
            'datum': p.datum,
            'fach': p.fach.name if p.fach else ''
        })
    
    # Vertretungen
    vertretungen = Vertretung.query.filter(
        Vertretung.klasse_id == klasse_id,
        Vertretung.datum >= heute,
        Vertretung.datum <= naechste_woche
    ).all()
    for v in vertretungen:
        kommende_termine.append({
            'typ': 'Vertretung',
            'titel': f'{v.stunde}. Stunde - {v.art}',
            'datum': v.datum,
            'fach': v.fach.name if v.fach else ''
        })
    
    # Nach Datum sortieren
    kommende_termine.sort(key=lambda x: x['datum'])
    
    return render_template('klassenbuch/erweitert.html',
                         klasse=klasse,
                         schueler_anzahl=schueler_anzahl,
                         aktuelle_hausaufgaben=aktuelle_hausaufgaben,
                         letzte_stunden=letzte_stunden,
                         anwesenheits_stats=anwesenheits_stats,
                         kommende_termine=kommende_termine)

# Datenbank initialisieren
@app.before_first_request
def create_tables():
    db.create_all()
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=3000)