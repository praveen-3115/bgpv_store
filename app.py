from flask import Flask,render_template,request,redirect,session,flash
from flask_mail import Mail,Message
import os
import re
import sqlite3
from werkzeug.utils import secure_filename
import config
import bcrypt
import random
import razorpay
from flask import request, jsonify, render_template
import traceback
from flask import make_response, render_template
from utils.pdf_generator import generate_pdf
from dotenv import load_dotenv
import requests
import urllib.parse
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

print("RUNNING THIS APP:", __file__)
app=Flask(__name__)
app.secret_key=config.secret_key

app.config['MAIL_SERVER'] = config.MAIL_SERVER
app.config['MAIL_PORT'] = config.MAIL_PORT
app.config['MAIL_USE_TLS'] = config.MAIL_USE_TLS
app.config['MAIL_USERNAME'] = config.MAIL_USERNAME
app.config['MAIL_PASSWORD'] = config.MAIL_PASSWORD
mail=Mail(app)

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'product_images')
ADMIN_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'product_images', 'admin_profiles')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ADMIN_UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ADMIN_UPLOAD_FOLDER'] = ADMIN_UPLOAD_FOLDER

# SQLite Cursor & Connection Wrappers for MySQL compatibility
class SQLiteCursorWrapper:
    def __init__(self, cursor):
        self._cursor = cursor

    def _convert_query(self, query):
        if not isinstance(query, str):
            return query
        # Seamlessly convert MySQL %s placeholders to SQLite ? placeholders
        return re.sub(r'%s', '?', query)

    def execute(self, query, params=None):
        converted = self._convert_query(query)
        if params is None:
            return self._cursor.execute(converted)
        if not isinstance(params, (tuple, list)):
            params = (params,)
        return self._cursor.execute(converted, params)

    def executemany(self, query, params_seq):
        converted = self._convert_query(query)
        return self._cursor.executemany(converted, params_seq)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def close(self):
        try:
            return self._cursor.close()
        except Exception:
            pass

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def __iter__(self):
        return iter(self._cursor)

class SQLiteConnectionWrapper:
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self, dictionary=False):
        # sqlite3.Row enables dict-like row access (e.g. row['col'] and row.col)
        return SQLiteCursorWrapper(self._conn.cursor())

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        try:
            return self._conn.close()
        except Exception:
            pass

# SQLite database connection
def get_db():
    if not os.path.exists(config.DB_PATH):
        from init_db import init_database
        init_database(config.DB_PATH)

    conn = sqlite3.connect(config.DB_PATH, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return SQLiteConnectionWrapper(conn)
#Route-1 home page
@app.route('/')
def home():

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM products ORDER BY product_id DESC")
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("index.html", products=products)
#route-2 admin register
@app.route('/admin_register',methods=['GET','POST'])
def admin_register():
    if request.method=="GET":
        return render_template("admin/admin_signup.html")
    name = request.form['name']
    email=request.form['email']
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT admin_id FROM admin WHERE email=%s", (email,))
    existing_admin = cursor.fetchone()
    cursor.close()
    conn.close()

    # 2️⃣ Save user input temporarily in session
    if existing_admin:
        flash("This email is already registered. Please login instead.", "danger")
        return redirect('/admin_register')

    # Save user input temporarily in session
    session['signup_name'] = name
    session['signup_email'] = email

    # Generate OTP
    otp = random.randint(100000, 999999)
    session['otp'] = otp

    # Send OTP
    message = Message(
        subject="Sassy Store Admin OTP",
        sender=config.MAIL_USERNAME,
        recipients=[email]
    )

    message.body = f"Your OTP for Sassy Store Admin Registration is: {otp}"

    mail.send(message)

    flash("OTP sent to your email!", "success")

    return redirect('/verify-otp')


# ---------------------------------------------------------
# ROUTE 2: DISPLAY OTP PAGE
# ---------------------------------------------------------
@app.route('/verify-otp', methods=['GET'])
def verify_otp_get():
    return render_template("admin/verify_otp.html")



# ---------------------------------------------------------
# ROUTE 3: VERIFY OTP + SAVE ADMIN
# ---------------------------------------------------------
@app.route('/verify-otp', methods=['POST'])
def verify_otp_post():
    
    # User submitted OTP + Password
    user_otp = request.form['otp']
    password = request.form['password']

    # Compare OTP
    if str(session.get('otp')) != str(user_otp):
        flash("Invalid OTP. Try again!", "danger")
        return redirect('/verify-otp')

    # Hash password using bcrypt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Insert admin into database
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO admin (name, email, password) VALUES (%s, %s, %s)",
        (session['signup_name'], session['signup_email'], hashed_password)
    )
    conn.commit()
    cursor.close()
    conn.close()

    # Clear temporary session data
    session.pop('otp', None)
    session.pop('signup_name', None)
    session.pop('signup_email', None)

    flash("Admin Registered Successfully!", "success")
    return redirect('/admin_register')
