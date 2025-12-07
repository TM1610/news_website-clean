from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, Response
import mysql.connector
import io
import csv
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from werkzeug.security import generate_password_hash, check_password_hash
from config import DB_CONFIG, SECRET_KEY, DEBUG, HEADLINES_PER_PAGE
from scraper import scrape_all_sources
from datetime import datetime

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['DEBUG'] = DEBUG

# Database connection
def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# ==================== HOME PAGE ====================
@app.route('/')
def index():
    # Log visit to analytics
    try:
        log_visit("Homepage")
    except Exception:
        pass
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Get page number and category filter
    page = request.args.get('page', 1, type=int)
    category_filter = request.args.get('category', None)
    offset = (page - 1) * HEADLINES_PER_PAGE
    
    # Get all categories for filter buttons
    cursor.execute("SELECT * FROM categories ORDER BY category_name")
    categories = cursor.fetchall()
    
    # Build query based on category filter
    if category_filter:
        count_query = "SELECT COUNT(*) as total FROM news_headlines h JOIN categories c ON h.category_id = c.category_id WHERE c.category_name = %s"
        cursor.execute(count_query, (category_filter,))
        total = cursor.fetchone()['total']
        
        query = """
            SELECT h.*, s.source_name, c.category_name, c.category_icon
            FROM news_headlines h
            JOIN news_sources s ON h.source_id = s.source_id
            JOIN categories c ON h.category_id = c.category_id
            WHERE c.category_name = %s
            ORDER BY h.publish_date DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, (category_filter, HEADLINES_PER_PAGE, offset))
    else:
        # Get total count
        cursor.execute("SELECT COUNT(*) as total FROM news_headlines")
        total = cursor.fetchone()['total']
        
        # Get headlines with source and category info
        query = """
            SELECT h.*, s.source_name, c.category_name, c.category_icon
            FROM news_headlines h
            JOIN news_sources s ON h.source_id = s.source_id
            JOIN categories c ON h.category_id = c.category_id
            ORDER BY h.publish_date DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, (HEADLINES_PER_PAGE, offset))
    
    headlines = cursor.fetchall()
    total_pages = (total + HEADLINES_PER_PAGE - 1) // HEADLINES_PER_PAGE
    
    cursor.close()
    conn.close()
    
    return render_template('index.html', 
                         headlines=headlines, 
                         categories=categories,
                         current_category=category_filter,
                         page=page, 
                         total_pages=total_pages)

# ==================== REGISTER ====================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Hash password
        hashed_pw = generate_password_hash(password)
         
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                (username, email, hashed_pw)
            )
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash('Username or email already exists!', 'error')
        finally:
            cursor.close()
            conn.close()
    
    return render_template('register.html')

# ==================== LOGIN ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Log visit
    try:
        log_visit("Login Page")
    except Exception:
        pass
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password!', 'error')
    
    return render_template('login.html')

# ==================== LOGOUT ====================
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# ==================== ADD TO FAVORITES ====================
@app.route('/favorite/<int:headline_id>', methods=['POST'])
def add_favorite(headline_id):
    if 'user_id' not in session:
        flash('Please login to save favorites!', 'error')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO favorites (user_id, headline_id) VALUES (%s, %s)",
            (user_id, headline_id)
        )
        conn.commit()
        flash('Added to favorites!', 'success')
    except mysql.connector.IntegrityError:
        flash('Already in favorites!', 'info')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(request.referrer or url_for('index'))

# ==================== REMOVE FROM FAVORITES ====================
@app.route('/unfavorite/<int:headline_id>', methods=['POST'])
def remove_favorite(headline_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "DELETE FROM favorites WHERE user_id = %s AND headline_id = %s",
        (user_id, headline_id)
    )
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Removed from favorites!', 'info')
    return redirect(request.referrer or url_for('favorites'))

# ==================== MY FAVORITES ====================
@app.route('/favorites')
def favorites():
    # Log visit
    try:
        log_visit("Favorites")
    except Exception:
        pass
    if 'user_id' not in session:
        flash('Please login to view favorites!', 'error')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Get category filter
    category_filter = request.args.get('category', None)
    
    # Get all categories for filter buttons
    cursor.execute("SELECT * FROM categories ORDER BY category_name")
    categories = cursor.fetchall()
    
    # Build query based on category filter
    if category_filter:
        query = """
            SELECT h.*, s.source_name, c.category_name, c.category_icon, f.saved_at
            FROM favorites f
            JOIN news_headlines h ON f.headline_id = h.headline_id
            JOIN news_sources s ON h.source_id = s.source_id
            JOIN categories c ON h.category_id = c.category_id
            WHERE f.user_id = %s AND c.category_name = %s
            ORDER BY f.saved_at DESC
        """
        cursor.execute(query, (user_id, category_filter))
    else:
        query = """
            SELECT h.*, s.source_name, c.category_name, c.category_icon, f.saved_at
            FROM favorites f
            JOIN news_headlines h ON f.headline_id = h.headline_id
            JOIN news_sources s ON h.source_id = s.source_id
            JOIN categories c ON h.category_id = c.category_id
            WHERE f.user_id = %s
            ORDER BY f.saved_at DESC
        """
        cursor.execute(query, (user_id,))
    
    headlines = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('favorites.html', 
                         headlines=headlines,
                         categories=categories,
                         current_category=category_filter)

