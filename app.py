from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature

app = Flask(__name__, template_folder="templates")
app.secret_key = "your_secret_key"

# Database Config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Fareeth@123'
app.config['MYSQL_DB'] = 'bookstore'

mysql = MySQL(app)

# ---------------- Mail Config ----------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # example using Gmail
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'mohamedfareeth0811@gmail.com'       # <-- your email
app.config['MAIL_PASSWORD'] = 'Fareeth@123'        # <-- app password or actual password
mail = Mail(app)

# Serializer for token generation
s = URLSafeTimedSerializer(app.secret_key)


# ------------------ HOME ------------------
@app.route('/')
def index():
    return render_template('index.html')


# ------------------ REGISTER ------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        if user:
            flash("Email already registered!", "danger")
        else:
            # Insert with is_verified = 0
            cursor.execute("INSERT INTO users (name, email, password, is_admin, is_verified) VALUES (%s, %s, %s, %s, %s)",
                           (name, email, password, 0, 0))
            mysql.connection.commit()

            # Generate token
            token = s.dumps(email, salt='email-confirm')

            # Send verification email
            link = url_for('verify_email', token=token, _external=True)
            msg = Message('Verify Your Email', sender='your_email@gmail.com', recipients=[email])
            msg.body = f'Hi {name}, click the link to verify your email: {link}'
            mail.send(msg)

            flash("Registration successful! Check your email to verify your account.", "success")
            return redirect(url_for('login'))

    return render_template('register.html')



# ------------------ LOGIN ------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Auto-redirect if already logged in
    if 'loggedin' in session:
        if session.get('is_admin'):
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('user_dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['loggedin'] = True
            session['id'] = user['id']
            session['email'] = user['email']
            session['is_admin'] = user['is_admin']

            if user['is_admin']:
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash("Invalid email or password!", "danger")

    return render_template('login.html')


# ------------------ LOGOUT ------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ------------------ ADMIN DASHBOARD ------------------
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'loggedin' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Add Book
    if request.method == 'POST' and request.form.get('action') == 'add':
        title = request.form['title']
        author = request.form['author']
        price = request.form['price']
        stock = request.form['stock']
        cursor.execute("INSERT INTO books (title, author, price, stock) VALUES (%s, %s, %s, %s)",
                       (title, author, price, stock))
        mysql.connection.commit()
        flash("Book added successfully!", "success")
        return redirect(url_for('admin'))

    # Fetch stats
    cursor.execute("SELECT COUNT(*) AS total_users FROM users")
    total_users = cursor.fetchone()['total_users']

    cursor.execute("SELECT COUNT(*) AS total_books FROM books")
    total_books = cursor.fetchone()['total_books']

    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()

    return render_template("admin.html", total_users=total_users, total_books=total_books, books=books)


# ------------------ EDIT BOOK ------------------
@app.route('/edit_book/<int:id>', methods=['GET', 'POST'])
def edit_book(id):
    if 'loggedin' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        price = request.form['price']
        stock = request.form['stock']

        cursor.execute("UPDATE books SET title=%s, author=%s, price=%s, stock=%s WHERE id=%s",
                       (title, author, price, stock, id))
        mysql.connection.commit()
        flash("Book updated successfully!", "success")
        return redirect(url_for('admin'))

    cursor.execute("SELECT * FROM books WHERE id=%s", (id,))
    book = cursor.fetchone()
    return render_template("edit_book.html", book=book)


# ------------------ DELETE BOOK ------------------
@app.route('/delete_book/<int:id>')
def delete_book(id):
    if 'loggedin' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM books WHERE id=%s", (id,))
    mysql.connection.commit()
    flash("Book deleted successfully!", "success")
    return redirect(url_for('admin'))


# ------------------ USER DASHBOARD ------------------
@app.route('/user_dashboard')
def user_dashboard():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()

    return render_template("user_dashboard.html", books=books)


# ------------------ MAIN ------------------
if __name__ == "__main__":
    app.run(debug=True)

