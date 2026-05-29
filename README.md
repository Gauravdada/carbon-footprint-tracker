# 🌿 Carbon Footprint Tracker

A full-stack web application for tracking daily carbon emissions, 
built for Indian users with city-specific targets.

## Features
- Email/password login with email verification
- Google OAuth login
- Daily CO₂ calculation based on real Indian emission factors (CEA, MoRTH, CPCB)
- City-specific targets for 100+ Indian cities
- AI-powered reduction insights via Claude API
- InShorts-style motivational feed
- Dashboard with history chart

## Tech Stack
- Python, Flask, SQLAlchemy
- Microsoft SQL Server
- Anthropic Claude API
- Google OAuth (Authlib)
- Flask-Login, Flask-Mail, Flask-WTF

## Setup
1. Clone the repo
2. Create virtual environment: `python -m venv .venv`
3. Activate: `.venv\Scripts\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and fill in your values
6. Run: `python app.py`
