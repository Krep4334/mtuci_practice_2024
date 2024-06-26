from flask import Flask, render_template, request, jsonify
import psycopg2
from psycopg2 import sql
import requests
import re

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(
        dbname='for_practice',
        user='krep',
        password='199129',
        host='localhost',
        port='5432'
    )
    return conn

def get_vacancies(profession, page=0, per_page=20):
    url = "https://api.hh.ru/vacancies"
    params = {
        'text': profession,
        'page': page,
        'per_page': per_page
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def clean_text(text):
    if text is None:
        return ''
    cleaned_text = re.sub(r'<[^>]+>', '', text)
    return cleaned_text

def parse_vacancies(data):
    vacancies = []
    for item in data['items']:
        salary = item['salary']
        if salary:
            salary_str = f"{salary['from']}-{salary['to']} {salary['currency']}" if salary['from'] and salary['to'] else salary['from'] if salary['from'] else salary['to']
        else:
            salary_str = 'Не указана'
        
        vacancy = {
            'id': item['id'],
            'title': clean_text(item['name']),
            'snippet': clean_text(item['snippet'].get('responsibility')),
            'requirement': clean_text(item['snippet'].get('requirement')),
            'salary': salary_str
        }
        vacancies.append(vacancy)
    return vacancies

def save_to_db(vacancies, conn):
    cursor = conn.cursor()
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS vacancies (
        id VARCHAR(255) PRIMARY KEY,
        title TEXT,
        snippet TEXT,
        requirement TEXT,
        salary TEXT
    )
    '''
    cursor.execute(create_table_query)
    
    insert_query = '''
    INSERT INTO vacancies (id, title, snippet, requirement, salary)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (id) DO NOTHING
    '''
    for vacancy in vacancies:
        cursor.execute(insert_query, (
            vacancy['id'],
            vacancy['title'],
            vacancy['snippet'],
            vacancy['requirement'],
            vacancy['salary']
        ))
    
    conn.commit()
    cursor.close()

def salary_to_numeric(salary_str):
    if isinstance(salary_str, int):
        return salary_str
    if salary_str == 'Не указана':
        return 0
    try:
        return int(salary_str.split('-')[0].strip())
    except (ValueError, IndexError):
        return 0

@app.route('/', methods=['GET', 'POST'])
def index():
    vacancies = []
    profession = ''
    num_vacancies = 0
    
    if request.method == 'POST':
        profession = request.form['profession']
        num_pages = int(request.form.get('num_pages', 5))
        conn = get_db_connection()
        
        all_vacancies = []
        for page in range(num_pages):
            data = get_vacancies(profession, page=page)
            vacancies_page = parse_vacancies(data)
            all_vacancies.extend(vacancies_page)
        
        save_to_db(all_vacancies, conn)
        conn.close()
        
        vacancies = all_vacancies
        num_vacancies = len(vacancies)
    
    return render_template('index.html', vacancies=vacancies, profession=profession, num_vacancies=num_vacancies)

@app.route('/sort_vacancies', methods=['POST'])
def sort_vacancies():
    vacancies = request.json['vacancies']
    sort_by_salary = request.json['sort_by_salary']
    sorted_vacancies = sorted(vacancies, key=lambda x: salary_to_numeric(x['salary']), reverse=(sort_by_salary == 'desc'))
    return jsonify(sorted_vacancies)

if __name__ == '__main__':
    app.run(debug=True)
