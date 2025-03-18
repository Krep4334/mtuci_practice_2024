import pytest
from app import app, get_db_connection, get_vacancies, parse_vacancies, salary_to_numeric, save_to_db
import os

# Фикстура для тестового клиента Flask
@pytest.fixture
def test_client():
    app.config['TESTING'] = True
    app.config['DATABASE_URL'] = "postgresql://user:password@localhost/test_db"  # используем тестовую базу данных
    with app.test_client() as client:
        yield client

# Фикстура для подключения к базе данных
@pytest.fixture
def test_db_connection():
    conn = get_db_connection()
    yield conn
    conn.close()

# Тест для salary_to_numeric()
def test_salary_to_numeric():
    assert salary_to_numeric("1000-2000 RUR") == 1500
    assert salary_to_numeric("1500 RUR") == 1500
    assert salary_to_numeric("Не указана") == 0
    assert salary_to_numeric("abc") == 0  # некорректная строка, должно возвращать 0

# Тест для parse_vacancies()
def test_parse_vacancies():
    data = {
        'items': [
            {
                'id': '1',
                'name': 'Vacancy 1',
                'snippet': {'responsibility': 'Some responsibility', 'requirement': 'Some requirement'},
                'salary': {'from': 1000, 'to': 2000, 'currency': 'RUR'},
                'alternate_url': 'http://example.com/1'
            },
            {
                'id': '2',
                'name': 'Vacancy 2',
                'snippet': {'responsibility': 'Another responsibility', 'requirement': 'Another requirement'},
                'salary': None,
                'alternate_url': 'http://example.com/2'
            }
        ]
    }

    vacancies = parse_vacancies(data)
    assert len(vacancies) == 2
    assert vacancies[0]['salary'] == '1000-2000 RUR'
    assert vacancies[1]['salary'] == 'Не указана'

# Тест для get_vacancies()
def test_get_vacancies():
    profession = "developer"
    data = get_vacancies(profession)
    assert 'items' in data  # Проверяем, что ответ содержит список вакансий
    assert len(data['items']) > 0  # Убедимся, что вакансий больше 0

# Тест для главной страницы (GET-запрос)
def test_index(client):
    response = client.get('/')
    assert response.status_code == 200
    assert 'Введите профессию' in response.data.decode('utf-8')  # Проверяем, что текст на странице присутствует


# Тест для сортировки вакансий (POST-запрос)
def test_sort_vacancies(client):
    vacancies = [
        {'salary': '1000-2000 RUR', 'title': 'Vacancy 1'},
        {'salary': '1500 RUR', 'title': 'Vacancy 2'}
    ]
    
    response = client.post('/sort_vacancies', json={'vacancies': vacancies, 'sort_by_salary': 'desc'})
    sorted_vacancies = response.json
    assert sorted_vacancies[0]['title'] == 'Vacancy 2'

# Тест для работы с базой данных (сохранение вакансий)
def test_save_to_db(db_connection):
    vacancies = [
        {'id': '1', 'title': 'Vacancy 1', 'snippet': 'Snippet 1', 'requirement': 'Requirement 1', 'salary': '1000-2000 RUR', 'url': 'http://example.com/1'},
        {'id': '2', 'title': 'Vacancy 2', 'snippet': 'Snippet 2', 'requirement': 'Requirement 2', 'salary': '1500 RUR', 'url': 'http://example.com/2'}
    ]
    save_to_db(vacancies, db_connection)

    cursor = db_connection.cursor()
    cursor.execute('SELECT * FROM vacancies WHERE id = %s', ('1',))
    vacancy = cursor.fetchone()
    assert vacancy is not None
    assert vacancy[1] == 'Vacancy 1'  # Проверяем, что название вакансии сохранено
