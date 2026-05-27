"""
app.py  — Carbon Footprint Flask App
"""

from flask import (Flask, render_template, redirect, url_for,
                   request, flash, session, jsonify)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)
from flask_mail import Mail, Message
from authlib.integrations.flask_client import OAuth
from itsdangerous import URLSafeTimedSerializer
from email_validator import validate_email, EmailNotValidError
from datetime import datetime, date
import os, json, re
import requests as req

from config import Config
from models import db, User, ActivityLog, Calculation

# ── App setup ─────────────────────────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
mail = Mail(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"

serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])

# ── Google OAuth setup ────────────────────────────────────────────
oauth = OAuth(app)
google = oauth.register(
    name="google",
    client_id=app.config.get("GOOGLE_CLIENT_ID"),
    client_secret=app.config.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def get_base_url():
    return app.config.get("BASE_URL", "").rstrip("/") or request.host_url.rstrip("/")


# ══════════════════════════════════════════════════════════════════
#  EMAIL HELPERS
# ══════════════════════════════════════════════════════════════════

def send_verification_email(user):
    token = serializer.dumps(user.email, salt="email-verify")
    verify_url = f"{get_base_url()}/verify/{token}"
    msg = Message(
        subject="✅ Verify your Carbon Footprint account",
        recipients=[user.email],
        body=f"""Hello!

Thank you for registering with Carbon Footprint.

Please verify your email by clicking this link:
{verify_url}

This link expires in 1 hour.

If you did not register, please ignore this email.

— Carbon Footprint Team
"""
    )
    mail.send(msg)


def send_reset_email(user):
    token = serializer.dumps(user.email, salt="password-reset")
    reset_url = f"{get_base_url()}/reset-password/{token}"
    msg = Message(
        subject="🔑 Reset your Carbon Footprint password",
        recipients=[user.email],
        body=f"""Hello!

You requested a password reset for your Carbon Footprint account.

Click this link to reset your password:
{reset_url}

This link expires in 30 minutes.

If you did NOT request this, ignore this email.

— Carbon Footprint Team
"""
    )
    mail.send(msg)


# ══════════════════════════════════════════════════════════════════
#  CLI — flask db-init
# ══════════════════════════════════════════════════════════════════
@app.cli.command("db-init")
def db_init():
    with app.app_context():
        db.create_all()
        print("✅ All database tables created successfully.")


# ══════════════════════════════════════════════════════════════════
#  ROUTE 1 — Home
# ══════════════════════════════════════════════════════════════════
@app.route("/")
def index():
    if current_user.is_authenticated:
        if not current_user.onboarding_done:
            return redirect(url_for("onboarding"))
        return redirect(url_for("feed"))
    return render_template("login.html")


# ══════════════════════════════════════════════════════════════════
#  ROUTE 2 — Register
# ══════════════════════════════════════════════════════════════════
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("feed"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")
        errors   = []

        try:
            valid = validate_email(email, check_deliverability=False)
            email = valid.email
        except EmailNotValidError as e:
            errors.append(f"❌ Invalid email address: {str(e)}")

        if len(password) < 8:
            errors.append("❌ Password must be at least 8 characters.")
        if password != confirm:
            errors.append("❌ Passwords do not match.")

        if not errors:
            if User.query.filter_by(email=email).first():
                errors.append("❌ An account with this email already exists.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("login.html", show_register=True, email=email)

        user = User(email=email, is_verified=False)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        try:
            send_verification_email(user)
            flash("✅ Account created! Check your email to verify before logging in.", "success")
        except Exception:
            user.is_verified = True
            db.session.commit()
            flash("✅ Account created! You can log in now. (Email service not configured)", "warning")

        return render_template("login.html", show_register=False)

    return render_template("login.html", show_register=True)


# ══════════════════════════════════════════════════════════════════
#  ROUTE 3 — Verify Email
# ══════════════════════════════════════════════════════════════════
@app.route("/verify/<token>")
def verify_email(token):
    try:
        email = serializer.loads(token, salt="email-verify", max_age=3600)
    except Exception:
        flash("❌ Verification link is invalid or has expired.", "danger")
        return redirect(url_for("login"))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("❌ User not found.", "danger")
        return redirect(url_for("login"))

    if user.is_verified:
        flash("✅ Email already verified. Please log in.", "info")
        return redirect(url_for("login"))

    user.is_verified = True
    db.session.commit()
    flash("✅ Email verified! You can now log in.", "success")
    return redirect(url_for("login"))


# ══════════════════════════════════════════════════════════════════
#  ROUTE 4 — Login
# ══════════════════════════════════════════════════════════════════
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("feed"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        try:
            valid = validate_email(email, check_deliverability=False)
            email = valid.email
        except EmailNotValidError:
            flash("❌ Please enter a valid email address.", "danger")
            return render_template("login.html")

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("❌ Invalid email or password.", "danger")
            return render_template("login.html")

        if not user.is_verified:
            flash("⚠️ Please verify your email first. Check your inbox.", "warning")
            return render_template("login.html")

        user.last_login = datetime.utcnow()
        db.session.commit()
        login_user(user, remember=remember)

        if not user.onboarding_done:
            return redirect(url_for("onboarding"))

        next_page = request.args.get("next")
        return redirect(next_page or url_for("feed"))

    return render_template("login.html")


# ══════════════════════════════════════════════════════════════════
#  ROUTE 5 — Google Login
# ══════════════════════════════════════════════════════════════════
@app.route("/login/google")
def google_login():
    if not app.config.get("GOOGLE_CLIENT_ID") or not app.config.get("GOOGLE_CLIENT_SECRET"):
        flash("⚠️ Google login is not configured. Please use email & password.", "warning")
        return redirect(url_for("login"))

    base = app.config.get("BASE_URL", "http://localhost:5000").rstrip("/")
    redirect_uri = f"{base}/login/google/callback"
    return google.authorize_redirect(redirect_uri)


# ══════════════════════════════════════════════════════════════════
#  ROUTE 6 — Google Callback
# ══════════════════════════════════════════════════════════════════
@app.route("/login/google/callback")
def google_callback():
    try:
        token     = google.authorize_access_token()
        user_info = token.get("userinfo")
    except Exception:
        flash("❌ Google login failed. Please try again.", "danger")
        return redirect(url_for("login"))

    if not user_info:
        flash("❌ Could not get info from Google.", "danger")
        return redirect(url_for("login"))

    email     = user_info.get("email", "").lower()
    google_id = user_info.get("sub")
    name      = user_info.get("name", "")
    picture   = user_info.get("picture", "")

    user = User.query.filter_by(email=email).first()
    if user:
        user.google_id   = google_id
        user.profile_pic = picture
        user.is_verified = True
    else:
        user = User(
            email=email, google_id=google_id,
            full_name=name, profile_pic=picture, is_verified=True,
        )
        db.session.add(user)

    user.last_login = datetime.utcnow()
    db.session.commit()
    login_user(user)

    flash(f"✅ Welcome, {user.full_name or email}!", "success")
    if not user.onboarding_done:
        return redirect(url_for("onboarding"))
    return redirect(url_for("feed"))


# ══════════════════════════════════════════════════════════════════
#  ROUTE 7 — Forgot Password
# ══════════════════════════════════════════════════════════════════
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        try:
            valid = validate_email(email, check_deliverability=False)
            email = valid.email
        except EmailNotValidError:
            flash("❌ Please enter a valid email address.", "danger")
            return render_template("forgot_password.html")

        user = User.query.filter_by(email=email).first()
        flash("📧 If that email is registered, a reset link has been sent.", "info")

        if user:
            try:
                send_reset_email(user)
            except Exception:
                flash("⚠️ Could not send email. Check MAIL settings in .env.", "warning")

        return render_template("forgot_password.html")

    return render_template("forgot_password.html")


# ══════════════════════════════════════════════════════════════════
#  ROUTE 8 — Reset Password
# ══════════════════════════════════════════════════════════════════
@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        email = serializer.loads(token, salt="password-reset", max_age=1800)
    except Exception:
        flash("❌ Reset link is invalid or expired.", "danger")
        return redirect(url_for("forgot_password"))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("❌ User not found.", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        new_password = request.form.get("password", "")
        confirm      = request.form.get("confirm_password", "")

        errors = []
        if len(new_password) < 8:
            errors.append("❌ Password must be at least 8 characters.")
        if new_password != confirm:
            errors.append("❌ Passwords do not match.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("reset_password.html", token=token)

        user.set_password(new_password)
        user.is_verified = True
        db.session.commit()
        flash("✅ Password reset! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html", token=token)


# ══════════════════════════════════════════════════════════════════
#  ROUTE 9 — Onboarding
# ══════════════════════════════════════════════════════════════════
@app.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    cities = Config.ALL_CITIES

    if request.method == "POST":
        full_name   = request.form.get("full_name", "").strip()
        city        = request.form.get("city", "")
        family_size = request.form.get("family_size", "4")

        errors = []
        if not full_name:
            errors.append("Please enter your name.")
        if city not in Config.CITY_TARGETS:
            errors.append("Please select a valid city.")
        try:
            family_size = max(1, int(family_size))
        except ValueError:
            family_size = 1

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("onboarding.html", cities=cities)

        current_user.full_name       = full_name
        current_user.city            = city
        current_user.family_size     = family_size
        current_user.onboarding_done = True
        db.session.commit()

        flash(f"Welcome, {full_name}! Let's see why your actions matter.", "success")
        return redirect(url_for("feed"))

    return render_template("onboarding.html", cities=cities)


# ══════════════════════════════════════════════════════════════════
#  ROUTE 10 — Feed
# ══════════════════════════════════════════════════════════════════
@app.route("/feed")
@login_required
def feed():
    city       = request.args.get("city", current_user.city or "Pune")
    all_cities = Config.ALL_CITIES
    return render_template("feed.html", city=city,
                           all_cities=all_cities, user=current_user)


# ══════════════════════════════════════════════════════════════════
#  ROUTE 11 — City News API  (used by feed.html via fetch)
# ══════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════
#  REPLACE your existing city_news() function and fallback_cards()
#  with this entire block in app.py
# ══════════════════════════════════════════════════════════════════

@app.route("/api/city-news")
@login_required
def city_news():
    city    = request.args.get("city", current_user.city or "Pune").strip()
    api_key = os.environ.get("NEWSDATA_API_KEY", "")

    real_news = []

    if api_key:
        # Multiple targeted queries to get more environment news
        queries = [
            f'"{city}" air pollution AQI',
            f'"{city}" smog heatwave environment',
            f'"{city}" water pollution toxic waste',
            f'"{city}" climate change weather disaster',
        ]
        colors_map = {0:"card-red", 1:"card-orange", 2:"card-blue", 3:"card-yellow"}
        icons_map  = {0:"🌫️", 1:"🌡️", 2:"💧", 3:"🌪️"}

        for qi, query in enumerate(queries):
            try:
                resp = req.get(
                    "https://newsdata.io/api/1/news",
                    params={
                        "apikey":   api_key,
                        "q":        query,
                        "country":  "in",
                        "language": "en",
                    },
                    timeout=6
                )
                data     = resp.json()
                articles = data.get("results", [])

                for art in articles[:7]:
                    title = (art.get("title") or "").strip()
                    desc  = (art.get("description") or art.get("content") or "").strip()

                    # Skip if city name not in title/desc (avoid Maharashtra-only news)
                    combined = (title + " " + desc).lower()
                    if city.lower() not in combined:
                        continue

                    # Skip if not environment related
                    env_keywords = ["pollution","aqi","air","smog","heat","climate",
                                    "water","toxic","emission","carbon","dust","pm2",
                                    "pm10","ozone","waste","flood","drought","weather",
                                    "temperature","environment","forest","deforest"]
                    if not any(kw in combined for kw in env_keywords):
                        continue

                    # Avoid duplicates
                    if any(r["title"] == title for r in real_news):
                        continue

                    desc = (desc[:300] + "...") if len(desc) > 300 else desc
                    src  = (art.get("source_id") or "News").replace("-"," ").title()

                    real_news.append({
                        "title":   title,
                        "stat":    f"📰 {src}",
                        "body":    desc or "Read the full story for details.",
                        "icon":    icons_map[qi],
                        "color":   colors_map[qi],
                        "source":  src,
                        "type":    "news",
                        "link":    art.get("link", ""),
                    })
            except Exception as e:
                print(f"NewsData query error ({query}): {e}")
                continue

    # Always add AI-generated awareness cards (these are always city-specific)
    awareness = awareness_cards(city)

    # Mix: real news first, then awareness cards
    all_cards = real_news + awareness

    # If no real news at all, use full fallback
    if not all_cards:
        all_cards = fallback_cards(city) + awareness

    return jsonify({"cards": all_cards, "city": city, "total": len(all_cards)})


def awareness_cards(city):
    """
    AI-generated awareness cards — always shown.
    City-specific, environment-focused, alarming and educational.
    """
    return [
        # ── Air Quality Cards ──────────────────────────────────────
        {
            "title": f"How Dangerous Is {city}'s Air Right Now?",
            "stat": "AQI 150–300 is 'Very Poor'",
            "body": f"{city}'s AQI regularly crosses 200 in winter months. An AQI of 200 means every breath you take contains particulate matter equivalent to smoking half a cigarette. Children, elderly, and people with asthma are at severe risk. The lungs cannot filter all this particulate matter — it enters the bloodstream directly.\n\n🔴 What you can do: Wear N95 masks outdoors. Avoid morning walks on high-pollution days. Check AQI daily at aqicn.org before stepping out.",
            "icon": "🌫️", "color": "card-red", "source": "CPCB / WHO", "type": "awareness"
        },
        {
            "title": "PM2.5 — The Invisible Killer in Your City",
            "stat": "PM2.5 causes 1.67 lakh deaths in India yearly",
            "body": f"PM2.5 particles are 2.5 micrometres — 30 times smaller than a human hair. They penetrate deep into your lungs and bloodstream. In {city}, vehicle exhausts and construction dust are the primary sources. Long-term exposure causes permanent lung damage, heart disease, and strokes.\n\n🔴 What you can do: Use air purifiers indoors. Keep windows closed on high AQI days. Plant indoor air-purifying plants like peace lily and spider plant.",
            "icon": "😷", "color": "card-red", "source": "WHO / ICMR", "type": "awareness"
        },
        # ── Heat Cards ─────────────────────────────────────────────
        {
            "title": f"Why Is {city} Getting Hotter Every Year?",
            "stat": "Urban heat islands add 3–5°C extra heat",
            "body": f"Concrete, asphalt, and reduced tree cover trap heat and make cities 3–5°C hotter than surrounding areas. This is called the Urban Heat Island effect. {city} has lost over 40% of its tree cover in the last 20 years due to construction. This directly causes more heatwaves, higher electricity bills, and heat-related deaths.\n\n🟡 What you can do: Plant trees in your society. Paint your roof white — it reflects 80% of heat. Use fans before AC to reduce energy use.",
            "icon": "🌡️", "color": "card-yellow", "source": "NASA / IMD", "type": "awareness"
        },
        {
            "title": "How to Survive {city}'s Extreme Summers",
            "stat": "Heat kills 25,000 Indians yearly",
            "body": f"As temperatures cross 42°C in cities like {city}, heat stroke becomes a real danger. Signs: confusion, no sweating, body temp above 40°C. Heatstroke can kill within hours. The poor, outdoor workers, and elderly are most vulnerable.\n\n🟡 Survival tips: Drink 3–4 litres of water daily even if not thirsty. Avoid outdoor work between 11am–4pm. Eat light meals — heavy food raises body temperature. Wear loose, light-coloured cotton clothes.",
            "icon": "☀️", "color": "card-orange", "source": "NDMA India", "type": "awareness"
        },
        # ── Water Cards ────────────────────────────────────────────
        {
            "title": f"Is {city}'s Water Safe to Drink?",
            "stat": "70% of India's water sources are contaminated",
            "body": f"Industrial effluents, sewage discharge, and pesticide runoff contaminate rivers and groundwater near cities like {city}. Heavy metals like lead, arsenic, and mercury have been found in tap water samples across Indian cities. Long-term exposure causes kidney failure, cancer, and neurological disorders.\n\n💧 What you can do: Use RO+UV water purifiers. Never drink directly from taps in areas near industrial zones. Test your tap water at a government lab — it costs ₹200–500.",
            "icon": "💧", "color": "card-blue", "source": "CPCB / BIS India", "type": "awareness"
        },
        # ── Carbon & Climate Cards ─────────────────────────────────
        {
            "title": "Your Daily Commute's Real Carbon Cost",
            "stat": "Average Indian commuter emits 1.2 kg CO₂/day",
            "body": f"A 10 km petrol car ride emits 2.1 kg of CO₂. Multiply that by 250 working days — that's 525 kg CO₂ per year from commuting alone. In {city}, 60% of vehicle trips are under 5 km — easily replaceable by cycling or walking. Switching to public transport for just 3 days a week cuts your transport emissions by 60%.\n\n🌱 Start today: Walk or cycle for trips under 2 km. Use the metro or bus 2 days a week. Carpool with 2 colleagues — that cuts 3 cars off the road.",
            "icon": "🚗", "color": "card-orange", "source": "MoEFCC India", "type": "awareness"
        },
        {
            "title": "How Electricity Use Destroys Your Air",
            "stat": "India's grid emits 0.82 kg CO₂ per kWh",
            "body": f"Every time you turn on an AC, you're burning coal. India generates 70% of its electricity from coal power plants. A 1.5-tonne AC running 8 hours/day emits 3.9 kg of CO₂ — that's like driving 18 km in a petrol car. In {city}, summer electricity demand causes power plants to run at 110% capacity, releasing massive amounts of SO₂ and NOx.\n\n⚡ Easy savings: Set AC to 24°C — every 1°C lower uses 6% more power. Use inverter ACs — they use 30–50% less electricity. Switch off lights and fans in empty rooms.",
            "icon": "⚡", "color": "card-blue", "source": "CEA India", "type": "awareness"
        },
        # ── Health Impact Cards ────────────────────────────────────
        {
            "title": "Pollution Is Making Your Children Sick",
            "stat": "1 in 3 Indian children has asthma or respiratory illness",
            "body": f"Children breathe faster than adults — meaning they inhale proportionally more polluted air. In high-pollution cities like {city}, children develop smaller lungs permanently. A 2023 study found that children in polluted Indian cities have 30% lower lung capacity by age 12 compared to children in clean-air areas. This is irreversible.\n\n🔴 Protect your children: Keep them indoors on high-AQI days. Use air purifiers in children's bedrooms. Avoid living near highways or industrial areas if possible.",
            "icon": "👧", "color": "card-red", "source": "ICMR / Lancet", "type": "awareness"
        },
        # ── Waste & Plastic Cards ──────────────────────────────────
        {
            "title": f"Plastic Burning in {city} — A Silent Emergency",
            "stat": "India burns 40% of its plastic waste in open air",
            "body": f"Open burning of plastic releases dioxins — chemicals 1,000 times more toxic than cyanide. In {city}'s outskirts and slum areas, plastic burning is common practice as waste management fails to reach all areas. Dioxin exposure causes cancer, birth defects, and immune system damage. The smoke travels up to 10 km.\n\n🟠 What you can do: Never burn plastic or garbage. Report open burning to your municipal corporation. Reduce single-use plastic — carry cloth bags and steel bottles.",
            "icon": "🔥", "color": "card-orange", "source": "CPCB / Greenpeace", "type": "awareness"
        },
        # ── Nature & Trees Cards ───────────────────────────────────
        {
            "title": "Plant Trees — The Cheapest Air Purifier",
            "stat": "One tree absorbs 22 kg of CO₂ per year",
            "body": f"A single mature tree can absorb 22 kg of CO₂ per year and filter up to 100 kg of pollutants from the air. {city} needs to plant 2 million more trees to meet WHO's recommended 9 sq metres of green space per person. Studies show neighbourhoods with more trees have 25% lower PM2.5 levels.\n\n🌱 Start this week: Plant one tree in your society or nearby area. Choose native species like Neem, Peepal, Banyan, or Gulmohar. Water it for the first 3 months — after that it survives on its own.",
            "icon": "🌳", "color": "card-green", "source": "FSI India", "type": "awareness"
        },
        # ── Food & Lifestyle Cards ─────────────────────────────────
        {
            "title": "How Your Food Choices Affect the Air",
            "stat": "Meat production causes 14.5% of global emissions",
            "body": f"Producing 1 kg of beef emits 27 kg of CO₂ — the same as driving 130 km in a petrol car. Even dairy farming in India is a significant methane source. Switching to one plant-based meal per day can reduce your annual food carbon footprint by 500 kg of CO₂. In {city}, seasonal and local vegetables have a 70% smaller carbon footprint than imported foods.\n\n🌱 Try this: Eat one meal without meat or dairy today. Buy vegetables from local markets — less transport = less emissions. Reduce food waste — rotting food in landfills produces methane.",
            "icon": "🥗", "color": "card-green", "source": "FAO / IPCC", "type": "awareness"
        },
        # ── Action Card ────────────────────────────────────────────
        {
            "title": "Small Changes. Massive City Impact.",
            "stat": f"If 1 lakh {city} families act, city CO₂ drops by 1 lakh tonnes",
            "body": f"You might feel powerless against {city}'s pollution problem. But consider this: if just 1 lakh families each save 1 kg of CO₂ per day through small changes — that's 1 lakh tonnes of CO₂ per year removed from the city's air. That equals taking 22,000 cars off the road permanently.\n\nYou already tracked your footprint. Now share it. Tell one friend. Plant one tree. Take the bus once this week. Small consistent actions by many people create city-scale change.\n\n🌿 You've already started — keep going.",
            "icon": "🌍", "color": "card-green", "source": "Carbon Footprint App", "type": "awareness"
        },
    ]


def fallback_cards(city):
    return [
        {
            "title": f"{city}'s Air Quality Is Dangerous",
            "stat": "AQI often exceeds 200",
            "body": f"{city} frequently records AQI above 200 — the 'Very Poor' category. Breathing this air is equivalent to smoking 2 cigarettes daily. PM2.5 particles enter your bloodstream and cause permanent lung damage.",
            "icon": "🌫️", "color": "card-red", "source": "CPCB India", "type": "fallback"
        },
        {
            "title": "Vehicle Pollution Is the #1 Cause",
            "stat": "40% of city pollution from vehicles",
            "body": f"Vehicles contribute over 40% of {city}'s air pollution. A single petrol car emits 2.1 kg of CO₂ per 10 km. With 72 lakh vehicles in cities like Pune, the cumulative impact is catastrophic.",
            "icon": "🚗", "color": "card-orange", "source": "MoRTH India", "type": "fallback"
        },
        {
            "title": "Heatwaves Are the New Normal",
            "stat": "47°C recorded in Indian cities in 2024",
            "body": f"India recorded its hottest temperatures in 2024. Urban areas like {city} are 3–5°C hotter than rural areas due to heat island effects. By 2030, heatwaves that were once-in-50-years events will occur every 5 years.",
            "icon": "🌡️", "color": "card-yellow", "source": "IMD India", "type": "fallback"
        },
        {
            "title": "Water Sources Are Running Dry",
            "stat": "21 Indian cities will run out of groundwater by 2030",
            "body": f"India's NITI Aayog warns that 21 cities including metros near {city} will exhaust groundwater by 2030. Overuse, pollution, and reduced rainfall from climate change are draining aquifers that took thousands of years to fill.",
            "icon": "💧", "color": "card-blue", "source": "NITI Aayog", "type": "fallback"
        },
        {
            "title": "Electricity Grid Adds to CO₂",
            "stat": "0.82 kg CO₂ per kWh",
            "body": f"Every unit of electricity in {city} emits 0.82 kg of CO₂ from coal power plants. A family using 300 kWh/month produces 246 kg of CO₂ just from their electricity bill — equivalent to planting 11 trees to offset.",
            "icon": "⚡", "color": "card-blue", "source": "CEA India", "type": "fallback"
        },
        {
            "title": "Children's Lungs Are Being Damaged Forever",
            "stat": "30% lower lung capacity in polluted city children",
            "body": f"Research shows children growing up in polluted cities like {city} develop 30% lower lung capacity by age 12 compared to children in clean-air areas. This damage is permanent and increases risk of respiratory disease lifelong.",
            "icon": "👧", "color": "card-red", "source": "ICMR / Lancet", "type": "fallback"
        },
        {
            "title": "Plastic Waste Is Poisoning the Air",
            "stat": "India generates 26,000 tonnes of plastic waste daily",
            "body": f"India generates 26,000 tonnes of plastic waste daily. 40% is burned in open air — releasing toxic dioxins and furans that are 1,000 times more toxic than cyanide. This invisible chemical pollution affects {city} and every urban area in India.",
            "icon": "🔥", "color": "card-orange", "source": "CPCB / Greenpeace", "type": "fallback"
        },
    ]
    PYEOF
    
# ══════════════════════════════════════════════════════════════════
#  ROUTE 12 — Calculate CO₂
# ══════════════════════════════════════════════════════════════════
@app.route("/calculate", methods=["GET", "POST"])
@login_required
def calculate():
    if request.method == "POST":
        def f(key):
            try:
                return max(0.0, float(request.form.get(key, 0) or 0))
            except ValueError:
                return 0.0

        car_petrol_km       = f("car_petrol_km")
        car_diesel_km       = f("car_diesel_km")
        two_wheeler_km      = f("two_wheeler_km")
        public_transport_km = f("public_transport_km")
        air_travel_km       = f("air_travel_km")
        electricity_kwh     = f("electricity_kwh")
        lpg_kg              = f("lpg_kg")

        try:
            log_date = date.fromisoformat(request.form.get("log_date", ""))
        except ValueError:
            log_date = date.today()

        log = ActivityLog(
            user_id=current_user.id, log_date=log_date,
            car_petrol_km=car_petrol_km, car_diesel_km=car_diesel_km,
            two_wheeler_km=two_wheeler_km, public_transport_km=public_transport_km,
            air_travel_km=air_travel_km, electricity_kwh=electricity_kwh, lpg_kg=lpg_kg,
        )
        db.session.add(log)
        db.session.flush()

        factors       = Config.CO2_FACTORS
        transport_co2 = (
            car_petrol_km       * factors["car_petrol"]       +
            car_diesel_km       * factors["car_diesel"]       +
            two_wheeler_km      * factors["two_wheeler"]      +
            public_transport_km * factors["public_transport"] +
            air_travel_km       * factors["air_travel"]
        )
        home_co2   = electricity_kwh * factors["electricity"] + lpg_kg * factors["lpg_cooking"]
        total_co2  = transport_co2 + home_co2
        family_co2 = total_co2 * current_user.family_size

        city_daily_kg = (Config.CITY_TARGETS.get(current_user.city, 1.8) * 1000) / 365
        percentile    = min(100, (total_co2 / city_daily_kg) * 50) if city_daily_kg else 50

        calc = Calculation(
            user_id=current_user.id, activity_log_id=log.id,
            transport_co2=round(transport_co2, 3), home_co2=round(home_co2, 3),
            total_co2=round(total_co2, 3), family_co2=round(family_co2, 3),
            city_percentile=round(percentile, 1),
        )
        db.session.add(calc)
        db.session.commit()

        session["last_calc_id"] = calc.id
        return redirect(url_for("insights"))

    return render_template("calculate.html", today=str(date.today()), user=current_user)


# ══════════════════════════════════════════════════════════════════
#  ROUTE 13 — Insights
# ══════════════════════════════════════════════════════════════════
@app.route("/insights")
@login_required
def insights():
    calc_id = session.get("last_calc_id")
    calc    = Calculation.query.get(calc_id) if calc_id else None

    if not calc or calc.user_id != current_user.id:
        flash("Please complete a calculation first.", "info")
        return redirect(url_for("calculate"))

    city = current_user.city or "Pune"
    suggestions = [
        {"title": "Switch to Public Transport",
         "saving": f"Save up to {round(calc.total_co2 * 0.4, 1)} kg CO₂/day",
         "body": f"Replacing your car with bus or metro cuts transport CO₂ by 40%.",
         "icon": "🚌", "action": "Start with 2 days a week on public transport.", "color": "card-green"},
        {"title": "Go Electric for Two-Wheelers",
         "saving": "Save 80% on two-wheeler emissions",
         "body": f"Electric scooters emit near-zero CO₂. {city}'s charging infrastructure is growing fast.",
         "icon": "⚡", "action": "Calculate EV savings vs your current bike at evyatri.in", "color": "card-blue"},
        {"title": "Lower Your Electricity Bill",
         "saving": f"Save {round(calc.home_co2 * 0.2, 1)} kg CO₂ by cutting 20% power",
         "body": "Switch to 5-star BEE-rated ACs. Run AC at 24°C — each degree saves 6% electricity.",
         "icon": "💡", "action": "Set your AC to 24°C starting today.", "color": "card-yellow"},
        {"title": "Replace LPG with Solar Cooking",
         "saving": "Cut cooking emissions by 100%",
         "body": "Solar cookers work 300+ days a year. Or switch to induction — faster and zero emissions.",
         "icon": "☀️", "action": "Try cooking 1 meal per day on induction.", "color": "card-orange"},
        {"title": "Your Family × City = Real Change",
         "saving": f"Family emits {round(calc.family_co2, 1)} kg CO₂/day",
         "body": f"If your family cuts 30%, that's {round(calc.family_co2 * 0.3, 1)} kg/day saved.",
         "icon": "🌏", "action": "Share your footprint with your family today.", "color": "card-green"},
    ]

    return render_template("insights.html", calc=calc, suggestions=suggestions,
                           city=city, user=current_user)


# ══════════════════════════════════════════════════════════════════
#  ROUTE 14 — Dashboard
# ══════════════════════════════════════════════════════════════════
@app.route("/dashboard")
@login_required
def dashboard():
    calcs  = Calculation.query.filter_by(user_id=current_user.id).order_by(Calculation.calc_date).all()
    latest = calcs[-1] if calcs else None
    return render_template("dashboard.html",
                           calcs=calcs, latest=latest,
                           chart_labels=json.dumps([c.calc_date.strftime("%d %b") for c in calcs]),
                           chart_data=json.dumps([c.total_co2 for c in calcs]),
                           user=current_user)


# ══════════════════════════════════════════════════════════════════
#  ROUTE 15 — Logout
# ══════════════════════════════════════════════════════════════════
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You've been logged out.", "info")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)