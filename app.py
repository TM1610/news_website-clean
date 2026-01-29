from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import psycopg2
import psycopg2.extras
import io
from openpyxl import Workbook
from datetime import datetime

from config import DB_CONFIG, SECRET_KEY, DEBUG, HEADLINES_PER_PAGE
from scraper import scrape_all_sources

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['DEBUG'] = DEBUG


# ==================== DATABASE CONNECTION ====================
def get_db():
    return psycopg2.connect(**DB_CONFIG)


# ==================== HOME PAGE ====================
@app.route('/')
def index():
    try:
        log_visit("Homepage")
    except Exception:
        pass

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    page = request.args.get('page', 1, type=int)
    category_filter = request.args.get('category')
    offset = (page - 1) * HEADLINES_PER_PAGE

    cursor.execute("SELECT * FROM categories ORDER BY category_name")
    categories = cursor.fetchall()

    if category_filter:
        cursor.execute(
            """SELECT COUNT(*) AS total
               FROM news_headlines h
               JOIN categories c ON h.category_id = c.category_id
               WHERE c.category_name = %s""",
            (category_filter,)
        )
        total = cursor.fetchone()['total']

        cursor.execute(
            """SELECT h.*, s.source_name, c.category_name, c.category_icon
               FROM news_headlines h
               JOIN news_sources s ON h.source_id = s.source_id
               JOIN categories c ON h.category_id = c.category_id
               WHERE c.category_name = %s
               ORDER BY h.publish_date DESC
               LIMIT %s OFFSET %s""",
            (category_filter, HEADLINES_PER_PAGE, offset)
        )
    else:
        cursor.execute("SELECT COUNT(*) AS total FROM news_headlines")
        total = cursor.fetchone()['total']

        cursor.execute(
            """SELECT h.*, s.source_name, c.category_name, c.category_icon
               FROM news_headlines h
               JOIN news_sources s ON h.source_id = s.source_id
               JOIN categories c ON h.category_id = c.category_id
               ORDER BY h.publish_date DESC
               LIMIT %s OFFSET %s""",
            (HEADLINES_PER_PAGE, offset)
        )

    headlines = cursor.fetchall()
    total_pages = (total + HEADLINES_PER_PAGE - 1) // HEADLINES_PER_PAGE

    cursor.close()
    conn.close()

    return render_template(
        'index.html',
        headlines=headlines,
        categories=categories,
        current_category=category_filter,
        page=page,
        total_pages=total_pages
    )


# ==================== REGISTER ====================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        conn = get_db()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                (request.form['username'], request.form['email'], request.form['password'])
            )
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))

        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash('Username or email already exists!', 'error')

        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')


# ==================== LOGIN ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        log_visit("Login Page")
    except Exception:
        pass

    if request.method == 'POST':
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("SELECT * FROM users WHERE email = %s", (request.form['email'],))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user and user['password'] == request.form['password']:
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            flash(f"Welcome back, {user['username']}!", 'success')
            return redirect(url_for('index'))

        flash('Invalid email or password!', 'error')

    return render_template('login.html')


# ==================== LOGOUT ====================
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# ==================== FAVORITES ====================
@app.route('/favorite/<int:headline_id>', methods=['POST'])
def add_favorite(headline_id):
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO favorites (user_id, headline_id) VALUES (%s, %s)",
            (session['user_id'], headline_id)
        )
        conn.commit()
        flash('Added to favorites!', 'success')

    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash('Already in favorites!', 'info')

    finally:
        cursor.close()
        conn.close()

    return redirect(request.referrer or url_for('index'))


@app.route('/favorites')
def favorites():
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("SELECT * FROM categories ORDER BY category_name")
    categories = cursor.fetchall()

    cursor.execute(
        """SELECT h.*, s.source_name, c.category_name, c.category_icon, f.saved_at
           FROM favorites f
           JOIN news_headlines h ON f.headline_id = h.headline_id
           JOIN news_sources s ON h.source_id = s.source_id
           JOIN categories c ON h.category_id = c.category_id
           WHERE f.user_id = %s
           ORDER BY f.saved_at DESC""",
        (session['user_id'],)
    )

    headlines = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('favorites.html', headlines=headlines, categories=categories)


# ==================== SCRAPER ====================
@app.route('/scrape')
def scrape():
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect(url_for('login'))

    scrape_all_sources()
    flash('News scraped successfully!', 'success')
    return redirect(url_for('index'))


# ==================== VISITOR LOGGING ====================
def log_visit(page):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO visit_logs (user_id, ip_address, visited_page) VALUES (%s, %s, %s)",
        (session.get('user_id'), request.remote_addr, page)
    )
    conn.commit()
    cursor.close()
    conn.close()


# ==================== REPORTS ====================
@app.route('/reports')
def reports():
    return render_template('reports.html')


# ==================== MAIN ====================
if __name__ == '__main__':
    app.run(debug=DEBUG)