#route-4-admin-login
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():

    # Show login page
    if request.method == 'GET':
        return render_template("admin/admin_login.html")

    # POST → Validate login
    email = request.form['email']
    password = request.form['password']

    # Step 1: Check if admin email exists
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM admin WHERE email=%s", (email,))
    admin = cursor.fetchone()

    cursor.close()
    conn.close()

    if admin is None:
        flash("Email not found! Please register first.", "danger")
        return redirect('/admin-login')

    # Step 2: Compare entered password with hashed password (handle both str and bytes in SQLite)
    stored_hashed_password = admin['password']
    if isinstance(stored_hashed_password, str):
        stored_hashed_password = stored_hashed_password.encode('utf-8')

    if not bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password):
        flash("Incorrect password! Try again.", "danger")
        return redirect('/admin-login')

    # Step 5: If login success → Create admin session
    session['admin_id'] = admin['admin_id']
    session['admin_name'] = admin['name']
    session['admin_email'] = admin['email']

    flash("Login Successful!", "success")
    return redirect('/admin-dashboard')
#route-5 admin dashoard
@app.route('/admin-dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        flash("Please login to access dashboard","danger")
        return redirect('/admin-login')
    return render_template("admin/admin_dashboard.html",admin_name=session['admin_name'])
#route 6 admin-logout
@app.route('/admin-logout')
def admin_logout():
     session.pop('admin_id', None)
     session.pop('admin_name', None)
     session.pop('admin_email', None)

     flash("Logged out successfully.", "success")
     return redirect('/admin-login')

#route 7 add-item
@app.route('/admin/add-item', methods=['GET'])
def add_item_page():

    # Only logged-in admin can access
    if 'admin_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/admin-login')

    return render_template("admin/add_item.html")
@app.route('/admin/add-item', methods=['POST'])
def add_item():

    # Check admin session
    if 'admin_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/admin-login')

    # 1️⃣ Get form data
    name = request.form['name']
    description = request.form['description']
    category = request.form['category']
    price = request.form['price']
    image_file = request.files['image']

    # 2️⃣ Validate image upload
    if image_file.filename == "":
        flash("Please upload a product image!", "danger")
        return redirect('/admin/add-item')

    # 3️⃣ Secure the file name
    filename = secure_filename(image_file.filename)

    # 4️⃣ Create full path
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # 5️⃣ Save image into folder
    image_file.save(image_path)

    # 6️⃣ Insert product into database
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO products (name, description, category, price, image) VALUES (%s, %s, %s, %s, %s)",
        (name, description, category, price, filename)
    )

    conn.commit()
    cursor.close()
    conn.close()

    flash("Product added successfully!", "success")
    return redirect('/admin/add-item')

@app.route('/admin/item-list')
def item_list():

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    search = request.args.get('search', '')
    category_filter = request.args.get('category', '')

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # 1️⃣ Fetch category list for dropdown
    cursor.execute("SELECT DISTINCT category FROM products")
    categories = cursor.fetchall()

    # 2️⃣ Build dynamic query based on filters
    query = "SELECT * FROM products WHERE 1=1"
    params = []

    if search:
        query += " AND name LIKE %s"
        params.append("%" + search + "%")

    if category_filter:
        query += " AND category = %s"
        params.append(category_filter)

    cursor.execute(query, params)
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin/item_list.html",
        products=products,
        categories=categories
    )

@app.route('/admin/view-item/<int:item_id>')
def view_item_page(item_id):

    # Check admin session
    if 'admin_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/admin-login')

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM products WHERE product_id = %s", (item_id,))
    product = cursor.fetchone()

    cursor.close()
    conn.close()

    if not product:
        flash("Product not found!", "danger")
        return redirect('/admin/item-list')

    return render_template("admin/view_item.html", product=product)

#route-11 update-item
@app.route('/admin/update-item/<int:item_id>', methods=['GET'])
def update_item_page(item_id):

    # Check login
    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    # Fetch product data
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM products WHERE product_id = %s", (item_id,))
    product = cursor.fetchone()

    cursor.close()
    conn.close()

    if not product:
        flash("Product not found!", "danger")
        return redirect('/admin/item-list')

    return render_template("admin/update_item.html", product=product)


#route-12 update-item-logic
@app.route('/admin/update-item/<int:item_id>', methods=['POST'])
def update_item(item_id):

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    # 1️⃣ Get updated form data
    name = request.form['name']
    description = request.form['description']
    category = request.form['category']
    price = request.form['price']

    new_image = request.files['image']

    # 2️⃣ Fetch old product data
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE product_id = %s", (item_id,))
    product = cursor.fetchone()

    if not product:
        flash("Product not found!", "danger")
        return redirect('/admin/item-list')

    old_image_name = product['image']

    # 3️⃣ If admin uploaded a new image → replace it
    if new_image and new_image.filename != "":
        
        # Secure filename
        from werkzeug.utils import secure_filename
        new_filename = secure_filename(new_image.filename)

        # Save new image
        new_image_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        new_image.save(new_image_path)

        # Delete old image file
        old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], old_image_name)
        if os.path.exists(old_image_path):
            os.remove(old_image_path)

        final_image_name = new_filename

    else:
        # No new image uploaded → keep old one
        final_image_name = old_image_name

    # 4️⃣ Update product in the database
    cursor.execute("""
        UPDATE products
        SET name=%s, description=%s, category=%s, price=%s, image=%s
        WHERE product_id=%s
    """, (name, description, category, price, final_image_name, item_id))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Product updated successfully!", "success")
    return redirect('/admin/item-list')

