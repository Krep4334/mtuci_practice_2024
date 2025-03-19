# Используем официальный образ Python
FROM python:3.12-slim

# Устанавливаем зависимости системы
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта в рабочую директорию
COPY . /app

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем зависимости для тестирования
RUN pip install --no-cache-dir pytest pytest-flask

# Команда для запуска тестов с использованием pytest
CMD ["pytest", "--maxfail=1", "--disable-warnings", "-q"]
