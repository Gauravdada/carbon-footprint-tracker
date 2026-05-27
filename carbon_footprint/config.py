import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    WTF_CSRF_ENABLED = True

    _SERVER   = os.environ.get("SQL_SERVER", "localhost")
    _DATABASE = os.environ.get("SQL_DATABASE", "CarbonFootprintDB")
    _WIN_AUTH = os.environ.get("USE_WINDOWS_AUTH", "1") == "1"
    _USERNAME = os.environ.get("SQL_USERNAME", "sa")
    _PASSWORD = os.environ.get("SQL_PASSWORD", "")

    if _WIN_AUTH:
        _CONN = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={_SERVER};"
            f"DATABASE={_DATABASE};"
            f"Trusted_Connection=yes;"
        )
    else:
        _CONN = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={_SERVER};"
            f"DATABASE={_DATABASE};"
            f"UID={_USERNAME};"
            f"PWD={_PASSWORD};"
        )

    SQLALCHEMY_DATABASE_URI = (
        "mssql+pyodbc:///?odbc_connect=" + _CONN.replace(" ", "+")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    BASE_URL          = os.environ.get("BASE_URL", "")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

    GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    MAIL_SERVER         = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT           = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS        = os.environ.get("MAIL_USE_TLS", "1") == "1"
    MAIL_USERNAME       = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD       = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_USERNAME", "")

    CO2_FACTORS = {
        "car_petrol":       0.21,
        "car_diesel":       0.17,
        "two_wheeler":      0.08,
        "electricity":      0.82,
        "lpg_cooking":      2.98,
        "air_travel":       0.255,
        "public_transport": 0.04,
    }

    CITY_TARGETS = {
        # Maharashtra
        "Pune": 1.8, "Mumbai": 1.5, "Nagpur": 2.1, "Nashik": 1.9,
        "Aurangabad": 2.0, "Solapur": 1.8, "Kolhapur": 1.7,
        "Thane": 1.6, "Navi Mumbai": 1.6, "Amravati": 1.9,
        # Delhi NCR
        "Delhi": 2.3, "Gurugram": 2.2, "Noida": 2.1,
        "Faridabad": 2.2, "Ghaziabad": 2.3,
        # Karnataka
        "Bengaluru": 1.7, "Mysuru": 1.5, "Hubli": 1.8,
        "Mangaluru": 1.6, "Belagavi": 1.7,
        # Tamil Nadu
        "Chennai": 1.6, "Coimbatore": 1.7, "Madurai": 1.6,
        "Tiruchirappalli": 1.5, "Salem": 1.6, "Tiruppur": 1.7,
        # Telangana & AP
        "Hyderabad": 1.9, "Warangal": 1.8, "Visakhapatnam": 2.0,
        "Vijayawada": 1.9, "Guntur": 1.8,
        # Gujarat
        "Ahmedabad": 2.1, "Surat": 2.0, "Vadodara": 2.0,
        "Rajkot": 1.9, "Bhavnagar": 1.8, "Jamnagar": 1.9,
        # Rajasthan
        "Jaipur": 2.0, "Jodhpur": 1.9, "Udaipur": 1.7,
        "Kota": 2.1, "Ajmer": 1.8,
        # Uttar Pradesh
        "Lucknow": 2.2, "Kanpur": 2.4, "Agra": 2.2,
        "Varanasi": 2.1, "Prayagraj": 2.1, "Meerut": 2.3,
        # West Bengal
        "Kolkata": 2.0, "Howrah": 2.1, "Durgapur": 2.3, "Asansol": 2.2,
        # Madhya Pradesh
        "Bhopal": 2.0, "Indore": 2.0, "Jabalpur": 1.9, "Gwalior": 2.1,
        # Punjab & Haryana
        "Ludhiana": 2.2, "Amritsar": 2.0, "Chandigarh": 1.9, "Jalandhar": 2.1,
        # Bihar & Jharkhand
        "Patna": 2.1, "Ranchi": 2.0, "Jamshedpur": 2.3, "Dhanbad": 2.5,
        # Odisha
        "Bhubaneswar": 1.8, "Cuttack": 1.9, "Rourkela": 2.2,
        # Kerala
        "Kochi": 1.5, "Thiruvananthapuram": 1.4, "Kozhikode": 1.5, "Thrissur": 1.5,
        # Northeast
        "Guwahati": 1.7, "Dibrugarh": 1.6, "Agartala": 1.5,
        "Imphal": 1.4, "Shillong": 1.5, "Aizawl": 1.4,
        "Itanagar": 1.4, "Gangtok": 1.3, "Kohima": 1.4,
        # Hill stations / others
        "Dehradun": 1.7, "Shimla": 1.4, "Haridwar": 1.8,
        "Panaji": 1.5, "Margao": 1.5,
        # Chhattisgarh
        "Raipur": 2.1, "Bhilai": 2.3,
    }

    ALL_CITIES = sorted(CITY_TARGETS.keys())