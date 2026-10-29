import csv, io, json, os, sqlite3, subprocess, sys, tempfile
from datetime import datetime
from functools import wraps
from pathlib import Path
from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for, make_response
from werkzeug.security import check_password_hash, generate_password_hash

BASE = Path(__file__).resolve().parent
DB_PATH = os.environ.get("DATABASE_PATH", str(BASE / "instance" / "sales.sqlite3"))
app = Flask(__name__)
app.config.update(SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"), MAX_CONTENT_LENGTH=5 * 1024 * 1024)

SCHEMA = """CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, company TEXT NOT NULL, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, created_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, sale_date TEXT NOT NULL, product TEXT NOT NULL, quantity INTEGER NOT NULL CHECK(quantity > 0), unit_price REAL NOT NULL CHECK(unit_price >= 0), created_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);"""

def get_db():
    if 'db' not in g:
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db

@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop('db', None)
    if db: db.close()

def init_db():
    db = get_db()
    for statement in SCHEMA.split(';'):
        if statement.strip(): db.execute(statement)
    db.commit()

@app.cli.command('init-db')
def init_db_command():
    init_db(); print('Database initialized.')

@app.before_request
def prepare():
    init_db()
    if 'csrf' not in session: session['csrf'] = os.urandom(24).hex()

def csrf_token(): return session.get('csrf', '')
app.jinja_env.globals['csrf_token'] = csrf_token

def require_csrf():
    if request.method in {'POST','PUT','PATCH','DELETE'} and request.form.get('csrf_token') != session.get('csrf'):
        return False
    return True

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('user_id'): return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped

def current_user():
    if not session.get('user_id'): return None
    return get_db().execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
app.jinja_env.globals['current_user'] = current_user

def parse_sale(form):
    date = form.get('sale_date','').strip(); product = form.get('product','').strip()
    if not date or not product: raise ValueError('Date and product are required.')
    datetime.strptime(date, '%Y-%m-%d')
    quantity = int(form.get('quantity','0')); price = float(form.get('unit_price','-1'))
    if quantity <= 0: raise ValueError('Quantity must be a positive whole number.')
    if price < 0: raise ValueError('Unit price cannot be negative.')
    return date, product[:120], quantity, price

def sales_for_user(user_id):
    return get_db().execute('SELECT * FROM sales WHERE user_id=? ORDER BY sale_date DESC, id DESC', (user_id,)).fetchall()

def analytics(user_id):
    rows = sales_for_user(user_id); monthly = {}; products = {}; revenue=0; units=0
    for r in rows:
        value = r['quantity'] * r['unit_price']; revenue += value; units += r['quantity']
        month = r['sale_date'][:7]; monthly.setdefault(month, {'orders':0,'revenue':0,'units':0}); monthly[month]['orders'] += 1; monthly[month]['revenue'] += value; monthly[month]['units'] += r['quantity']
        products.setdefault(r['product'], {'orders':0,'revenue':0,'units':0}); products[r['product']]['orders'] += 1; products[r['product']]['revenue'] += value; products[r['product']]['units'] += r['quantity']
    month_rows=[]; previous=None
    for month, data in sorted(monthly.items()):
        change = None if previous in (None, 0) else ((data['revenue']-previous)/previous)*100
        month_rows.append({'month':month, **data, 'change':change}); previous=data['revenue']
    product_rows = [{'product':k, **v} for k,v in products.items()]; product_rows.sort(key=lambda x:x['revenue'], reverse=True)
    return {'total_revenue':revenue, 'orders':len(rows), 'units':units, 'average_order_value': revenue/len(rows) if rows else 0, 'months':month_rows, 'products':product_rows, 'sales':[dict(r) for r in rows], 'engine': 'hadoop' if os.environ.get('HADOOP_STREAMING_JAR') else 'local-fallback'}

@app.route('/')
def index(): return redirect(url_for('dashboard')) if session.get('user_id') else redirect(url_for('login'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        if not require_csrf(): return 'Invalid CSRF token', 400
        company=request.form.get('company','').strip(); username=request.form.get('username','').strip().lower(); password=request.form.get('password',''); confirm=request.form.get('confirm','')
        if not company or not username or len(password)<6 or password != confirm: flash('Enter a company, username, and matching password of at least 6 characters.','error')
        else:
            try:
                db=get_db(); cur=db.execute('INSERT INTO users(company,username,password_hash,created_at) VALUES(?,?,?,?)',(company,username,generate_password_hash(password),datetime.utcnow().isoformat())); db.commit(); session['user_id']=cur.lastrowid; return redirect(url_for('dashboard'))
            except sqlite3.IntegrityError: flash('That username is already registered.','error')
    return render_template('auth.html', mode='register')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        if not require_csrf(): return 'Invalid CSRF token', 400
        user=get_db().execute('SELECT * FROM users WHERE username=?',(request.form.get('username','').strip().lower(),)).fetchone()
        if user and check_password_hash(user['password_hash'],request.form.get('password','')): session['user_id']=user['id']; return redirect(url_for('dashboard'))
        flash('Invalid username or password.','error')
    return render_template('auth.html', mode='login')

@app.post('/logout')
def logout():
    if not require_csrf(): return 'Invalid CSRF token', 400
    session.clear(); return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard(): return render_template('dashboard.html', data=analytics(session['user_id']))

@app.route('/sales', methods=['GET','POST'])
@login_required
def sales():
    if request.method == 'POST':
        if not require_csrf(): return 'Invalid CSRF token', 400
        try:
            date, product, quantity, price = parse_sale(request.form); db=get_db(); db.execute('INSERT INTO sales(user_id,sale_date,product,quantity,unit_price,created_at) VALUES(?,?,?,?,?,?)',(session['user_id'],date,product,quantity,price,datetime.utcnow().isoformat())); db.commit(); flash('Sale added.','success')
        except (ValueError, TypeError): flash('Please enter a valid date, product, positive quantity, and non-negative price.','error')
    return render_template('sales.html', sales=sales_for_user(session['user_id']))

@app.post('/sales/import')
@login_required
def import_csv():
    if not require_csrf(): return 'Invalid CSRF token', 400
    upload=request.files.get('file')
    if not upload or not upload.filename.lower().endswith('.csv'): flash('Choose a CSV file.','error'); return redirect(url_for('sales'))
    try:
        text=io.TextIOWrapper(upload.stream, encoding='utf-8-sig'); reader=csv.DictReader(text); required={'date','product','quantity','unit_price'}
        if not required.issubset(set(reader.fieldnames or [])): raise ValueError('CSV columns must be date, product, quantity, unit_price.')
        db=get_db(); count=0
        for row in reader:
            date, product, quantity, price = parse_sale({'sale_date':row['date'],'product':row['product'],'quantity':row['quantity'],'unit_price':row['unit_price']}); db.execute('INSERT INTO sales(user_id,sale_date,product,quantity,unit_price,created_at) VALUES(?,?,?,?,?,?)',(session['user_id'],date,product,quantity,price,datetime.utcnow().isoformat())); count+=1
        db.commit(); flash(f'Imported {count} sales.','success')
    except Exception as exc: flash(str(exc),'error')
    return redirect(url_for('sales'))

@app.get('/api/analytics')
@login_required
def api_analytics(): return jsonify(analytics(session['user_id']))

@app.get('/api/status')
def status(): return jsonify({'status':'ok','engine':'hadoop' if os.environ.get('HADOOP_STREAMING_JAR') else 'local-fallback'})

@app.get('/download')
@login_required
def download():
    output=io.StringIO(); writer=csv.writer(output); writer.writerow(['date','product','quantity','unit_price','revenue'])
    for r in sales_for_user(session['user_id']): writer.writerow([r['sale_date'],r['product'],r['quantity'],r['unit_price'],r['quantity']*r['unit_price']])
    response=make_response(output.getvalue()); response.headers['Content-Disposition']='attachment; filename=sales_export.csv'; response.headers['Content-Type']='text/csv'; return response

if __name__ == '__main__': app.run(debug=True)
