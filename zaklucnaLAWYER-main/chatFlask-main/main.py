from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "skrivni_kljuc_123"

USERS_FILE = 'users.json'
REVIEWS_FILE = 'reviews.json'

def load_users():
    try:
        if not os.path.exists(USERS_FILE):
            return {}
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading users: {e}")
        return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def load_reviews():
    try:
        if not os.path.exists(REVIEWS_FILE):
            return []
        with open(REVIEWS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading reviews: {e}")
        return []

def save_reviews(reviews):
    with open(REVIEWS_FILE, 'w') as f:
        json.dump(reviews, f, indent=4)

@app.route('/')
def zacetna():
    return redirect(url_for('prijava'))

@app.route('/login', methods=['GET', 'POST'])
def prijava():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        users = load_users()
        
        if username in users and users[username]['geslo'] == password:
            session['uporabnisko_ime'] = username
            return redirect(url_for('lawyer_selection'))
        else:
            return render_template('login.html', error="Invalid credentials")
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def registracija():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not all([username, email, password, confirm_password]):
            return render_template('register.html', error="All fields are required")
        
        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match")
        
        users = load_users()
        
        if username in users:
            return render_template('register.html', error="Username already exists")
        
        users[username] = {
            'e_posta': email,
            'geslo': password
        }
        
        save_users(users)
        return redirect(url_for('prijava'))
    
    return render_template('register.html')

@app.route('/menu')
def meni():
    if 'uporabnisko_ime' not in session:
        return redirect(url_for('prijava'))
    return render_template('menu.html', uporabnisko_ime=session['uporabnisko_ime'])

@app.route('/logout')
def logout():
    session.pop('uporabnisko_ime', None)
    return redirect(url_for('prijava'))

@app.route('/lawyer_selection')
def lawyer_selection():
    if 'uporabnisko_ime' not in session:
        return redirect(url_for('prijava'))
    return render_template('lawyer_selection.html', uporabnisko_ime=session['uporabnisko_ime'])

@app.route('/lawyer_chat')
def lawyer_chat():
    if 'uporabnisko_ime' not in session:
        return redirect(url_for('prijava'))

    lawyer_type = request.args.get('type', 'General')

    valid_types = ['Korporativni', 'Kazenska prava', 'Družinski', 'Intelektualni']
    if lawyer_type not in valid_types:
        return redirect(url_for('lawyer_selection'))
    
    return render_template('lawyer_chat.html', lawyer_type=lawyer_type, 
                         uporabnisko_ime=session['uporabnisko_ime'])

@app.route('/lawyer/<specialty>')
def lawyer_chat_specialty(specialty):
    return redirect(url_for('lawyer_chat', type=specialty))

@app.route('/menu')
def legal_services():
    return redirect(url_for('lawyer_selection'))

# === NOVE POTI ZA SISTEM OCEN IN MNENJ ===

@app.route('/reviews')
def reviews():
    """Stran za prikaz vseh ocen in mnenj"""
    if 'uporabnisko_ime' not in session:
        return redirect(url_for('prijava'))
    
    lawyer_type = request.args.get('type', None)
    
    reviews = load_reviews()
    
    # Filtriranje po specializaciji odvetnika, če je določeno
    if lawyer_type:
        filtered_reviews = [r for r in reviews if r['lawyer_type'] == lawyer_type]
    else:
        filtered_reviews = reviews
    
    # Razvrsti ocene po datumu, najnovejše najprej
    filtered_reviews.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('reviews.html', 
                          reviews=filtered_reviews, 
                          lawyer_type=lawyer_type,
                          uporabnisko_ime=session['uporabnisko_ime'])

@app.route('/add_review', methods=['GET', 'POST'])
def add_review():
    """Stran za dodajanje nove ocene"""
    if 'uporabnisko_ime' not in session:
        return redirect(url_for('prijava'))
    
    # Seznam vseh tipov odvetnikov
    lawyer_types = ['Korporativni', 'Kazenska prava', 'Družinski', 'Intelektualni']
    
    if request.method == 'POST':
        # Pridobitev podatkov iz obrazca
        lawyer_type = request.form.get('lawyer_type')
        lawyer_name = request.form.get('lawyer_name')
        rating = int(request.form.get('rating'))
        comment = request.form.get('comment')
        
        # Validacija podatkov
        if not all([lawyer_type, lawyer_name, rating, comment]):
            return render_template('add_review.html', 
                                  error="Vsa polja so obvezna.",
                                  lawyer_types=lawyer_types,
                                  uporabnisko_ime=session['uporabnisko_ime'])
        
        if rating < 1 or rating > 5:
            return render_template('add_review.html', 
                                  error="Ocena mora biti med 1 in 5.",
                                  lawyer_types=lawyer_types,
                                  uporabnisko_ime=session['uporabnisko_ime'])
        
        # Ustvarimo novo oceno
        new_review = {
            'id': generate_review_id(),
            'user': session['uporabnisko_ime'],
            'lawyer_type': lawyer_type,
            'lawyer_name': lawyer_name,
            'rating': rating,
            'comment': comment,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Dodamo oceno v seznam
        reviews = load_reviews()
        reviews.append(new_review)
        save_reviews(reviews)
        
        return redirect(url_for('reviews'))
    
    return render_template('add_review.html', 
                          lawyer_types=lawyer_types,
                          uporabnisko_ime=session['uporabnisko_ime'])

@app.route('/api/reviews', methods=['GET'])
def api_get_reviews():
    """API končna točka za pridobitev ocen v JSON formatu"""
    lawyer_type = request.args.get('type', None)
    
    reviews = load_reviews()
    
    if lawyer_type:
        filtered_reviews = [r for r in reviews if r['lawyer_type'] == lawyer_type]
    else:
        filtered_reviews = reviews
    
    # Razvrsti ocene po datumu, najnovejše najprej
    filtered_reviews.sort(key=lambda x: x['date'], reverse=True)
    
    return jsonify(filtered_reviews)

@app.route('/api/reviews', methods=['POST'])
def api_add_review():
    """API končna točka za dodajanje nove ocene"""
    if 'uporabnisko_ime' not in session:
        return jsonify({'error': 'User not authenticated'}), 401
    
    data = request.get_json()
    
    # Preveri ali so vsi potrebni podatki prisotni
    required_fields = ['lawyer_type', 'lawyer_name', 'rating', 'comment']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Validacija ocene
    try:
        rating = int(data['rating'])
        if rating < 1 or rating > 5:
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Rating must be a number'}), 400
    
    # Ustvarimo novo oceno
    new_review = {
        'id': generate_review_id(),
        'user': session['uporabnisko_ime'],
        'lawyer_type': data['lawyer_type'],
        'lawyer_name': data['lawyer_name'],
        'rating': rating,
        'comment': data['comment'],
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Dodamo oceno v seznam
    reviews = load_reviews()
    reviews.append(new_review)
    save_reviews(reviews)
    
    return jsonify(new_review), 201

@app.route('/api/reviews/<review_id>', methods=['DELETE'])
def api_delete_review(review_id):
    """API končna točka za brisanje ocene"""
    if 'uporabnisko_ime' not in session:
        return jsonify({'error': 'User not authenticated'}), 401
    
    reviews = load_reviews()
    
    # Najdi oceno po ID-ju
    review_index = None
    for i, review in enumerate(reviews):
        if review['id'] == review_id:
            review_index = i
            break
    
    # Če ocene ni, vrnemo napako
    if review_index is None:
        return jsonify({'error': 'Review not found'}), 404
    
    # Preverimo, ali je uporabnik lastnik ocene
    if reviews[review_index]['user'] != session['uporabnisko_ime']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Odstranimo oceno
    deleted_review = reviews.pop(review_index)
    save_reviews(reviews)
    
    return jsonify(deleted_review), 200

def generate_review_id():
    """Generira unikatni ID za oceno"""
    import uuid
    return str(uuid.uuid4())

if __name__ == '__main__':
    app.run(debug=True)