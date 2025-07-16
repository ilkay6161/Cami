from flask import Flask, render_template, request, redirect, url_for, jsonify, abort, send_file, session, flash
import datetime
import json
import os
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
from sqlalchemy import func

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
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float)
    type = db.Column(db.String(50), nullable=False) # 'Einnahme', 'Ausgabe', 'note'
    category = db.Column(db.String(100))
    date = db.Column(db.Date, nullable=False)
    cost_center_id = db.Column(db.Integer, db.ForeignKey('cost_center.id'), nullable=True)
    process_id = db.Column(db.Integer, db.ForeignKey('process.id'), nullable=True)
    document_filename = db.Column(db.String(255), nullable=True)
    # Add other fields if you have them, like 'is_approved', 'accounting_circle'
    is_approved = db.Column(db.Boolean, default=False)
    accounting_circle = db.Column(db.String(100), default='Hauptbuch')


    def __repr__(self):
        return f"<Transaction {self.description}>"

# MODELS
class Klasse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    schuljahr = db.Column(db.String(9), nullable=False)
    schueler = db.relationship('Schueler', backref='klasse', lazy=True)
    unterrichtseinheiten = db.relationship('Unterrichtseinheit', backref='klasse', lazy=True)

class Schueler(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    nachname = db.Column(db.String(50), nullable=False)
    geburtsdatum = db.Column(db.Date)
    geschlecht = db.Column(db.String(1))
    klasse_id = db.Column(db.Integer, db.ForeignKey('klasse.id'), nullable=False)

class Unterrichtseinheit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datum = db.Column(db.Date, nullable=False)
    stunden = db.Column(db.String(10), nullable=False)
    thema = db.Column(db.String(100), nullable=False)
    inhalte = db.Column(db.Text)
    bemerkung = db.Column(db.Text)
    klasse_id = db.Column(db.Integer, db.ForeignKey('klasse.id'), nullable=False)

class Anwesenheit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schueler_id = db.Column(db.Integer, db.ForeignKey('schueler.id'), nullable=False)
    unterrichtseinheit_id = db.Column(db.Integer, db.ForeignKey('unterrichtseinheit.id'), nullable=False)
    anwesend = db.Column(db.Boolean, default=False)
    entschuldigt = db.Column(db.Boolean, default=False)

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


# Datenbank initialisieren
@app.before_first_request
def create_tables():
    db.create_all()
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=3000)