#route 13 - delete item
@app.route('/admin/delete-item/<int:item_id>')
def delete_item(item_id):

    if 'admin_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/admin-login')

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # 1️⃣ Fetch product to get image name
    cursor.execute("SELECT image FROM products WHERE product_id=%s", (item_id,))
    product = cursor.fetchone()

    if not product:
        flash("Product not found!", "danger")
        return redirect('/admin/item-list')

    image_name = product['image']

    # Delete image from folder
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name)
    if os.path.exists(image_path):
        os.remove(image_path)

    # 2️⃣ Delete product from DB
    cursor.execute("DELETE FROM products WHERE product_id=%s", (item_id,))
    conn.commit()

    cursor.close()
    conn.close()

    flash("Product deleted successfully!", "success")
    return redirect('/admin/item-list')


@app.route('/admin/profile', methods=['GET'])
def admin_profile():

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    admin_id = session['admin_id']

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM admin WHERE admin_id = %s", (admin_id,))
    admin = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("admin/admin_profile.html", admin=admin)

@app.route('/admin/profile', methods=['POST'])
def admin_profile_update():

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    admin_id = session['admin_id']

    # 1️⃣ Get form data
    name = request.form['name']
    email = request.form['email']
    new_password = request.form['password']
    new_image = request.files['profile_image']

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # 2️⃣ Fetch old admin data
    cursor.execute("SELECT * FROM admin WHERE admin_id = %s", (admin_id,))
    admin = cursor.fetchone()

    old_image_name = admin['profile_image']

    # 3️⃣ Update password only if entered
    if new_password:
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    else:
        hashed_password = admin['password']  # keep old password

    # 4️⃣ Process new profile image if uploaded
    if new_image and new_image.filename != "":
        
        from werkzeug.utils import secure_filename
        new_filename = secure_filename(new_image.filename)

        # Save new image
        image_path = os.path.join(app.config['ADMIN_UPLOAD_FOLDER'], new_filename)
        new_image.save(image_path)

        # Delete old image
        if old_image_name:
            old_image_path = os.path.join(app.config['ADMIN_UPLOAD_FOLDER'], old_image_name)
            if os.path.exists(old_image_path):
                os.remove(old_image_path)

        final_image_name = new_filename
    else:
        final_image_name = old_image_name

    # 5️⃣ Update database
    cursor.execute("""
        UPDATE admin
        SET name=%s, email=%s, password=%s, profile_image=%s
        WHERE admin_id=%s
    """, (name, email, hashed_password, final_image_name, admin_id))

    conn.commit()
    cursor.close()
    conn.close()

    # Update session name for UI consistency
    session['admin_name'] = name  
    session['admin_email'] = email

    flash("Profile updated successfully!", "success")
    return redirect('/admin/profile')

'''
------------------------
------------------------
USER MODULE
------------------------
------------------------
'''
#---------USER REGISTER-------------
@app.route('/user_register',methods=['GET','POST'])
def user_register():
    if request.method=="GET":
        return render_template("user/user_signup.html")
    name = request.form['name']
    email=request.form['email']
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id FROM users WHERE email=%s", (email,))
    existing_user = cursor.fetchone()
    cursor.close()
    conn.close()

    # 2️⃣ Save user input temporarily in session
    if existing_user:
        flash("This email is already registered. Please login instead.", "danger")
        return redirect('/user_register')

    # Save user input temporarily in session
    session['signup_name'] = name
    session['signup_email'] = email

    # Generate OTP
    otp = random.randint(100000, 999999)
    session['otp'] = otp

    # Send OTP
    message = Message(
        subject="Sassy Store User OTP",
        sender=config.MAIL_USERNAME,
        recipients=[email]
    )

    message.body = f"Your OTP for Sassy Store User Registration is: {otp}"

    mail.send(message)

    flash("OTP sent to your email!", "success")

    return redirect('/verify-user-otp')

#-----OTP sending and verification
@app.route('/verify-user-otp', methods=['GET'])
def verify_user_otp_get():
    return render_template("user/verify_otp.html")



# ---------------------------------------------------------
# ROUTE 3: VERIFY OTP + SAVE ADMIN
# ---------------------------------------------------------
@app.route('/verify-user-otp', methods=['POST'])
def verify_user_otp_post():
    
    # User submitted OTP + Password
    user_otp = request.form['otp']
    password = request.form['password']

    # Compare OTP
    if str(session.get('otp')) != str(user_otp):
        flash("Invalid OTP. Try again!", "danger")
        return redirect('/verify-user-otp')

    # Hash password using bcrypt and decode to utf-8 string for clean SQLite storage
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Insert user into database
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
        (session['signup_name'], session['signup_email'], hashed_password)
    )
    conn.commit()
    cursor.close()
    conn.close()

    # Clear temporary session data
    session.pop('otp', None)
    session.pop('signup_name', None)
    session.pop('signup_email', None)

    flash("User Registered Successfully! Please login.", "success")
    return redirect('/user-login')
