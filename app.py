from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
import logging

# ---------------- APP CONFIG ----------------
app = Flask(__name__)
app.secret_key = "swapsecretkey"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///swapyourskills.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ---------------- MAIL CONFIG ----------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'swapyourskillsteam@gmail.com'
app.config['MAIL_PASSWORD'] = 'vfcwgsntakdtxblg'  # Use Gmail App Password
mail = Mail(app)

# Enable debug logging for Flask-Mail
logging.basicConfig(level=logging.DEBUG)

db = SQLAlchemy(app)

# ---------------- MODELS ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    dob = db.Column(db.String(20))
    gender = db.Column(db.String(20))
    age = db.Column(db.Integer)
    occupation = db.Column(db.String(100))

class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    skill_name = db.Column(db.String(100))
    type = db.Column(db.String(20))  # offer / learn

class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    skill_name = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')
    rating_your = db.Column(db.Integer)
    rating_partner = db.Column(db.Integer)

class ClearedMatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    partner_id = db.Column(db.Integer)
    skill_name = db.Column(db.String(100))
    viewed = db.Column(db.Boolean, default=False)

# ---------------- HELPERS ----------------
def current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

# ---------------- ROUTES ----------------
@app.route('/')
def index():
    return render_template("index.html", user=current_user())

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(email=email).first():
            flash("Email already exists!", "danger")
            return redirect(url_for('signup'))
        db.session.add(User(username=username, email=email, password=password))
        db.session.commit()
        flash("Signup successful! Please login.", "success")
        return redirect(url_for('login'))
    return render_template("signup.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        flash("Invalid credentials!", "danger")
        return redirect(url_for('login'))
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Logged out!", "success")
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user = current_user()
    if not user:
        flash("Login first!", "danger")
        return redirect(url_for('login'))
    if request.method == 'POST':
        user.dob = request.form['dob']
        user.gender = request.form['gender']
        user.age = request.form['age']
        user.occupation = request.form['occupation']
        db.session.commit()
        flash("Profile updated!", "success")
        return redirect(url_for('profile'))
    return render_template("profile.html", user=user, current_date=date.today().isoformat())

@app.route('/dashboard')
def dashboard():
    user = current_user()
    if not user:
        flash("Login first!", "danger")
        return redirect(url_for('login'))
    cleared_set = set((c.partner_id, c.skill_name) for c in ClearedMatch.query.filter_by(user_id=user.id, viewed=True).all())
    my_offers = Skill.query.filter_by(user_id=user.id, type='offer').all()
    my_learns = Skill.query.filter_by(user_id=user.id, type='learn').all()
    notif_count = Request.query.filter_by(receiver_id=user.id, status='pending').count()
    notif_count += Request.query.filter_by(sender_id=user.id).filter(Request.status.in_(['accepted', 'declined'])).count()
    # Count new matches
    for offer in my_offers:
        learners = Skill.query.filter_by(skill_name=offer.skill_name, type='learn').all()
        for l in learners:
            if l.user_id != user.id and (l.user_id, offer.skill_name) not in cleared_set:
                existing = Request.query.filter_by(sender_id=user.id, receiver_id=l.user_id, skill_name=offer.skill_name).first()
                if not existing:
                    notif_count += 1
    for learn in my_learns:
        offers = Skill.query.filter_by(skill_name=learn.skill_name, type='offer').all()
        for o in offers:
            if o.user_id != user.id and (o.user_id, learn.skill_name) not in cleared_set:
                existing = Request.query.filter_by(sender_id=user.id, receiver_id=o.user_id, skill_name=learn.skill_name).first()
                if not existing:
                    notif_count += 1
    return render_template("dashboard.html", user=user, notif_count=notif_count)

# ---------------- ADD / DELETE SKILLS ----------------
@app.route('/add_skills', methods=['GET', 'POST'])
def add_skills():
    user = current_user()
    if not user:
        flash("Login first!", "danger")
        return redirect(url_for('login'))
    if request.method == 'POST':
        skill_name = request.form.get('offer_skill') or request.form.get('learn_skill')
        skill_type = 'offer' if 'submit_offer' in request.form else 'learn'
        db.session.add(Skill(user_id=user.id, skill_name=skill_name, type=skill_type))
        db.session.commit()
        flash(f"{skill_type.title()} skill added!", "success")
    offer_skills = Skill.query.filter_by(user_id=user.id, type='offer').all()
    learn_skills = Skill.query.filter_by(user_id=user.id, type='learn').all()
    return render_template("add_skills.html", user=user, offer_skills=offer_skills, learn_skills=learn_skills)

@app.route('/delete_skill/<int:skill_id>')
def delete_skill(skill_id):
    user = current_user()
    if not user:
        flash("Login first!", "danger")
        return redirect(url_for('login'))
    skill = Skill.query.get(skill_id)
    if skill and skill.user_id == user.id:
        db.session.delete(skill)
        db.session.commit()
        flash(f"Skill '{skill.skill_name}' removed!", "success")
    else:
        flash("You cannot delete this skill!", "danger")
    return redirect(url_for('add_skills'))

# ---------------- NOTIFICATIONS ----------------
@app.route('/notifications')
def notifications():
    user = current_user()
    if not user:
        flash("Login first!", "danger")
        return redirect(url_for('login'))
    notifications = []
    cleared_set = set((c.partner_id, c.skill_name) for c in ClearedMatch.query.filter_by(user_id=user.id).all())
    my_offers = Skill.query.filter_by(user_id=user.id, type='offer').all()
    my_learns = Skill.query.filter_by(user_id=user.id, type='learn').all()
    # Incoming Requests
    for r in Request.query.filter_by(receiver_id=user.id).all():
        sender = User.query.get(r.sender_id)
        notifications.append({
            "partner_id": sender.id,
            "partner_name": sender.username,
            "skill_offered": r.skill_name,
            "skill_wants_to_learn": ', '.join([s.skill_name for s in Skill.query.filter_by(user_id=user.id, type='learn')]) or "-",
            "request_status": r.status
        })
    # Sent Requests
    for r in Request.query.filter_by(sender_id=user.id).filter(Request.status.in_(['accepted','declined'])).all():
        receiver = User.query.get(r.receiver_id)
        notifications.append({
            "partner_id": receiver.id,
            "partner_name": receiver.username,
            "skill_offered": r.skill_name,
            "skill_wants_to_learn": ', '.join([s.skill_name for s in Skill.query.filter_by(user_id=receiver.id, type='learn')]) or "-",
            "request_status": r.status
        })
    # New Matches
    for offer in my_offers:
        learners = Skill.query.filter_by(skill_name=offer.skill_name, type='learn').all()
        for l in learners:
            if l.user_id != user.id and (l.user_id, offer.skill_name) not in cleared_set:
                existing = Request.query.filter_by(sender_id=user.id, receiver_id=l.user_id, skill_name=offer.skill_name).first()
                if not existing:
                    partner = User.query.get(l.user_id)
                    notifications.append({
                        "partner_id": partner.id,
                        "partner_name": partner.username,
                        "skill_offered": offer.skill_name,
                        "skill_wants_to_learn": ', '.join([s.skill_name for s in Skill.query.filter_by(user_id=partner.id, type='learn')]) or "-",
                        "request_status": None
                    })
    for learn in my_learns:
        offers = Skill.query.filter_by(skill_name=learn.skill_name, type='offer').all()
        for o in offers:
            if o.user_id != user.id and (o.user_id, learn.skill_name) not in cleared_set:
                existing = Request.query.filter_by(sender_id=user.id, receiver_id=o.user_id, skill_name=learn.skill_name).first()
                if not existing:
                    partner = User.query.get(o.user_id)
                    notifications.append({
                        "partner_id": partner.id,
                        "partner_name": partner.username,
                        "skill_offered": ', '.join([s.skill_name for s in Skill.query.filter_by(user_id=partner.id, type='offer')]) or "-",
                        "skill_wants_to_learn": learn.skill_name,
                        "request_status": None
                    })
    return render_template("notifications.html", user=user, notifications=notifications)

@app.route('/clear_notification/<int:partner_id>/<skill>')
def clear_notification(partner_id, skill):
    user = current_user()
    if not user:
        flash("Login first!", "danger")
        return redirect(url_for('login'))
    cleared = ClearedMatch.query.filter_by(user_id=user.id, partner_id=partner_id, skill_name=skill).first()
    if not cleared:
        db.session.add(ClearedMatch(user_id=user.id, partner_id=partner_id, skill_name=skill, viewed=True))
        db.session.commit()
        flash("Notification cleared!", "success")
    return redirect(url_for('notifications'))

# ---------------- REQUESTS ----------------
@app.route('/send_request/<int:receiver_id>/<skill>')
def send_request(receiver_id, skill):
    user = current_user()
    if not user:
        flash("Login first!", "danger")
        return redirect(url_for('login'))
    existing = Request.query.filter_by(sender_id=user.id, receiver_id=receiver_id, skill_name=skill).first()
    if not existing:
        db.session.add(Request(sender_id=user.id, receiver_id=receiver_id, skill_name=skill))
        db.session.commit()
        flash("Request sent!", "success")
    else:
        flash("Request already exists!", "warning")
    return redirect(url_for('notifications'))

@app.route('/requests')
def requests_view():
    user = current_user()
    if not user:
        flash("Login first!", "danger")
        return redirect(url_for('login'))
    data = []
    for r in Request.query.filter_by(receiver_id=user.id).all():
        sender = User.query.get(r.sender_id)
        sender_offers = ', '.join([s.skill_name for s in Skill.query.filter_by(user_id=sender.id, type='offer')])
        sender_learns = ', '.join([s.skill_name for s in Skill.query.filter_by(user_id=sender.id, type='learn')])
        data.append({
            "id": r.id,
            "sender_name": sender.username,
            "sender_offers": sender_offers,
            "sender_learns": sender_learns,
            "skill_name": r.skill_name,
            "status": r.status,
            "sender_email": sender.email
        })
    return render_template("requests.html", user=user, requests=data)

@app.route('/accept_request/<int:req_id>')
def accept_request(req_id):
    user = current_user()
    r = Request.query.get(req_id)
    if r and r.receiver_id == user.id:
        r.status = 'accepted'
        db.session.commit()
        sender = User.query.get(r.sender_id)
        try:
            msg = Message(
                'Your Skill Request Accepted',
                sender=app.config['MAIL_USERNAME'],
                recipients=[sender.email]
            )
            msg.body = f"""Hi {sender.username},

Your request for skill '{r.skill_name}' has been accepted by {user.username}.

Partner Details:
Name       : {user.username}
Age        : {user.age if user.age else "Not provided"}
Occupation : {user.occupation if user.occupation else "Not provided"}
Email      : {user.email}

Happy Learning!
SwapYourSkills Team
"""
            mail.send(msg)
            flash("Request accepted and email sent!", "success")
        except Exception as e:
            flash(f"Request accepted but email failed: {e}", "warning")
    return redirect(url_for('requests_view'))

@app.route('/decline_request/<int:req_id>')
def decline_request(req_id):
    user = current_user()
    r = Request.query.get(req_id)
    if r and r.receiver_id == user.id:
        r.status = 'declined'
        db.session.commit()
        sender = User.query.get(r.sender_id)
        try:
            msg = Message(
                'Your Skill Request Declined',
                sender=app.config['MAIL_USERNAME'],
                recipients=[sender.email]
            )
            msg.body = f"""Hi {sender.username},

Your request for skill '{r.skill_name}' has been declined.

Don't worry! You can explore and request skills from other users.
SwapYourSkills Team
"""
            mail.send(msg)
            flash("Request declined and email sent!", "success")
        except Exception as e:
            flash(f"Request declined but email failed: {e}", "warning")
    return redirect(url_for('requests_view'))

# ---------------- RATINGS ----------------
@app.route('/ratings')
def ratings():
    user = current_user()
    if not user:
        flash("Login first!", "danger")
        return redirect(url_for('login'))
    rated_requests = Request.query.filter(
        ((Request.sender_id==user.id)|(Request.receiver_id==user.id)) & 
        (Request.status=='accepted')
    ).all()
    data = []
    for r in rated_requests:
        partner_id = r.receiver_id if r.sender_id == user.id else r.sender_id
        partner = User.query.get(partner_id)
        data.append({
            "id": r.id,
            "partner_name": partner.username,
            "partner_email": partner.email,
            "partner_age": partner.age,
            "partner_occupation": partner.occupation,
            "skill_name": r.skill_name,
            "rating_your": r.rating_your,
            "rating_partner": r.rating_partner
        })
    return render_template("ratings.html", user=user, matches=data)

@app.route('/rate/<int:req_id>', methods=['GET', 'POST'])
def rate(req_id):
    user = current_user()
    if not user:
        flash("Login first!", "danger")
        return redirect(url_for('login'))
    request_obj = Request.query.get(req_id)
    if not request_obj or request_obj.status != 'accepted':
        flash("Invalid request!", "danger")
        return redirect(url_for('ratings'))
    partner_id = request_obj.receiver_id if request_obj.sender_id == user.id else request_obj.sender_id
    partner = User.query.get(partner_id)
    already_rated = (request_obj.rating_your is not None) if request_obj.sender_id == user.id else (request_obj.rating_partner is not None)
    if request.method == 'POST':
        rating = int(request.form['rating'])
        if request_obj.sender_id == user.id:
            request_obj.rating_your = rating
        else:
            request_obj.rating_partner = rating
        db.session.commit()
        flash("Rating submitted successfully!", "success")
        return redirect(url_for('ratings'))
    return render_template("rate_form.html", user=user, partner=partner, request=request_obj, already_rated=already_rated)

# ---------------- TEST EMAIL ----------------
@app.route('/test_email')
def test_email():
    try:
        msg = Message(
            "Test Email from SwapYourSkills",
            sender=app.config['MAIL_USERNAME'],
            recipients=["swapyourskillsteam@gmail.com"]  # Replace with your email
        )
        msg.body = "This is a test email from SwapYourSkills app."
        mail.send(msg)
        return "Test email sent successfully!"
    except Exception as e:
        return f"Email failed: {str(e)}"

# ---------------- DB CREATE ----------------
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
