from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3, os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__, template_folder='.', static_folder='.')
app.secret_key = "smartcampus123"
app.config['UPLOAD_FOLDER'] = "static/uploads"
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_db():
    conn = sqlite3.connect("smartcampus.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users 
        (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS issues 
        (id INTEGER PRIMARY KEY, title TEXT, description TEXT, category TEXT, location TEXT, 
        priority TEXT, confidence TEXT, status TEXT, report_count INTEGER, photo TEXT,
        user_id INTEGER, name TEXT, created_at TEXT)""")
        # Create default admin
        try:
            c.execute("INSERT INTO users (name,email,password) VALUES (?,?,?)",
                      ("Admin","admin@campus.com","admin123"))
            c.commit()
        except: pass

init_db()

@app.route('/')
def home(): return redirect('/login')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        name=request.form['name'].strip()
        email=request.form['email'].strip().lower()
        pwd=request.form['password'].strip()
        try:
            with get_db() as c:
                c.execute("INSERT INTO users (name,email,password) VALUES (?,?,?)",(name,email,pwd))
                c.commit()
            return redirect('/login')
        except:
            return "Email already exists! <a href='/register'>Try again</a>"
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        email=request.form['email'].strip().lower()
        pwd=request.form['password'].strip()
        with get_db() as c:
            user=c.execute("SELECT * FROM users WHERE email=? AND password=?",(email,pwd)).fetchone()
            if user:
                session['user_id']=user['id']
                session['name']=user['name']
                session['email']=user['email']
                return redirect('/dashboard')
        return "Wrong email/password! <a href='/login'>Try again</a>"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect('/login')
    with get_db() as c:
        issues=c.execute("SELECT * FROM issues WHERE user_id=? ORDER BY id DESC",(session['user_id'],)).fetchall()
    return render_template("dashboard.html", issues=issues, name=session['name'])

@app.route('/report', methods=['GET','POST'])
def report():
    if 'user_id' not in session: return redirect("/login")
    if request.method=="POST":
        title=request.form['title'].strip()
        loc=request.form['location'].strip()
        desc=request.form['desc']
        cat="Plumbing" if "water" in title.lower() or "leak" in title.lower() else "Electrical" if "light" in title.lower() or "fan" in title.lower() else "Cleanliness" if "clean" in title.lower() or "dust" in title.lower() else "Infrastructure"
        prio="High" if "leak" in title.lower() or "water" in title.lower() or "broken" in title.lower() else "Medium"
        conf="92%"
        f=request.files.get('photo'); pname=""
        if f and f.filename:
            pname=secure_filename(f.filename)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'],pname))
        with get_db() as c:
            # One Task Many Reports logic
            ex=c.execute("SELECT id, report_count FROM issues WHERE LOWER(title)=? AND status!='Resolved'",(title.lower(),)).fetchone()
            if ex:
                c.execute("UPDATE issues SET report_count=report_count+1 WHERE id=?",(ex['id'],))
                c.commit()
                return redirect('/dashboard')
            c.execute("INSERT INTO issues (title, description, category, location, priority, confidence, status, report_count, photo, user_id, name, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                      (title, desc, cat, loc, prio, conf, 'Active', 1, pname, session['user_id'], session['name'], datetime.now().strftime("%Y-%m-%d %H:%M")))
            c.commit()
        return redirect('/dashboard')
    return render_template("report.html")

@app.route('/admin')
def admin():
    if 'user_id' not in session: return redirect('/login')
    with get_db() as c:
        issues=c.execute("SELECT * FROM issues ORDER BY id DESC").fetchall()
    return render_template("admin.html", issues=issues)

@app.route('/update_status/<int:id>', methods=['POST'])
def update_status(id):
    if 'user_id' not in session: return redirect('/login')
    s=request.form.get('status')
    with get_db() as c:
        c.execute("UPDATE issues SET status=? WHERE id=?",(s,id))
        c.commit()
    return redirect('/admin')

@app.route('/update_status/<int:issue_id>', methods=['POST'])
def update_status2(issue_id):
    if 'user_id' not in session: return redirect('/login')
    s=request.form.get('status')
    with get_db() as c:
        c.execute("UPDATE issues SET status=? WHERE id=?",(s,issue_id))
        c.commit()
    return redirect('/admin')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__=='__main__':
    print("*** FINAL SMARTCAMPUS RUNNING ***")
    app.run(debug=True)