#route-4-admin-login
@app.route('/user-login', methods=['GET', 'POST'])
def user_login():

    # Show login page
    if request.method == 'GET':
        return render_template("user/user_login.html")

    # POST → Validate login
    email = request.form['email']
    password = request.form['password']

    # Step 1: Check if admin email exists
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user is None:
        flash("Email not found! Please register first.", "danger")
        return redirect('/user-login')

    # Step 2: Compare entered password with hashed password (handle both str and bytes in SQLite)
    stored_hashed_password = user['password']
    if isinstance(stored_hashed_password, str):
        stored_hashed_password = stored_hashed_password.encode('utf-8')

    if not bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password):
        flash("Incorrect password! Try again.", "danger")
        return redirect('/user-login')

    # Step 5: If login success → Create admin session
    session['user_id'] = user['user_id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']

    flash("Login Successful!", "success")
    return redirect('/user-dashboard')
# route-6 user logout
@app.route('/user-logout')
def user_logout():
    
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_email', None)

    flash("Logged out successfully!", "success")
    return redirect('/user-login')

# ---------------------------------------------------------
# USER FORGOT PASSWORD & RESET
# ---------------------------------------------------------
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template("user/forgot_password.html")

    email = request.form.get('email', '').strip()

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id, name FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        flash("No account registered with that email address.", "danger")
        return redirect('/forgot-password')

    otp = random.randint(100000, 999999)
    session['reset_email'] = email
    session['reset_otp'] = str(otp)

    try:
        message = Message(
            subject="Password Reset OTP - Sassy Store",
            sender=config.MAIL_USERNAME,
            recipients=[email]
        )
        message.body = (
            f"Hello {user['name']},\n\n"
            f"Your OTP for resetting your Sassy Store account password is: {otp}\n\n"
            f"If you did not request this password reset, please ignore this email.\n\n"
            f"Best regards,\nSassy Store Support Team"
        )
        mail.send(message)
        flash("Password reset OTP has been sent to your email!", "success")
        return redirect('/reset-password')
    except Exception as e:
        app.logger.error("Failed to send reset email: %s\n%s", str(e), traceback.format_exc())
        flash("Failed to send OTP email. Please verify mail configuration or try again.", "danger")
        return redirect('/forgot-password')


@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_email' not in session or 'reset_otp' not in session:
        flash("Please request a password reset first.", "warning")
        return redirect('/forgot-password')

    if request.method == 'GET':
        return render_template("user/reset_password.html", email=session.get('reset_email'))

    entered_otp = request.form.get('otp', '').strip()
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if str(session.get('reset_otp')) != str(entered_otp):
        flash("Invalid OTP. Please check your email and try again.", "danger")
        return redirect('/reset-password')

    if new_password != confirm_password:
        flash("Passwords do not match. Please re-enter.", "danger")
        return redirect('/reset-password')

    if len(new_password) < 6:
        flash("Password must be at least 6 characters long.", "danger")
        return redirect('/reset-password')

    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    email = session.get('reset_email')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password=%s WHERE email=%s", (hashed_password, email))
    conn.commit()
    cursor.close()
    conn.close()

    session.pop('reset_email', None)
    session.pop('reset_otp', None)

    flash("Password reset successfully! Please sign in with your new password.", "success")
    return redirect('/user-login')

# ---------------------------------------------------------
# ADMIN FORGOT PASSWORD & RESET
# ---------------------------------------------------------
@app.route('/admin/forgot-password', methods=['GET', 'POST'])
def admin_forgot_password():
    if request.method == 'GET':
        return render_template("admin/admin_forgot_password.html")

    email = request.form.get('email', '').strip()

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT admin_id, name FROM admin WHERE email=%s", (email,))
    admin = cursor.fetchone()
    cursor.close()
    conn.close()

    if not admin:
        flash("No admin account registered with that email address.", "danger")
        return redirect('/admin/forgot-password')

    otp = random.randint(100000, 999999)
    session['admin_reset_email'] = email
    session['admin_reset_otp'] = str(otp)

    try:
        message = Message(
            subject="Admin Password Reset OTP - Sassy Store",
            sender=config.MAIL_USERNAME,
            recipients=[email]
        )
        message.body = (
            f"Hello {admin['name']},\n\n"
            f"Your OTP for resetting your Sassy Store Admin password is: {otp}\n\n"
            f"If you did not request this, please secure your account immediately.\n\n"
            f"Best regards,\nSassy Store Security Team"
        )
        mail.send(message)
        flash("Admin password reset OTP sent to your email!", "success")
        return redirect('/admin/reset-password')
    except Exception as e:
        app.logger.error("Failed to send admin reset email: %s\n%s", str(e), traceback.format_exc())
        flash("Failed to send OTP email. Please verify mail configuration or try again.", "danger")
        return redirect('/admin/forgot-password')


