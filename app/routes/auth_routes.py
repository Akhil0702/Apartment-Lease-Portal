from flask import render_template, request, redirect, url_for, session
from app import apartment
from app.models.tenants import Tenant
from app.models.apartments import Apartment 
from app.models.applications import Application
from app.models.admin import Admin
from app.models.communities import Community
from werkzeug.security import generate_password_hash, check_password_hash 
import logging
from bson import ObjectId
from .decorators import login_required
from flask import send_from_directory

from flask import flash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@apartment.route('/')
def index():
    # Only get apartments with 'available' status
    apartments = list(Apartment.collection.find({"status": "available"}))
    
    # Get all communities for displaying community names
    communities = {str(comm['_id']): comm['name'] for comm in Community.collection.find()}
    
    # Enrich apartment data with community name
    for apartment in apartments:
        community_id = apartment.get('community_id')
        if community_id and community_id in communities:
            apartment['community_name'] = communities[community_id]
        else:
            apartment['community_name'] = "Unknown Community"
    
    return render_template('index.html', session=session, apartments=apartments)


@apartment.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(apartment.config['UPLOAD_FOLDER'], filename)

import random
@apartment.route('/tenant_home')
@login_required
def tenant_home():
    if session.get("user_type") != "tenant":
        flash("Unauthorized access.", "error")
        return redirect(url_for('tenant_login'))
    
    # Only get apartments with 'available' status
    apartments = list(Apartment.collection.find({"status": "available"}))
    
    # Get all communities for displaying community names
    communities = {str(comm['_id']): comm['name'] for comm in Community.collection.find()}
    
    # Enrich apartment data with community name
    for apartment in apartments:
        community_id = apartment.get('community_id')
        if community_id and community_id in communities:
            apartment['community_name'] = communities[community_id]
        else:
            apartment['community_name'] = "Unknown Community"
    
    return render_template('tenant/home.html', session=session, apartments=apartments)


@apartment.route('/tenant_login', methods=['GET', 'POST'])
def tenant_login():
    if request.method == 'POST':
        email = request.form.get("email").strip()
        password = request.form.get("password").strip()
        
        if Tenant.exists_by_email(email):
            tenant = Tenant.get_by_email(email)
            if check_password_hash(tenant['password'], password):
                session["user_id"] = str(tenant['_id'])
                session["user_type"] = "tenant"
                next_page = session.get('next', url_for('tenant_home'))
                session.pop('next', None) 
                return redirect(next_page)
            else:
                flash('Invalid credentials', 'error')
        else:
            flash('No such tenant', 'error')

    next_page = request.args.get('next')
    if next_page:
        session['next'] = next_page  

    return render_template('tenant/login.html')





@apartment.route('/register_tenant', methods=['GET', 'POST'])
def register_tenant(): 
    try:
        if request.method == 'POST':
            email = request.form.get("email").strip()
            password = request.form.get("password").strip()
            confirm_password = request.form.get("confirm_password").strip()

            if Tenant.exists_by_email(email):
                flash("Email already registered", "error")
                return render_template('tenant/register.html')

            if password != confirm_password:
                flash("Passwords do not match", "error")
                return render_template('tenant/register.html')

            data = {
                "name": request.form.get("name").strip(),
                "email": email,
                "phone": request.form.get("phone").strip(),
                "dob": request.form.get("dob"),
                "ssn": request.form.get("ssn").strip(),
                "address": request.form.get("address").strip(),
                "city": request.form.get("city").strip(),
                "state": request.form.get("state").strip(),
                "zipcode": request.form.get("zipcode").strip(),
                "password": generate_password_hash(password)
            }

            Tenant.create(data)
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('tenant_login'))

        return render_template('tenant/register.html')
    except Exception as e:
        logger.error(f"Error during tenant registration: {str(e)}")
        flash("An error occurred during registration. Please try again.", "error")
        return render_template('tenant/register.html')


@apartment.route('/logout')
def logout():
    try:
        session.clear()  
        session.pop('tenant_id', None)
        session.pop('tenant_type', None)
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        return "Internal Server Error", 500