# ==================== CATEGORY STATS ====================
@app.route('/categories')
def category_stats():
    # Log visit
    try:
        log_visit("Category Stats")
    except Exception:
        pass
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT c.category_name, c.category_icon, COUNT(h.headline_id) as count
        FROM categories c
        LEFT JOIN news_headlines h ON c.category_id = h.category_id
        GROUP BY c.category_id
        ORDER BY count DESC
    """
    cursor.execute(query)
    stats = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('categories.html', stats=stats)

# ==================== SCRAPE NEWS (ADMIN) ====================
@app.route('/scrape')
def scrape():
    # Log visit
    try:
        log_visit("Scrape")
    except Exception:
        pass
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect(url_for('login'))
    
    # Run scraper
    try:
        scrape_all_sources()
        flash('News scraped successfully!', 'success')
    except Exception as e:
        flash(f'Error scraping news: {str(e)}', 'error')
    
    return redirect(url_for('index'))

# ==================== CHECK IF FAVORITED ====================
@app.template_filter('is_favorited')
def is_favorited(headline_id):
    if 'user_id' not in session:
        return False
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM favorites WHERE user_id = %s AND headline_id = %s",
        (session['user_id'], headline_id)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result is not None


@app.template_filter('timesince')
def timesince(dt):
    """Return a short human-friendly relative time (e.g. '2h ago') for a datetime.

    If `dt` is a string and can't be parsed with fromisoformat, the original
    string is returned.
    """
    if not dt:
        return ''

    # If the value is a string, try ISO format parsing first
    if isinstance(dt, str):
        try:
            dt_obj = datetime.fromisoformat(dt)
        except Exception:
            # Could not parse; return raw string
            return dt
    else:
        dt_obj = dt

    # Use naive UTC/Local difference depending on dt_obj tzinfo
    now = datetime.utcnow()
    try:
        if getattr(dt_obj, 'tzinfo', None):
            # If dt_obj has tzinfo, compare in its zone to avoid errors
            now = datetime.now(dt_obj.tzinfo)
    except Exception:
        pass

    delta = now - dt_obj
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 7:
        return f"{days}d ago"
    # Older than a week — show a date
    return dt_obj.strftime('%b %d, %Y')


# ==================== VISITOR LOGGING ====================
def log_visit(page_name):
    """Record a visitor action into the visit_logs table."""
    try:
        ip = request.remote_addr
    except Exception:
        ip = None
    user_id = session.get('user_id')

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO visit_logs (user_id, ip_address, visited_page) VALUES (%s, %s, %s)",
            (user_id, ip, page_name)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


# ==================== REPORT DOWNLOADS ====================
@app.route('/download/visitors/csv')
def download_visitors_csv():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, ip_address, visited_page, visited_at FROM visit_logs ORDER BY visited_at DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'User ID', 'IP Address', 'Page', 'Visited At'])
    for r in rows:
        cw.writerow(r)

    output = si.getvalue()
    return Response(output, mimetype='text/csv', headers={
        'Content-Disposition': 'attachment; filename=visitors_report.csv'
    })


@app.route('/download/visitors/excel')
def download_visitors_excel():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, ip_address, visited_page, visited_at FROM visit_logs ORDER BY visited_at DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    wb = Workbook()
    ws = wb.active
    ws.title = 'Visitors'
    ws.append(['ID', 'User ID', 'IP Address', 'Page', 'Visited At'])
    for r in rows:
        # If visited_at is datetime-like, keep as string
        ws.append([r[0], r[1], r[2], r[3], str(r[4])])

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return send_file(bio, as_attachment=True, download_name='visitors_report.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.route('/download/visitors/pdf')
def download_visitors_pdf():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, ip_address, visited_page, visited_at FROM visit_logs ORDER BY visited_at DESC LIMIT 50")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    p.setFont('Helvetica-Bold', 16)
    p.drawString(72, height - 72, 'Visitors Report (Last 50 Visits)')
    p.setFont('Helvetica', 10)
    y = height - 100
    line_height = 14

    for r in rows:
        text = f"{r[0]} | user:{r[1]} | {r[2]} | {r[3]} | {r[4]}"
        p.drawString(72, y, text)
        y -= line_height
        if y < 72:
            p.showPage()
            p.setFont('Helvetica', 10)
            y = height - 72

    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='visitors_report.pdf', mimetype='application/pdf')


@app.route('/reports')
def reports():
    # Simple reports dashboard
    try:
        log_visit('Reports Page')
    except Exception:
        pass
    return render_template('reports.html')

if __name__ == '__main__':
    app.run(debug=DEBUG)