@app.route('/admin/reset-password', methods=['GET', 'POST'])
def admin_reset_password():
    if 'admin_reset_email' not in session or 'admin_reset_otp' not in session:
        flash("Please request an admin password reset first.", "warning")
        return redirect('/admin/forgot-password')

    if request.method == 'GET':
        return render_template("admin/admin_reset_password.html", email=session.get('admin_reset_email'))

    entered_otp = request.form.get('otp', '').strip()
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if str(session.get('admin_reset_otp')) != str(entered_otp):
        flash("Invalid OTP. Try again.", "danger")
        return redirect('/admin/reset-password')

    if new_password != confirm_password:
        flash("Passwords do not match.", "danger")
        return redirect('/admin/reset-password')

    if len(new_password) < 6:
        flash("Password must be at least 6 characters long.", "danger")
        return redirect('/admin/reset-password')

    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    email = session.get('admin_reset_email')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE admin SET password=%s WHERE email=%s", (hashed_password, email))
    conn.commit()
    cursor.close()
    conn.close()

    session.pop('admin_reset_email', None)
    session.pop('admin_reset_otp', None)

    flash("Admin password reset successfully! Please log in.", "success")
    return redirect('/admin-login')

#route-5 admin dashoard
@app.route('/user-dashboard')
def user_dashboard():
    if 'user_id' not in session:
        flash("Please login to access dashboard","danger")
        return redirect('/admin-login')
    return render_template("user/user_dashboard.html",user_name=session['user_name'])

@app.route('/products')
def products():
    if 'user_id' not in session:
        flash("Please Login to start shopping")
        return redirect('/user-login')
        

    search = request.args.get('search', '')
    category_filter = request.args.get('category', '')


    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Fetch categories for filter dropdown
    cursor.execute("SELECT DISTINCT category FROM products")
    categories = cursor.fetchall()

    # Build dynamic SQL
    query = "SELECT * FROM products WHERE 1=1"
    params = []

    if search:
        query += " AND name LIKE %s"
        params.append("%" + search + "%")

    if category_filter:
        query += " AND category = %s"
        params.append(category_filter)

    cursor.execute(query, params)
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "user/products.html",
        products=products,
        categories=categories
    )

# view single product
@app.route('/user/product/<int:product_id>')
def user_product_details(product_id):

    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/user-login')

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
    product = cursor.fetchone()

    cursor.close()
    conn.close()

    if not product:
        flash("Product not found!", "danger")
        return redirect('/products')

    return render_template("user/product_details.html",product=product)
# add to cart
# add to cart
@app.route("/add-to-cart/<int:product_id>")
def add_to_cart(product_id):

    if "user_id" not in session:
        return redirect("/user-login")

    user_id = session["user_id"]

    con = get_db()
    cur = con.cursor()

    # Check if product already exists in cart
    cur.execute(
        "SELECT quantity FROM cart WHERE user_id = %s AND product_id = %s",
        (user_id, product_id)
    )

    item = cur.fetchone()

    if item:
        # Increase quantity
        cur.execute(
            "UPDATE cart SET quantity = quantity + 1 "
            "WHERE user_id = %s AND product_id = %s",
            (user_id, product_id)
        )
    else:
        # Add new product
        cur.execute(
            "INSERT INTO cart (user_id, product_id, quantity) "
            "VALUES (%s, %s, %s)",
            (user_id, product_id, 1)
        )

    con.commit()
    cur.close()
    con.close()

    # Open cart page
    return redirect("/cart")


# cart page
# cart page
@app.route("/cart")
def cart():

    if "user_id" not in session:
        return redirect("/user-login")

    user_id = session["user_id"]

    con = get_db()
    cur = con.cursor(dictionary=True)

    cur.execute("""
        SELECT 
            cart.product_id,
            cart.quantity,
            products.name,
            products.price,
            products.image
        FROM cart
        JOIN products
        ON cart.product_id = products.product_id
        WHERE cart.user_id = %s
    """, (user_id,))

    cart_items = cur.fetchall()

    # Calculate total
    total = 0

    for item in cart_items:
        total += item["price"] * item["quantity"]

    cur.close()
    con.close()

    return render_template(
        "user/add_to_cart.html",
        cart_items=cart_items,
        total=total
    )
# remove from cart
@app.route("/remove-from-cart/<int:product_id>")
def remove_from_cart(product_id):

    if "user_id" not in session:
        return redirect("/user-login")

    user_id = session["user_id"]

    con = get_db()
    cur = con.cursor()

    cur.execute(
        "DELETE FROM cart WHERE user_id = %s AND product_id = %s",
        (user_id, product_id)
    )

    con.commit()

    cur.close()
    con.close()


    return redirect("/cart")
# increase quantity
@app.route("/increase-quantity/<int:product_id>")
def increase_quantity(product_id):

    if "user_id" not in session:
        return redirect("/user-login")

    user_id = session["user_id"]

    con = get_db()
    cur = con.cursor()

    cur.execute(
        """
        UPDATE cart
        SET quantity = quantity + 1
        WHERE user_id = %s AND product_id = %s
        """,
        (user_id, product_id)
    )

    con.commit()

    cur.close()
    con.close()

    return redirect("/cart")


# decrease quantity
@app.route("/decrease-quantity/<int:product_id>")
def decrease_quantity(product_id):

    if "user_id" not in session:
        return redirect("/user-login")

    user_id = session["user_id"]

    con = get_db()
    cur = con.cursor()

    cur.execute(
        """
        UPDATE cart
        SET quantity = quantity - 1
        WHERE user_id = %s
        AND product_id = %s
        AND quantity > 1
        """,
        (user_id, product_id)
    )

    con.commit()

    cur.close()
    con.close()

    return redirect("/cart")
