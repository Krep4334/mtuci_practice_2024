# Flask Vacancies App

This project is a Flask application that interacts with the HeadHunter API to fetch vacancy data and store it in a PostgreSQL database. The application provides a web interface to search for vacancies, display results, and show statistics about the vacancies.

## Features

- Fetch vacancies from the HeadHunter API based on a given profession.
- Store vacancy data in a PostgreSQL database.
- Display the fetched vacancies on a web page.
- Sort vacancies by salary.
- Display all vacancies stored in the database.
- Filter vacancies by various parameters.
- Show top 3 professions by average salary in RUR.

## Project Structure

```
your_project/
│
├── app.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── templates/
    ├── index.html
    └── all_vacancies.html
```

## Getting Started

### Prerequisites

- Docker
- Docker Compose

### Installation

1. Clone the repository:

```
git clone https://github.com/Krep4334/mtuci_practice_2024.git
cd mtuci_practice_2024
```

2. Create and configure your environment file:
``` touch .env ```

Add the following environment variables to your .env file:
```
FLASK_ENV=development
DATABASE_URL=postgres://krep:199129@db:5432/for_practice
```

Usage
Build and run the Docker containers:

```
docker-compose -p myproject build
docker-compose -p myproject up
```
The application should now be accessible at http://localhost:5001.

Application Endpoints

`/` - The main page where you can search for vacancies.

`/all_vacancies` - Page displaying all vacancies stored in the database.

`/apidocs` - Swagger page for testing

Stopping the Containers
To stop the running containers, use:

```docker-compose -p myproject down```

Project Files
- `app.py` - The main Flask application file.
- `Dockerfile` - The Dockerfile for building the Flask application image.
- `docker-compose.yml` - Docker Compose configuration file for setting up the Flask and PostgreSQL services.
- `requirements.txt` - File listing Python dependencies.
- `templates/` - Directory containing HTML templates for the web application.
- `README.md` - Users manual
