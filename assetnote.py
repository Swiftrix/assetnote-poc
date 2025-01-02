from flask import Flask, render_template, request, jsonify, redirect
from flask_seasurf import SeaSurf
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required
from urllib.parse import urljoin
import config

app = Flask(__name__)
app.config.from_object('config')
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqldb://root:testing@localhost:3389/assetnote'  # Use PyMySQL if necessary
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
csrf = SeaSurf(app)

roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'))
)

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)
    confirmed_at = db.Column(db.DateTime)
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))

class Domain(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(255), unique=True)
    first_scan = db.Column(db.String(255))
    push_notification_key = db.Column(db.String(255))
    type = db.Column(db.String(255))

class SentNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    new_domain = db.Column(db.String(255))
    push_notification_key = db.Column(db.String(255))
    time_sent = db.Column(db.DateTime)

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

@app.before_first_request
def create_user():
    db.create_all()
    existing_user = User.query.filter_by(email='shubs').first()
    if existing_user:
        db.session.delete(existing_user)
        db.session.commit()
    user_datastore.create_user(email='shubs', password='testing')
    db.session.commit()

@app.route("/")
@login_required
def index():
    sent_notifications = SentNotification.query.all()
    return render_template("index.html", sent=sent_notifications)

@app.route("/manage")
@login_required
def manage():
    all_domains = Domain.query.all()
    return render_template("manage.html", domains_monitored=all_domains)

@app.route("/api/get_domains")
@login_required
def get_domain_data():
    all_domains = Domain.query.all()
    return jsonify(data=[d.__dict__ for d in all_domains])

@app.route("/api/add_domain", methods=["POST"])
@login_required
def add_domain_api():
    domain = request.form.get("domain")
    pushover_key = request.form.get("pushover_key")
    try:
        new_domain = Domain(domain=domain, first_scan="Y", push_notification_key=pushover_key)
        db.session.add(new_domain)
        db.session.commit()
        return jsonify(result="success")
    except Exception as e:
        db.session.rollback()
        return jsonify(result=str(e)), 400

@app.route("/api/delete_domain", methods=["POST"])
@login_required
def delete_domain_api():
    d_id = request.form.get("d_id")
    try:
        domain = Domain.query.get(d_id)
        if not domain:
            return jsonify(result="Domain not found"), 404
        db.session.delete(domain)
        db.session.commit()
        return jsonify(result="success")
    except Exception as e:
        db.session.rollback()
        return jsonify(result=str(e)), 400

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True)
