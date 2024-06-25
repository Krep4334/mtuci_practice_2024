from flask import Flask, render_template, request, redirect, url_for
import psycopg2
from psycopg2 import sql
import requests
import json

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
            'title': item['name'],
            'snippet': item['snippet']['responsibility'],
            'requirement': item['snippet']['requirement'],
            'salary': salary_str,
            'views_count': item.get('counters', {}).get('views', 'Не указано')
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
        salary TEXT,
        views_count TEXT
    )
    '''
    cursor.execute(create_table_query)
    
    insert_query = '''
    INSERT INTO vacancies (id, title, snippet, requirement, salary, views_count)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (id) DO NOTHING
    '''
    for vacancy in vacancies:
        cursor.execute(insert_query, (
            vacancy['id'],
            vacancy['title'],
            vacancy['snippet'],
            vacancy['requirement'],
            vacancy['salary'],
            vacancy['views_count']
        ))
    
    conn.commit()
    cursor.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        profession = request.form['profession']
        num_pages = int(request.form.get('num_pages', 5))
        conn = get_db_connection()
        
        all_vacancies = []
        for page in range(num_pages):
            data = get_vacancies(profession, page=page)
            vacancies = parse_vacancies(data)
            all_vacancies.extend(vacancies)
        
        save_to_db(all_vacancies, conn)
        conn.close()
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM vacancies')
    vacancies = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', vacancies=vacancies)

if __name__ == '__main__':
    app.run(debug=True)