@app.route('/calculate_total',methods=['POST'])
def calculate_total():
    if 'user_id' not  in session:
        flash("Please Login First")
        return redirect('/user-login')
    user_id=session['user_id']
    selected_products=request.form.getlist("selected_products")
    print("selected_products",selected_products)
    total=0
    con=get_db()
    cursor=con.cursor(dictionary=True)
    for product_id in selected_products:

        cursor.execute("""
            SELECT cart.quantity, products.price
            FROM cart
            JOIN products
            ON cart.product_id = products.product_id
            WHERE cart.user_id = %s
            AND cart.product_id = %s
        """, (user_id, product_id))
        item=cursor.fetchone()
        if item:
            total+=item["price"] * item["quantity"]
    cursor.execute("""

        SELECT
            cart.product_id,
            cart.quantity,
            products.name,
            products.price,
            products.image
        FROM cart
        JOIN products
        ON cart.product_id = products.product_id
        WHERE cart.user_id = %s
    """, (user_id,))
    cart_items=cursor.fetchall()
    cursor.close()
    con.close()
    return render_template(
    "user/add_to_cart.html",
    cart_items=cart_items,
    total=total,
    selected_products=selected_products
)


# razorpay module 

razorpay_client = razorpay.Client(
    auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET)
)

@app.route('/checkout-address', methods=['POST'])
def checkout_address():

    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/user-login')

    selected_products = request.form.getlist("selected_products")

    if not selected_products:
        flash("Please select at least one product!", "danger")
        return redirect('/cart')

    return render_template(
        "user/address.html",
        selected_products=selected_products
    )

def send_whatsapp_order_notification(phone_number, order_id, amount, customer_name, items_summary, address):
    """
    Sends an automated order confirmation message to the customer's mobile number via WhatsApp.
    Uses Twilio WhatsApp API (whitelisted on PythonAnywhere free tier).
    Fails safely if credentials are not configured or connection fails.
    """
    if not phone_number:
        app.logger.warning("No phone number provided for WhatsApp order notification #%s", order_id)
        return False

    clean_digits = re.sub(r'[^0-9]', '', str(phone_number))
    if len(clean_digits) == 10:
        clean_phone = "+91" + clean_digits
    elif clean_digits.startswith("0") and len(clean_digits) == 11:
        clean_phone = "+91" + clean_digits[1:]
    elif clean_digits.startswith("91") and len(clean_digits) == 12:
        clean_phone = "+" + clean_digits
    elif not clean_digits.startswith("+"):
        clean_phone = "+" + clean_digits
    else:
        clean_phone = str(phone_number).strip()

    # UltraMsg settings (e.g. instance12345)
    ultramsg_instance = getattr(config, 'ULTRAMSG_INSTANCE_ID', None) or os.getenv('ULTRAMSG_INSTANCE_ID')
    ultramsg_token = getattr(config, 'ULTRAMSG_TOKEN', None) or os.getenv('ULTRAMSG_TOKEN')

    # Twilio settings
    account_sid = getattr(config, 'TWILIO_ACCOUNT_SID', None) or os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = getattr(config, 'TWILIO_AUTH_TOKEN', None) or os.getenv('TWILIO_AUTH_TOKEN')
    from_whatsapp = getattr(config, 'TWILIO_WHATSAPP_NUMBER', None) or os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

    if from_whatsapp and not from_whatsapp.startswith('whatsapp:'):
        from_whatsapp = f"whatsapp:{from_whatsapp}"

    message_body = (
        f"✨ *BharVeen Store - Order Confirmed!* ✨\n\n"
        f"Hello *{customer_name}*! 🎉\n"
        f"Your order *#ORD-{order_id}* has been placed successfully.\n\n"
        f"💰 *Total Amount:* ₹{float(amount):.2f}\n"
        f"📦 *Items:* {items_summary}\n\n"
        f"Thank you for shopping with *BharVeen Store*! We are packing your order for fast dispatch."
    )

    # 1. Try UltraMsg if configured
    if ultramsg_instance and ultramsg_token:
        try:
            url = f"https://api.ultramsg.com/{ultramsg_instance}/messages/chat"
            res = requests.post(
                url,
                data={
                    "token": ultramsg_token,
                    "to": clean_phone,
                    "body": message_body
                },
                timeout=10
            )
            app.logger.info("UltraMsg WhatsApp notification status for order #%s: %s", order_id, res.status_code)
            return res.status_code in (200, 201)
        except Exception as e:
            app.logger.error("Failed to send WhatsApp notification via UltraMsg: %s", str(e))

    # 2. Try Twilio if configured
    if account_sid and auth_token:
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
            res = requests.post(
                url,
                auth=(account_sid, auth_token),
                data={
                    "From": from_whatsapp,
                    "To": f"whatsapp:{clean_phone}",
                    "Body": message_body
                },
                timeout=10
            )
            app.logger.info("Twilio WhatsApp order confirmation status for order #%s: %s", order_id, res.status_code)
            return res.status_code in (200, 201)
        except Exception as e:
            app.logger.error("Failed to send WhatsApp notification for order #%s: %s", order_id, str(e))
            return False

    app.logger.info("No WhatsApp API credentials configured (Twilio/UltraMsg). WhatsApp message prepared for %s (Order #%s)", clean_phone, order_id)
    return False


