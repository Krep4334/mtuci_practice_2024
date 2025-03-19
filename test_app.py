import pytest
from app import app, get_db_connection, get_vacancies, parse_vacancies
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