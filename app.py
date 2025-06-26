from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Product, Rating, Review
from forms import ReviewForm
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gunja_prajapati_secret'

# PostgreSQL URI from environment OR fallback to SQLite for local dev
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL") or \
    'sqlite:///' + os.path.join(basedir, 'ecommerce.db')

app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB max upload

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists. Please login.')
            return redirect(url_for('register'))
        new_user = User(email=email, role='user')
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!')
            return redirect(url_for('admin_dashboard') if user.role == 'admin' else 'home')
        else:
            flash('Invalid credentials. Try again.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.')
    return redirect(url_for('home'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('home'))
    products = Product.query.all()
    return render_template('admin_dashboard.html', products=products)

@app.route('/admin/add-product', methods=['GET', 'POST'])
@login_required
def add_product():
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('home'))
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])  # Use float
        image_file = request.files.get('image')
        filename = None

        if image_file and allowed_file(image_file.filename):
            filename = image_file.filename
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)

        new_product = Product(name=name, description=description, price=price, image_file=filename)
        db.session.add(new_product)
        db.session.commit()
        flash('Product added successfully.')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_product.html')

@app.route('/admin/edit-product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('home'))
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form['description']
        product.price = float(request.form['price'])
        image_file = request.files.get('image')

        if image_file and allowed_file(image_file.filename):
            filename = image_file.filename
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            product.image_file = filename

        db.session.commit()
        flash('Product updated!')
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_product.html', product=product)

@app.route('/admin/delete-product/<int:product_id>')
@login_required
def delete_product(product_id):
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('home'))
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted!')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/product/<int:product_id>')
@login_required
def view_product(product_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    product = Product.query.get_or_404(product_id)
    return render_template('view_product.html', product=product)

@app.route('/products')
def view_products():
    products = Product.query.all()
    return render_template('products.html', products=products)

@app.route('/product/<int:product_id>', methods=['GET', 'POST'])
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    reviews = Review.query.filter_by(product_id=product_id).all()
    avg_rating = db.session.query(db.func.avg(Rating.stars)).filter_by(product_id=product_id).scalar() or 0
    form = ReviewForm()

    if form.validate_on_submit() and current_user.is_authenticated:
        review = Review(content=form.content.data, user_id=current_user.id, product_id=product_id)
        rating = Rating(stars=form.stars.data, user_id=current_user.id, product_id=product_id)
        db.session.add_all([review, rating])
        db.session.commit()
        flash('Your review and rating have been posted.', 'success')
        return redirect(url_for('product_detail', product_id=product_id))

    return render_template(
        'product_detail.html',
        product=product,
        reviews=reviews,
        avg_rating=round(avg_rating, 1),
        form=form
    )

@app.route('/rate/<int:product_id>', methods=['POST'])
@login_required
def rate_product(product_id):
    stars = int(request.form['stars'])
    rating = Rating(stars=stars, user_id=current_user.id, product_id=product_id)
    db.session.add(rating)
    db.session.commit()
    flash('Thank you for rating!')
    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/create_admin')
def create_admin():
    admin_email = "admin@example.com"
    admin_password = "admin123"
    existing = User.query.filter_by(email=admin_email).first()
    if existing:
        return "Admin already exists!"
    new_admin = User(email=admin_email, role='admin')
    new_admin.set_password(admin_password)
    db.session.add(new_admin)
    db.session.commit()
    return "Admin user created!"

@app.route('/create_tables')
def create_tables():
    db.create_all()
    return "Tables created!"

if __name__ == '__main__':
    app.run(debug=True)