@app.route('/save_address', methods=['POST'])
def save_address():
    if 'user_id' not in session:
        flash("Please Login")
        return redirect('/user-login')

    full_name = request.form.get('full_name', '').strip()
    phone = request.form.get('phone', '').strip()
    address_line = request.form.get('address', '').strip()
    city = request.form.get('city', '').strip()
    state = request.form.get('state', '').strip()
    pincode = request.form.get('pincode', '').strip()
    selected_products = request.form.getlist('selected_products')

    if full_name or phone or city:
        formatted_address = f"{full_name}\n{address_line}\n{city}, {state} - {pincode}\nPhone: {phone}"
    else:
        formatted_address = address_line

    session['delivery_address'] = formatted_address
    session['delivery_phone'] = phone
    session['delivery_name'] = full_name
    session['selected_products'] = selected_products
    return redirect('/user/pay')

@app.route('/user/pay', methods=['POST','GET'])
def user_pay():

    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/user-login')

    user_id = session['user_id']

    # Get selected products
    selected_products = session.get("selected_products")

    if not selected_products:
        flash("Please select at least one product!", "danger")
        return redirect('/cart')

    con = get_db()
    cursor = con.cursor(dictionary=True)

    total_amount = 0
    selected_items = []

    for product_id in selected_products:

        cursor.execute("""
            SELECT
                cart.product_id,
                cart.quantity,
                products.name,
                products.price,
                products.image
            FROM cart
            JOIN products
            ON cart.product_id = products.product_id
            WHERE cart.user_id = %s
            AND cart.product_id = %s
        """, (user_id, product_id))

        item = cursor.fetchone()

        if item:
            selected_items.append(item)
            total_amount += item['price'] * item['quantity']

    cursor.close()
    con.close()

    if not selected_items:
        flash("Selected products are not available!", "danger")
        return redirect('/cart')

    # Razorpay amount must be in paise
    razorpay_amount = int(total_amount * 100)

    razorpay_order = razorpay_client.order.create({
        "amount": razorpay_amount,
        "currency": "INR",
        "payment_capture": "1"
    })

    session['razorpay_order_id'] = razorpay_order['id']

    # Store selected products temporarily
    session['selected_products'] = selected_products

    return render_template(
        "user/payment.html",
        amount=total_amount,
        key_id=config.RAZORPAY_KEY_ID,
        order_id=razorpay_order['id']
    )

@app.route('/payment-success')
def payment_success():

    payment_id = request.args.get('payment_id')
    order_id = request.args.get('order_id')

    if not payment_id:
        flash("Payment failed!", "danger")
        return redirect('/user/cart')

    return render_template(
        "user/payment_success.html",
        payment_id=payment_id,
        order_id=order_id
    )

@app.route('/verify-payment', methods=['POST'])
def verify_payment():

    if 'user_id' not in session:
        flash("Please login to complete the payment.", "danger")
        return redirect('/user-login')

    # Get logged-in user
    user_id = session['user_id']
    address=session['delivery_address']
    # Read Razorpay values
    razorpay_payment_id = request.form.get('razorpay_payment_id')
    razorpay_order_id = request.form.get('razorpay_order_id')
    razorpay_signature = request.form.get('razorpay_signature')

    if not (razorpay_payment_id and razorpay_order_id and razorpay_signature):
        flash("Payment verification failed (missing data).", "danger")
        return redirect('/cart')

    # Verify Razorpay signature
    payload = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }

    try:

        razorpay_client.utility.verify_payment_signature(payload)

    except Exception as e:

        app.logger.error(
            "Razorpay signature verification failed: %s",
            str(e)
        )

        flash("Payment verification failed. Please contact support.", "danger")
        return redirect('/cart')

    # Get selected products
    selected_products = session.get('selected_products', [])

    if not selected_products:
        flash("No products selected.", "danger")
        return redirect('/cart')

    # Connect database
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:

        total_amount = 0
        selected_items = []

        # Get selected products from MySQL cart
        for product_id in selected_products:

            cursor.execute("""
                SELECT
                    cart.product_id,
                    cart.quantity,
                    products.name,
                    products.price
                FROM cart
                JOIN products
                    ON cart.product_id = products.product_id
                WHERE cart.user_id = %s
                AND cart.product_id = %s
            """, (user_id, product_id))

            item = cursor.fetchone()

            if item:

                selected_items.append(item)

                total_amount += item['price'] * item['quantity']

        # Check selected products
        if not selected_items:

            flash("Selected products are not available.", "danger")
            return redirect('/cart')

        # Insert order
        cursor.execute("""
            INSERT INTO orders
            (user_id, razorpay_order_id, razorpay_payment_id,delivery_address, amount, payment_status)
            VALUES (%s, %s, %s,%s, %s, %s)
        """, (
            user_id,
            razorpay_order_id,
            razorpay_payment_id,
            address,
            total_amount,
            'paid'
        ))

        order_db_id = cursor.lastrowid

        # Insert selected items into order_items
        for item in selected_items:

            cursor.execute("""
                INSERT INTO order_items
                (order_id, product_id, product_name, quantity, price, address)
                VALUES (%s, %s, %s,%s, %s, %s)
            """, (
                order_db_id,
                item['product_id'],
                item['name'],
                item['quantity'],
                item['price'],
                address
            ))

        # Remove only purchased products from cart
        for product_id in selected_products:

            cursor.execute("""
                DELETE FROM cart
                WHERE user_id = %s
                AND product_id = %s
            """, (user_id, product_id))

        # Save everything
        conn.commit()

        # Extract phone and customer name for WhatsApp notification
        phone = session.get('delivery_phone', '')
        customer_name = session.get('delivery_name') or session.get('user_name', 'Valued Customer')
        items_summary = ", ".join([f"{it['name']} (x{it['quantity']})" for it in selected_items])

        # Send WhatsApp confirmation asynchronously
        try:
            threading.Thread(
                target=send_whatsapp_order_notification,
                args=(phone, order_db_id, total_amount, customer_name, items_summary, address),
                daemon=True
            ).start()
        except Exception as wa_err:
            app.logger.warning("Could not dispatch background WhatsApp notification: %s", str(wa_err))

        # Clear temporary session data
        session.pop('selected_products', None)
        session.pop('razorpay_order_id', None)

        flash("Payment successful and order placed!", "success")

        return redirect(
            f"/user/order-success/{order_db_id}"
        )

    except Exception as e:

        conn.rollback()

        app.logger.error(
            "Order storage failed: %s\n%s",
            str(e),
            traceback.format_exc()
        )

        flash(
            "There was an error saving your order. Contact support.",
            "danger"
        )

        return redirect('/cart')

    finally:

        cursor.close()
        conn.close()
