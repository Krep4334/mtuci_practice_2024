import requests
import json

# Функция для получения данных с hh.ru API
def get_vacancies(profession, page=0, per_page=20):
    url = "https://api.hh.ru/vacancies"
    params = {
        'text': profession,
        'page': page,
        'per_page': per_page
    }
    response = requests.get(url, params=params)
    response.raise_for_status()  # Проверка на ошибки
    return response.json()

# Функция для парсинга названий профессий, резюме и требований
def parse_vacancies(data):
    vacancies = []
    for item in data['items']:
        vacancy = {
            'title': item['name'],
            'snippet': item['snippet']['responsibility'],
            'requirement': item['snippet']['requirement']
        }
        vacancies.append(vacancy)
    return vacancies

# Основная функция
def main(profession, num_pages=5):
    all_vacancies = []
    for page in range(num_pages):  # Парсим num_pages страниц
        data = get_vacancies(profession, page=page)
        vacancies = parse_vacancies(data)
        all_vacancies.extend(vacancies)
    
    with open('vacancies.json', 'w', encoding='utf-8') as f:
        json.dump(all_vacancies, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    profession = input("Введите название профессии для поиска: ")
    main(profession)
