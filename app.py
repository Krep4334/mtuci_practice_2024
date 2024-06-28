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
    conn = psycopg2.connect(db_url)
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS vacancies (
        id VARCHAR(255) PRIMARY KEY,
        title TEXT,
        snippet TEXT,
        requirement TEXT,
        salary TEXT,
        url TEXT
    )
    '''
    cursor = conn.cursor()
    cursor.execute(create_table_query)
    conn.commit()
    cursor.close()
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
            if salary['currency'] != 'RUR' and salary['currency']:
                continue
            salary_str = f"{salary['from']}-{salary['to']} {salary['currency']}" if salary['from'] and salary['to'] else salary['from'] if salary['from'] else salary['to']
        else:
            salary_str = 'Не указана'
        
        vacancy = {
            'id': item['id'],
            'title': clean_text(item['name']),
            'snippet': clean_text(item['snippet'].get('responsibility')),
            'requirement': clean_text(item['snippet'].get('requirement')),
            'salary': salary_str,
            'url': item['alternate_url']
        }
        vacancies.append(vacancy)
    return vacancies

def save_to_db(vacancies, conn):
    cursor = conn.cursor()
    
    insert_query = '''
    INSERT INTO vacancies (id, title, snippet, requirement, salary, url)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title,
    snippet = EXCLUDED.snippet,
    requirement = EXCLUDED.requirement,
    salary = EXCLUDED.salary,
    url = EXCLUDED.url
    '''
    for vacancy in vacancies:
        cursor.execute(insert_query, (
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
        parts = salary_str.split('-')
        if len(parts) == 2:
            return (int(parts[0].strip()) + int(parts[1].strip())) // 2
        return int(parts[0].strip())
    except (ValueError, IndexError):
        return 0

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Main page to search for vacancies
    ---
    parameters:
      - name: profession
        in: query
        type: string
        required: true
        description: Profession to search for
      - name: num_pages
        in: query
        type: integer
        required: false
        default: 5
        description: Number of pages to fetch
    responses:
      200:
        description: A list of vacancies
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
              title:
                type: string
              snippet:
                type: string
              requirement:
                type: string
              salary:
                type: string
              url:
                type: string
    """
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
    """
    Sort vacancies by salary
    ---
    parameters:
      - name: vacancies
        in: body
        type: array
        required: true
        description: A list of vacancies to sort
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
              title:
                type: string
              snippet:
                type: string
              requirement:
                type: string
              salary:
                type: string
              url:
                type: string
      - name: sort_by_salary
        in: query
        type: string
        required: true
        description: Sort direction (asc or desc)
    responses:
      200:
        description: A sorted list of vacancies
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
              title:
                type: string
              snippet:
                type: string
              requirement:
                type: string
              salary:
                type: string
              url:
                type: string
    """
    vacancies = request.json['vacancies']
    sort_by_salary = request.json['sort_by_salary']
    sorted_vacancies = sorted(vacancies, key=lambda x: salary_to_numeric(x['salary']), reverse=(sort_by_salary == 'desc'))
    return jsonify(sorted_vacancies)

@app.route('/all_vacancies')
def all_vacancies():
    """
    Display all vacancies from the database
    ---
    responses:
      200:
        description: A list of all vacancies
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
              title:
                type: string
              snippet:
                type: string
              requirement:
                type: string
              salary:
                type: string
              url:
                type: string
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, snippet, requirement, salary, url FROM vacancies')
    vacancies = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(*) FROM vacancies')
    vacancy_count = cursor.fetchone()[0]

    cursor.execute('''
    SELECT title, ROUND(AVG(
        CASE 
            WHEN position('-' in salary) > 0 THEN
                (CAST(substring(salary, '(\d+)-') AS bigint) + CAST(substring(salary, '-(\d+)') AS bigint)) / 2
            ELSE CAST(REGEXP_REPLACE(salary, '[^0-9]', '', 'g') AS bigint)
        END
    )) AS average_salary
    FROM vacancies
    WHERE salary <> 'Не указана' AND salary LIKE '%RUR%'
    GROUP BY title
    ORDER BY average_salary DESC
    LIMIT 3
    ''')
    top_salaries = cursor.fetchall()

    top_salaries = [{'name': row[0], 'average_salary': int(row[1])} for row in top_salaries]

    cursor.close()
    conn.close()
    return render_template('all_vacancies.html', vacancies=vacancies, vacancy_count=vacancy_count, top_salaries=top_salaries)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
