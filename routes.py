from flask import Blueprint, render_template, redirect, session, url_for, request, flash
from flask_login import login_required, current_user
from db import db
from models import Contact
from ai_client import generate_email_text
from email_sender import send_message_via_gmail
import csv, io
from google_auth_oauthlib.flow import Flow
from config import Config
from google.oauth2.credentials import Credentials
from datetime import datetime

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
CLIENT_CONFIG = {
    "web": {
        "client_id": Config.GMAIL_CLIENT_ID,
        "client_secret": Config.GMAIL_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [Config.GMAIL_REDIRECT_URI]
    }
}

routes = Blueprint('routes', __name__)

@routes.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')

@routes.route('/contacts')
@login_required
def contacts():
    contacts = Contact.query.filter_by(owner_id=current_user.id).all()
    return render_template('contacts.html', contacts=contacts)

@routes.route('/contacts/add', methods=['GET','POST'])
@login_required
def add_contact():
    if request.method=='POST':
        c = Contact(
            owner_id=current_user.id,
            name=request.form['name'],
            email=request.form['email'],
            company=request.form.get('company'),
            notes=request.form.get('notes')
        )
        db.session.add(c); db.session.commit()
        return redirect(url_for('routes.contacts'))
    return render_template('add_contact.html')


@routes.route('/contacts/<int:contact_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_contact(contact_id):
    contact = Contact.query.filter_by(id=contact_id, owner_id=current_user.id).first_or_404()

    if request.method == 'POST':
        contact.name = request.form['name']
        contact.email = request.form['email']
        contact.company = request.form.get('company')
        contact.notes = request.form.get('notes')
        db.session.commit()
        flash('Контакт успешно обновлен', 'success')
        return redirect(url_for('routes.contacts'))

    return render_template('edit_contact.html', contact=contact)

@routes.route('/contacts/upload', methods=['GET','POST'])
@login_required
def upload_contacts():
    if request.method=='POST':
        file = request.files['file']
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        reader = csv.DictReader(stream)
        for row in reader:
            c = Contact(
                owner_id=current_user.id,
                name=row.get('name'),
                email=row.get('email'),
                company=row.get('company'),
                notes=row.get('notes')
            )
            db.session.add(c)
        db.session.commit()
        return redirect(url_for('routes.contacts'))
    return render_template('upload_contacts.html')

@routes.route('/generate/<int:contact_id>', methods=['GET','POST'])
@login_required
def generate_email(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    if request.method=='POST':
        extra = request.form.get('extra_prompt','')
        # Генерируем текст
        text = generate_email_text(current_user.name, current_user.company_name, current_user.company_info, contact, extra)
        # Сохраняем во временном хранилище
        session[f'email_{contact.id}'] = text
        return redirect(url_for('routes.edit_email', contact_id=contact.id))
    return render_template('generate_email.html', contact=contact)

@routes.route('/edit/<int:contact_id>', methods=['GET','POST'])
@login_required
def edit_email(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    key = f'email_{contact.id}'
    draft = session.pop(key, '')
    if request.method=='POST':
        # Из формы: либо отправляем, либо редактируем
        if 'send' in request.form:
            body = request.form['body']
            send_message_via_gmail(
                user=current_user,
                to_email=contact.email,
                subject=f"Напоминание от {current_user.company_name}",
                body=body
            )
            session.pop(key, None)
            flash('Письмо отправлено!')
            return redirect(url_for('routes.contacts'))
        else:
            # Сохраняем правки в сессии
            session[key] = request.form['body']
            flash('Черновик сохранён')
            return redirect(url_for('routes.edit_email', contact_id=contact.id))
    return render_template('edit_email.html', contact=contact, body=draft)

@routes.route('/settings', methods=['GET','POST'])
@login_required
def settings():
    if request.method=='POST':
        current_user.name = request.form['name']
        current_user.company_name = request.form['company_name']
        current_user.company_info = request.form['company_info']
        # TODO: OAuth2 flow to obtain gmail tokens
        db.session.commit()
        flash('Настройки сохранены')
    return render_template('settings.html')

@routes.route('/oauth_start')
@login_required
def oauth_start():
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=Config.GMAIL_REDIRECT_URI
    )
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    session['oauth_state'] = state
    print(session)
    print(state)
    return redirect(auth_url)

@routes.route('/oauth2callback')
@login_required
def oauth2callback():
    #print(session)
    # = session.get('oauth_state', None)
    state = session.pop('oauth_state', None)
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        state=state,
        redirect_uri=Config.GMAIL_REDIRECT_URI
    )
    flow.fetch_token(authorization_response=request.url)

    creds: Credentials = flow.credentials
    # сохраняем токены в БД

    #creds = flow.credentials
    # Сохраняем в модель User
    user = current_user
    user.gmail_token = creds.token
    user.gmail_refresh_token = creds.refresh_token
    user.gmail_token_expiry = creds.expiry  # datetime
    db.session.commit()

    flash('Gmail успешно подключён! Теперь можно отправлять письма.')
    return redirect(url_for('routes.settings'))