@app.route('/user/order-success/<int:order_db_id>')
def order_success(order_db_id):
    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/user-login')

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM orders WHERE order_id=%s AND user_id=%s", (order_db_id, session['user_id']))
    order = cursor.fetchone()

    cursor.execute("""
        SELECT order_items.*, products.image, products.category
        FROM order_items
        LEFT JOIN products ON order_items.product_id = products.product_id
        WHERE order_items.order_id=%s
    """, (order_db_id,))
    items = cursor.fetchall()

    cursor.close()
    conn.close()

    if not order:
        flash("Order not found.", "danger")
        return redirect('/products')

    order_dict = dict(order) if order else {}
    delivery_addr = order_dict.get('delivery_address') or ''
    phone_match = re.search(r'Phone:\s*([0-9+]+)', delivery_addr)
    phone_raw = phone_match.group(1) if phone_match else ''
    clean_digits = re.sub(r'[^0-9]', '', phone_raw)
    if len(clean_digits) == 10:
        clean_phone = "91" + clean_digits
    else:
        clean_phone = clean_digits

    # Pre-filled WhatsApp receipt text
    items_text = ", ".join([f"{it['product_name']} (x{it['quantity']})" for it in items])
    wa_msg = (
        f"✨ *BharVeen Store - Order Confirmation* ✨\n\n"
        f"Hello! My order *#ORD-{order['order_id']}* has been placed successfully. 🎉\n\n"
        f"💰 *Total Paid:* ₹{float(order['amount']):.2f}\n"
        f"📦 *Items:* {items_text}\n\n"
        f"Please share shipping & tracking updates here. Thank you!"
    )
    encoded_text = urllib.parse.quote(wa_msg)
    if clean_phone:
        whatsapp_link = f"https://api.whatsapp.com/send?phone={clean_phone}&text={encoded_text}"
    else:
        whatsapp_link = f"https://api.whatsapp.com/send?text={encoded_text}"

    return render_template(
        "/user/order_success.html",
        order=order,
        items=items,
        whatsapp_link=whatsapp_link,
        customer_phone=phone_raw
    )
@app.route('/user/my-orders')
def my_orders():
    if 'user_id' not in session:
        flash("Please login!", "danger")    
        return redirect('/user-login')

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM orders WHERE user_id=%s ORDER BY created_at DESC", (session['user_id'],))
    orders = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("user/my_orders.html", orders=orders)


@app.route("/user/download-invoice/<int:order_id>")
def download_invoice(order_id):

    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/user-login')

    # Fetch order
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM orders WHERE order_id=%s AND user_id=%s",
                   (order_id, session['user_id']))
    order = cursor.fetchone()

    cursor.execute("SELECT * FROM order_items WHERE order_id=%s", (order_id,))
    items = cursor.fetchall()

    cursor.close()
    conn.close()

    if not order:
        flash("Order not found.", "danger")
        return redirect('/user/my-orders')

    # Render invoice HTML
    html = render_template("user/invoice.html", order=order, items=items)

    pdf = generate_pdf(html)
    if not pdf:
        flash("Error generating PDF", "danger")
        return redirect('/user/my-orders')

    # Prepare response
    response = make_response(pdf.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f"attachment; filename=invoice_{order_id}.pdf"

    return response

if __name__=="__main__":
    app.run(debug=True)