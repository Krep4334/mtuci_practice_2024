from flask import Flask, render_template, request, jsonify
import psycopg2
import requests
import re
import os
from flasgger import Swagger


app = Flask(__name__)
swagger = Swagger(app)

def get_db_connection():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        db_url = "fallback_url"
    conn = psycopg2.connect(db_url)
    
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vacancies (
        id VARCHAR(255) PRIMARY KEY,
        title TEXT,
        snippet TEXT,
        requirement TEXT,
        salary TEXT,
        url TEXT
    )
    ''')
    conn.commit()
    cursor.close()
    
    # Лишний return conn, можно просто оставить conn
    return conn


def get_vacancies(profession, page=0, per_page=20):
    url = "https://api.hh.ru/vacancies"
    params = {}
    params['text'] = profession
    params['page'] = page
    params['per_page'] = per_page
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception("Ошибка API")
    data = response.json()
    return data

def clean_text(text):
    if text:
        return re.sub(r'<[^>]+>', '', text)
    return ''


def parse_vacancies(data):
    vacancies = []
    for item in data['items']:
        salary = item['salary']
        salary_str = 'Не указана'
        if salary:
            if salary['currency']:
                if salary['currency'] != 'RUR':
                    continue
            if salary['from']:
                if salary['to']:
                    salary_str = f"{salary['from']}-{salary['to']} {salary['currency']}"
                else:
                    salary_str = salary['from']
            elif salary['to']:
                salary_str = salary['to']

        vacancy = {
            'id': item['id'],
            'title': clean_text(item['name']),
            'snippet': clean_text(item['snippet']['responsibility']) if 'responsibility' in item['snippet'] else '',
            'requirement': clean_text(item['snippet']['requirement']) if 'requirement' in item['snippet'] else '',
            'salary': salary_str,
            'url': item['alternate_url']
        }
        vacancies.append(vacancy)
    return vacancies


def save_to_db(vacancies, conn):
    cursor = conn.cursor()
    for vacancy in vacancies:
        cursor.execute('''
        INSERT INTO vacancies (id, title, snippet, requirement, salary, url)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
        title = EXCLUDED.title,
        snippet = EXCLUDED.snippet,
        requirement = EXCLUDED.requirement,
        salary = EXCLUDED.salary,
        url = EXCLUDED.url
        ''', (
            vacancy['id'],
            vacancy['title'],
            vacancy['snippet'],
            vacancy['requirement'],
            vacancy['salary'],
            vacancy['url']
        ))
    conn.commit()
    cursor.close()


def salary_to_numeric(salary_str):
    if isinstance(salary_str, int):
        return salary_str
    if salary_str == 'Не указана':
        return 0
    try:
        if '-' in salary_str:
            parts = salary_str.split('-')
            if len(parts) == 2:
                num1 = int(parts[0].strip())
                num2 = int(parts[1].strip())
                return (num1 + num2) // 2
        else:
            return int(salary_str.strip())
    except:
        return 0


@app.route('/', methods=['GET', 'POST'])
def index():
    vacancies = []
    profession = ''
    num_vacancies = 0
    if request.method == 'POST':
        profession = request.form['profession']
        num_pages = request.form.get('num_pages', 5)
        if isinstance(num_pages, str):
            num_pages = int(num_pages)

        conn = get_db_connection()
        all_vacancies = []
        for page in range(num_pages):
            data = get_vacancies(profession, page)
            all_vacancies.extend(parse_vacancies(data))
        
        save_to_db(all_vacancies, conn)
        conn.close()
        vacancies = all_vacancies
        num_vacancies = len(vacancies)
    
    return render_template('index.html', vacancies=vacancies, profession=profession, num_vacancies=num_vacancies)


@app.route('/sort_vacancies', methods=['POST'])
def sort_vacancies():
    vacancies = request.json['vacancies']
    sort_by_salary = request.json['sort_by_salary']
    sorted_vacancies = sorted(vacancies, key=lambda x: salary_to_numeric(x['salary']), reverse=True if sort_by_salary == 'desc' else False)
    return jsonify(sorted_vacancies)


@app.route('/all_vacancies')
def all_vacancies():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, snippet, requirement, salary, url FROM vacancies')
    vacancies = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(*) FROM vacancies')
    vacancy_count = cursor.fetchone()
    if vacancy_count:
        vacancy_count = vacancy_count[0]
    else:
        vacancy_count = 0

    cursor.execute('''
    SELECT title, ROUND(AVG(
        CASE 
            WHEN salary LIKE '%-%' THEN
                (CAST(substring(salary from '(\d+)-') AS bigint) + CAST(substring(salary from '-(\d+)') AS bigint)) / 2
            ELSE CAST(REGEXP_REPLACE(salary, '[^0-9]', '', 'g') AS bigint)
        END
    )) AS avg_salary
    FROM vacancies
    WHERE salary <> 'Не указана' AND salary LIKE '%RUR%'
    GROUP BY title
    ORDER BY avg_salary DESC
    LIMIT 3
    ''')
    top_salaries = cursor.fetchall()
    
    final_top_salaries = []
    for row in top_salaries:
        if row and len(row) == 2:
            final_top_salaries.append({'name': row[0], 'average_salary': int(row[1])})
    
    cursor.close()
    conn.close()
    return render_template('all_vacancies.html', vacancies=vacancies, vacancy_count=vacancy_count, top_salaries=final_top_salaries)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
