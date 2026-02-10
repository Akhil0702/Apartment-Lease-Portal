from flask import render_template, request, redirect, url_for, session, flash, jsonify, send_file
from app import apartment
from app.models.admin import Admin
from app.models.apartments import Apartment
from app.models.communities import Community
from app.models.tenants import Tenant 
from app.models.payments import Payment 
from app.models.applications import Application
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from app.models.managers import Manager
from bson.objectid import ObjectId 
from flask import jsonify 
import logging
from .decorators import login_required



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@apartment.route('/admin_reg', methods=['GET'])
def admin_reg():
    try:
        # Hard-coded admin data
        email = "admin@admin.com"
        user_name = "admin"
        phone = "123-456-7890"
        password = "admin"

        # Check if the admin email is already registered
        if Admin.exists_by_email(email):
            return jsonify({"message": "Admin already registered. Check DB for details."}), 200

        # Data preparation
        data = {
            "email": email,
            "user_name": user_name,
            "phone": phone,
            "password": generate_password_hash(password)
        }

        # Create admin record
        Admin.create(data)
        return jsonify({"message": "Admin registered successfully!"}), 201

    except Exception as e:
        logger.error(f"Error during admin registration: {str(e)}")
        return "Internal Server Error", 500



@apartment.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get("email").strip()
        password = request.form.get("password").strip()
        
        # Check if tenant exists in the admin database
        if Admin.exists_by_email(email):
            admin = Admin.get_by_email(email)
            if check_password_hash(admin['password'], password):
                session["user_id"] = str(admin['_id'])
                session["user_type"] = "admin"
                return redirect(url_for('admin_home'))
            else:
                return "Invalid credentials", 400
        else:
            return "No such admin", 404

    return render_template('admin/login.html')


