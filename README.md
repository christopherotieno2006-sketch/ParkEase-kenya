# ParkEase Kenya

A functional Flask-based web parking management system 

## Features
- Visual available/occupied slot display
- User registration and login
- Vehicle registration
- Parking entry and slot allocation
- Automatic duration and fee calculation
- Payment confirmation before exit
- Receipt generation
- Administrator dashboard and slot management

## Tariff
- Up to 30 minutes: KSh 0
- More than 30 minutes up to 2 hours: KSh 50
- More than 2 hours up to 6 hours: KSh 100
- More than 6 hours: KSh 300

## Run locally
```bash
python -m venv .venv
pip install -r requirements.txt
python app.py
```
Open `http://127.0.0.1:5000`.

Seeded administrator: `admin@parkease.co.ke` / Christopher.admin@MMU

## GitHub
```bash
git init
git add .
git commit -m "Build ParkEase Kenya parking system"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

