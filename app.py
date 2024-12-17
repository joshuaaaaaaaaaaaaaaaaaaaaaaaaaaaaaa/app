# user_service/app.py
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import requests
import pandas as pd 
from waitress import serve
import os

app = Flask(__name__)
app.secret_key ='691d142e8a5967c9b0c55d8082715e06'

RECOMMENDATION_SERVICE_URL = 'https://web-production-1a11.up.railway.app'  # Recommendation Service URL
DATA_PATH = 'data/Data_Kegiatan_Volunteer_Realistic.xlsx'
DB_PATH = 'database/users.db'
df = pd.read_excel(DATA_PATH)
@app.route('/')
def home():
    return render_template('home1.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        response = requests.post(f"{RECOMMENDATION_SERVICE_URL}/login", json={
            'username': username,
            'password': password
        })

        if response.status_code == 200:
            user_data = response.json()
            session.update(user_data)
            return redirect(url_for('recommendations'))
        return "Invalid credentials!"

    return render_template('login1.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_data = {
            'username': request.form['username'],
            'password': request.form['password'],
            'location': request.form['location'],
            'category': request.form['category']
        }

        response = requests.post(f"{RECOMMENDATION_SERVICE_URL}/register", json=user_data)
        if response.status_code == 201:
            return redirect(url_for('login'))
        return "Username already exists!"

    return render_template('register1.html')

@app.route('/recommendations')
def recommendations():
    if 'username' not in session:
        return redirect(url_for('login'))

    # User information from the session
    username = session.get('username')
    location = session.get('location')
    category = session.get('category')
    applied_projects = session.get('applied_projects', [])

    # Separate logic based on applied projects
    if not applied_projects:  # New user without applied projects
        query_params = {'username': username, 'location': location, 'category': category}
    else:  # Existing user with applied projects
        query_params = {'username': username, 'location': location, 'category': category, 'applied_projects': ','.join(applied_projects)}

    try:
        response = requests.get(f"{RECOMMENDATION_SERVICE_URL}/recommendations", params=query_params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to the recommendation service: {e}")
        return "Error connecting to the recommendation service", 500

    try:
        recommendations = response.json()
    except requests.exceptions.JSONDecodeError:
        print("Failed to decode JSON. Response content:", response.text)
        return "Error decoding response from the recommendation service", 500

    return render_template('recommendations1.html', recommendations=recommendations)

@app.route('/apply/<int:project_id>')
def apply(project_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    response = requests.post(f"{RECOMMENDATION_SERVICE_URL}/apply", json={
        'username': session['username'],
        'project_id': project_id
    })

    if response.status_code == 200:
        # Update session with applied project
        applied_projects = session.get('applied_projects', [])
        applied_projects.append(str(project_id))
        session['applied_projects'] = applied_projects
        return redirect(url_for('applied_projects'))
    return "Error applying for the project!"


@app.route('/search', methods=['GET', 'POST'])
def search():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        query = request.form['query'].lower()
        results = df[df['Nama Kegiatan'].str.contains(query, case=False, na=False) | 
                     df['Lokasi (Kota, Provinsi)'].str.contains(query, case=False, na=False) | 
                     df['Kategori Kegiatan'].str.contains(query, case=False, na=False)]
        # Return the results as JSON for AJAX
        results = results.to_dict(orient='records')
        return jsonify(results)

    return render_template('search1.html')



@app.route('/applied_projects')
def applied_projects():
    if 'username' not in session:
        return redirect(url_for('login'))

    applied_projects = session.get('applied_projects', [])
    projects = []

    # Fetch applied projects from the data
    for project_id in applied_projects:
        project = df.loc[df['id'] == int(project_id)].to_dict(orient='records')
        if project:
            projects.append(project[0])

    return render_template('applied_projects1.html', projects=projects)

from flask import request, redirect, url_for, session

@app.route('/remove_applied_project', methods=['POST'])
def remove_applied_project():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Get the project ID from the form
    project_id = request.form.get('project_id')
    if project_id:
        # Remove the project from the applied projects list in the session
        applied_projects = session.get('applied_projects', [])
        if project_id in applied_projects:
            applied_projects.remove(project_id)
            session['applied_projects'] = applied_projects  # Update the session
    
    # Redirect back to the applied projects page
    return redirect(url_for('applied_projects'))

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))