@apartment.route('/admin_home')
@login_required
def admin_home():
    if session["user_type"] == "admin":
        # Fetch count of apartments
        apartments_count = Apartment.count() if Apartment.count() else 0

        # Fetch count of tenants
        tenants_count = Tenant.count() if Tenant.count() else 0

        # Fetch count of managers
        managers_count = Manager.count() if Manager.count() else 0

        # Fetch count of applications
        applications_count = Application.count() if Application.count() else 0
        
        # Fetch count of communities
        communities_count = Community.count() if Community.count() else 0

        # Pass the counts to the template
        return render_template(
            'admin/admin_home.html',
            apartments_count=apartments_count,
            tenants_count=tenants_count,
            managers_count=managers_count,
            applications_count=applications_count,
            communities_count=communities_count
        )
    else:
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_login'))

 
# view all tenants
@apartment.route('/admin_view_tenants', methods=['GET'])
@login_required
def admin_view_tenants():
    if session["user_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))

    # Get filter parameters
    community_id = request.args.get('community_id')
    status = request.args.get('status')
    role = request.args.get('role')
    
    # Apply filters if provided
    filters = {}
    if community_id:
        filters['community_id'] = community_id
    if status:
        filters['status'] = status
    if role:
        filters['role'] = role
    
    # Get tenants with filters
    tenants = Tenant.get_filtered(filters) if filters else Tenant.get_all()
    tenants = list(tenants)
    
    # Get all communities for the filter dropdown
    communities = Community.get_all()



    return render_template('admin/admin_view_tenants.html', 
                          tenants=tenants, 
                          communities=communities,
                          selected_community=community_id,
                          selected_status=status,
                          selected_role=role)

@apartment.route('/admin_tenant_status', methods=['POST'])
@login_required
def admin_tenant_status():
    if session["user_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))
    
    tenant_id = request.form.get('tenant_id')
    new_status = request.form.get('status')
    
    if not tenant_id or not new_status:
        flash("Missing required information.", "error")
        return redirect(url_for('admin_view_tenants'))
    
    # Update tenant status
    Tenant.update_status(tenant_id, new_status)
    flash(f"Tenant status updated to {new_status}.", "success")
    return redirect(url_for('admin_view_tenants'))

@apartment.route('/admin_tenant_history/<tenant_id>', methods=['GET'])
@login_required
def admin_tenant_history(tenant_id):
    if session["user_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))
    
    # Get tenant details
    tenant = Tenant.get_by_id(tenant_id)
    if not tenant:
        flash("Tenant not found.", "error")
        return redirect(url_for('admin_view_tenants'))
    
    # Get tenant's lease applications
    applications = Application.get_by_tenant_id(tenant_id)
    
    # Get tenant's payment records
    payments = Payment.get_by_tenant_id(tenant_id)
    
    return render_template('admin/tenant_history.html', 
                          tenant=tenant, 
                          applications=applications, 
                          payments=payments)

@apartment.route('/admin_view_payments', methods=['GET'])
@login_required
def admin_view_payments():
    if session["user_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))
    
    # Get filter parameters
    status = request.args.get('status')
    community_id = request.args.get('community_id')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Apply filters if provided
    query = {}
    if status:
        query['status'] = status
    if community_id:
        query['community_id'] = community_id
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            if 'payment_date' not in query:
                query['payment_date'] = {}
            query['payment_date']['$gte'] = from_date
        except ValueError:
            flash("Invalid date format for 'Date From'", "error")
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            # Add one day to include the end date
            to_date = to_date + timedelta(days=1)
            if 'payment_date' not in query:
                query['payment_date'] = {}
            query['payment_date']['$lt'] = to_date
        except ValueError:
            flash("Invalid date format for 'Date To'", "error")
    
    # Get payments with filters
    payments = list(Payment.collection.find(query)) if query else Payment.get_all()
    
    # Get all communities for the filter dropdown
    communities = Community.get_all()
    
    # Get tenant names for each payment
    for payment in payments:
        tenant = Tenant.get_by_id(payment.get('tenant_id', ''))
        payment['tenant_name'] = f"{tenant.get('first_name', '')} {tenant.get('last_name', '')}" if tenant else "Unknown"
    
    return render_template('admin/view_payments.html', 
                          payments=payments,
                          communities=communities,
                          selected_status=status,
                          selected_community=community_id,
                          date_from=date_from,
                          date_to=date_to)

@apartment.route('/admin_view_applications', methods=['GET', 'POST'])
@login_required
def admin_view_applications():
    if session["user_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))
    
    if request.method == 'POST':
        application_id = request.form.get('application_id')
        status = request.form.get('status')
        
        if application_id and status:
            # Update application status
            Application.update_status(application_id, status)
            flash("Application status updated successfully.", "success")
        
        return redirect(url_for('admin_view_applications'))
    
    # Get filter parameters
    status = request.args.get('status')
    community_id = request.args.get('community_id')
    
    # Apply filters if provided
    query = {}
    if status:
        query['status'] = status
    if community_id:
        query['community_id'] = community_id
    
    # Get applications with filters
    applications = list(Application.collection.find(query)) if query else Application.get_all()
    
    # Get all communities for the filter dropdown
    communities = Community.get_all()

    # caluclate duration based on start and ed and send in applications
    for application in applications:
        application['duration'] = (application['end_date'] - application['move_in_date']).days
    
    return render_template('admin/admin_view_applications.html', 
                          applications=applications,
                          communities=communities,
                          selected_status=status,
                          selected_community=community_id)

@apartment.route('/admin_view_managers', methods=['GET'])
@login_required
def admin_view_managers():
    if session["user_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))
    
    # Get filter parameters
    status = request.args.get('status')
    community_id = request.args.get('community_id')
    
    # Apply filters if provided
    query = {}
    if status:
        query['status'] = status
    if community_id:
        query['community_id'] = community_id
    
    # Get managers with filters
    managers = list(Manager.collection.find(query)) if query else list(Manager.get_all())
    print("Managers:", managers)
    
    # Get all communities for the filter dropdown and for displaying community names
    communities = Community.get_all()
    community_names = {str(comm['_id']): comm['name'] for comm in communities}
    print(community_names)
    
    # Add community name to each manager
    for manager in managers:
        if 'community_id' in manager and manager['community_id']:
            manager['community_name'] = community_names.get(str(manager['community_id']), 'Not Assigned')
        else:
            manager['community_name'] = 'Not Assigned'
    
    print("Final managers:", managers)
    return render_template('admin/admin_view_managers.html', 
                          managers=managers,
                          communities=communities,
                          selected_status=status,
                          selected_community=community_id)

@apartment.route('/admin_manager_status', methods=['POST'])
@login_required
def admin_manager_status():
    if session["user_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))
    
    manager_id = request.form.get('manager_id')
    new_status = request.form.get('status')
    
    if not manager_id or not new_status:
        flash("Missing required information.", "error")
        return redirect(url_for('admin_view_managers'))
    
    # Update manager status
    Manager.update_status(manager_id, new_status)
    flash(f"Manager status updated to {new_status}.", "success")
    return redirect(url_for('admin_view_managers'))

@apartment.route('/admin_view_apartments')
@login_required
def admin_view_apartments():
    if session.get("user_type") != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_login'))
    
    # Get all communities
    communities = list(Community.collection.find())
    
    # For each community, get its apartments
    for community in communities:
        community['apartments'] = list(Apartment.collection.find({"community_id": str(community['_id'])}))
    
    return render_template('admin/admin_view_apartments.html', communities=communities)
