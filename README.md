Crimpit
=========

# Installation

## Install OS (Ubuntu) Requirements

    
## Clone Project

    git clone <repository> crimpit-backend

## Virtual Envirnoment and requirements

    virtualenv -p /path/to/python3.8 venv
    source venv/bin/activate
    pip install -r requirements.txt

# Add Local Settings

    cp config/local.py.example config/local.py
    
    Add all keys and settings in local.py

## Postgres setup

    pip install psycopg2
    sudo su - postgres
    psql
    CREATE USER your-username WITH PASSWORD your-password;
    ALTER USER your-username WITH SUPERUSER;
    CREATE DATABASE db_name;
    GRANT ALL PRIVILEGES ON DATABASE db_name TO your-username;
    \q
    psql -d mu_db -U your-username -h localhost


## run migrations
   
   python manage.py migrate

## Running Development Server

    python manage.py runserver

**Note:** Never forget to enable virtual environment (`source venv/bin/activate`) before running above command and use settings accordingly.

Note:- Admin signup is restricted. To create an admin inform backend user

## Generate Sonar Report

    1. Setup sonarqube and sonar scanner on your system
    2. Then, Access sonar dashboard at localhost:9000
    3. Create your project here and generate auth token for it
    4. Run following command from project root folder:
        sonar-scanner -Dsonar.projectKey=project-name -Dsonar.sources=. -Dsonar.host.url=http://127.0.0.1:9000 \
        -Dsonar.login=auth-key
