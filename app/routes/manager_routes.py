from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app import apartment
from app.models.managers import Manager
from app.models.apartments import Apartment
from app.models.applications import Application
from app.models.tenants import Tenant
from app.models.communities import Community
from app.models.lease_agreements import LeaseAgreement
from app.models.payments import Payment
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from .decorators import login_required
import logging
from bson.objectid import ObjectId 


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



@apartment.route('/manager_register', methods=['GET', 'POST'])
def manager_register():
    if request.method == 'POST':
        email = request.form.get("email").strip()
        password = request.form.get("password").strip()
        user_name = request.form.get("user_name").strip()
        phone = request.form.get("phone").strip()
        first_name = request.form.get("first_name").strip()
        last_name = request.form.get("last_name").strip()
        dob = request.form.get("dob").strip()
        ssn = request.form.get("ssn").strip()
        address = request.form.get("address").strip()
        city = request.form.get("city").strip()
        state = request.form.get("state").strip()
        zipcode = request.form.get("zipcode").strip()

        if Manager.exists_by_email(email):
            flash("Email already registered!", "error")
            return redirect(url_for('manager_register'))
            
        if Manager.exists_by_username(user_name):
            flash("Username already taken!", "error")
            return redirect(url_for('manager_register'))

        # Hash the password here - don't pass plain text to the model
        hashed_password = generate_password_hash(password)
        
        data = {
            "email": email,
            "user_name": user_name,
            "phone": phone,
            "password": hashed_password,  # Use the hashed password
            "first_name": first_name,
            "last_name": last_name,
            "dob": dob,
            "ssn": ssn,
            "address": address,
            "city": city,
            "state": state,
            "zipcode": zipcode,
            "created_at": datetime.utcnow(),
            "status": "pending"  # Set status to pending until admin assigns a community
        }

        try:
            Manager.create(data)
            flash("Manager registered successfully! Please wait for admin approval and community assignment.", "success")
            return redirect(url_for('manager_login'))
        except ValueError as e:
            logger.error(f"Error during manager registration: {str(e)}")
            flash(f"Registration error: {str(e)}", "error")
            return redirect(url_for('manager_register'))
        except Exception as e:
            logger.error(f"Error during manager registration: {str(e)}")
            flash("Internal Server Error", "error")
            return redirect(url_for('manager_register'))

    return render_template('manager/register.html')


@apartment.route('/manager_login', methods=['GET', 'POST'])
def manager_login():
    if request.method == 'POST':
        identifier = request.form.get("identifier").strip()  # This can be either email or username
        password = request.form.get("password").strip()

        logger.info(f"Login attempt with identifier: {identifier}")

        # Try to find manager by email first
        manager = Manager.get_by_email(identifier)
        
        # If not found by email, try by username
        if not manager:
            logger.info("Not found by email, trying username")
            manager = Manager.get_by_username(identifier)
        
        if manager:
            logger.info(f"Manager found: {manager.get('user_name')}, Status: {manager.get('status')}, Community: {manager.get('community_id', 'None')}")
            
            # Add more detailed password debugging
            stored_password_hash = manager['password']
            logger.info(f"Stored password hash: {stored_password_hash[:20]}...")
            password_check_result = check_password_hash(stored_password_hash, password)
            logger.info(f"Password check result: {password_check_result}")
            
            if password_check_result:
                logger.info("Password check passed")
                
                # First check if community is assigned
                if not manager.get('community_id'):
                    logger.info("No community assigned")
                    flash("Your account doesn't have a community assigned yet. Please wait for an administrator to assign you to a community.", "warning")
                    return redirect(url_for('manager_login'))
                
                # Then check if account is pending
                if manager.get('status') == 'pending':
                    logger.info("Account is pending")
                    flash("Your account is pending approval. Please wait for an administrator to approve your account.", "warning")
                    return redirect(url_for('manager_login'))
                
                # Check if manager account is inactive
                if manager.get('status') == 'inactive':
                    logger.info("Account is inactive")
                    flash("Your account has been deactivated. Please contact an administrator.", "error")
                    return redirect(url_for('manager_login'))
                
                # All checks passed, proceed with login
                logger.info("All checks passed, logging in")
                session["user_id"] = str(manager['_id'])
                session["user_type"] = "manager"
                session["community_id"] = manager['community_id']
                
                flash("Login successful", "success")
                return redirect(url_for('manager_home'))
            else:
                logger.info("Password check failed")
                flash("Invalid credentials", "error")
                return redirect(url_for('manager_login'))
        else:
            logger.info("No manager found with that identifier")
            flash("No account found with that username or email", "error")
            return redirect(url_for('manager_login'))

    return render_template('manager/login.html')

@apartment.route('/manager_home')
def manager_home():
    # get manager details
    manager = Manager.get_by_id(session["user_id"])
    # set community id in session  if exists a value for community_id
    if 'community_id' in manager and manager['community_id']:
        session["community_id"] = manager['community_id']
    
    if session.get("user_id") and session.get("user_type") == "manager":
        return render_template('manager/home.html', manager=manager, community_id=session.get("community_id"))
    else:
        flash("Unauthorized access.", "error")
        return redirect(url_for('manager_login'))



@apartment.route('/manager_logout')
def manager_logout():
    session.pop('user_id', None)
    session.pop('user_type', None)
    session.pop('community_id', None)
    flash("Logged out successfully!", "success")
    return redirect(url_for('manager_login'))

@apartment.route('/manager_delete_apartment', methods=['POST'])
def manager_delete_apartment():
    if session.get("user_type") != "manager" or not session.get("community_id"):
        flash("Unauthorized access or no community assigned.", "error")
        return redirect(url_for('manager_home'))
    
    community_id = session.get("community_id")
    apartment_id = request.form.get('apartment_id')
    
    if not apartment_id:
        flash("No apartment specified.", "error")
        return redirect(url_for('manager_view_apartments'))
    
    apartment = Apartment.get_by_id(apartment_id)
    
    # Verify the apartment belongs to the manager's community
    if not apartment or apartment.get('community_id') != community_id:
        flash("Apartment not found or not in your community.", "error")
        return redirect(url_for('manager_view_apartments'))
    
    # Delete the apartment
    Apartment.delete(apartment_id)
    flash("Apartment deleted successfully!", "success")
    return redirect(url_for('manager_view_apartments'))


# Application Management Routes for Managers
@apartment.route('/manager_view_applications')
def manager_view_applications():
    if session.get("user_type") != "manager" or not session.get("community_id"):
        flash("Unauthorized access or no community assigned.", "error")
        return redirect(url_for('manager_home'))
    
    community_id = session.get("community_id")
    
    # Get all apartments in this community
    apartments = list(Apartment.collection.find({"community_id": community_id}))
    apartment_ids = [str(apt['_id']) for apt in apartments]
    
    # Get all applications for these apartments
    applications = []
    for apt_id in apartment_ids:
        apt_applications = list(Application.collection.find({"apartment_id": apt_id}))
        applications.extend(apt_applications)
    
    # Get tenant and apartment details for each application
    for app in applications:
        app['tenant'] = Tenant.get_by_id(app.get('tenant_id'))
        app['apartment'] = Apartment.get_by_id(app.get('apartment_id'))
    
    return render_template('manager/manager_view_applications.html', 
                          applications=applications)

@apartment.route('/manager_application_details/<application_id>')
def manager_application_details(application_id):
    if session.get("user_type") != "manager" or not session.get("community_id"):
        flash("Unauthorized access or no community assigned.", "error")
        return redirect(url_for('manager_home'))
    
    community_id = session.get("community_id")
    application = Application.get_by_id(application_id)
    
    if not application:
        flash("Application not found.", "error")
        return redirect(url_for('manager_view_applications'))
    
    # Get apartment and verify it belongs to this community
    apartment = Apartment.get_by_id(application.get('apartment_id'))
    if not apartment or apartment.get('community_id') != community_id:
        flash("Application is not for an apartment in your community.", "error")
        return redirect(url_for('manager_view_applications'))
    
    # Get tenant details
    tenant = Tenant.get_by_id(application.get('tenant_id'))
    
    return render_template('manager/manager_application_details.html',
                          application=application,
                          apartment=apartment,
                          tenant=tenant)

@apartment.route('/manager_update_application_status/<application_id>', methods=['POST'])
def manager_update_application_status(application_id):
    if session.get("user_type") != "manager":
        flash("Unauthorized access.", "error")
        return redirect(url_for('manager_home'))
    
    # Get application
    application = Application.find_one({'_id': ObjectId(application_id)})
    
    if not application:
        flash("Application not found.", "error")
        return redirect(url_for('manager_view_applications'))
    
    # Get apartment details
    apartment = Apartment.find_one({'_id': ObjectId(application['apartment_id'])})
    if not apartment:
        flash("Apartment not found.", "error")
        return redirect(url_for('manager_view_applications'))
    
    # Check if application fee has been paid
    application_fee_payment = Payment.find_one({
        'application_id': application_id,
        'tenant_id': application['tenant_id'],
        'payment_type': 'application_fee'
    })
    
    if not application_fee_payment or application_fee_payment.get('status') != 'completed':
        flash("Cannot update application status. Application fee has not been paid.", "error")
        return redirect(url_for('manager_application_details', application_id=application_id))
    
    status = request.form.get('status')
    if status not in ['approved', 'rejected']:
        flash("Invalid status.", "error")
        return redirect(url_for('manager_application_details', application_id=application_id))
    
    # Update application status
    Application.update_status(application_id, status)
    
    if status == 'approved':
        # Security deposit equals one month's rent
        security_deposit = apartment['rent']
        
        # Total initial payment (first month's rent + security deposit)
        total_amount = apartment['rent'] + security_deposit
        
        # Create a payment record for the initial payment (first month + security deposit)
        payment_data = {
            'payment_method': application.get('payment_method', 'credit_card'),
            'application_id': application_id,
            'tenant_id': application['tenant_id'],
            'apartment_id': str(application['apartment_id']),
            'amount': total_amount,
            'security_deposit': security_deposit,
            'monthly_rent': apartment['rent'],
            'payment_type': 'initial_payment',
            'payment_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'status': 'pending'  # Tenant will need to complete this payment
        }
        
        # Save the payment record
        Payment.create(payment_data)
        
        # Update application with approval details
        approval_data = {
            'decision_date': datetime.now(),
            'reviewed_by': session.get("user_id"),
            'reviewer_name': session.get("user_name", "Manager")
        }
        Application.update(application_id, approval_data)
        
        flash("Application approved. Payment request sent to tenant. Lease agreement will be created after payment is completed.", "success")
    else:
        rejection_reason = request.form.get('rejection_reason', '')
        
        # Update application with rejection details
        rejection_data = {
            'decision_date': datetime.now(),
            'reviewed_by': session.get("user_id"),
            'reviewer_name': session.get("user_name", "Manager"),
            'rejection_reason': rejection_reason
        }
        Application.update(application_id, rejection_data)
        
        flash("Application rejected.", "success")
    
    return redirect(url_for('manager_view_applications'))

@apartment.route('/manager_lease_agreement/<lease_id>')
def manager_lease_agreement(lease_id):
    if session.get("user_type") != "manager" or not session.get("community_id"):
        flash("Unauthorized access or no community assigned.", "error")
        return redirect(url_for('manager_home'))
    
    lease = LeaseAgreement.get_by_id(lease_id)
    if not lease:
        flash("Lease agreement not found.", "error")
        return redirect(url_for('manager_view_applications'))
    
    tenant = Tenant.get_by_id(lease.get('tenant_id'))
    apartment = Apartment.get_by_id(lease.get('apartment_id'))
    
    return render_template('manager/lease_agreement.html',
                         lease=lease,
                         tenant=tenant,
                         apartment=apartment)

@apartment.route('/manager_complete_lease/<lease_id>', methods=['POST'])
def manager_complete_lease(lease_id):
    if session.get("user_type") != "manager" or not session.get("community_id"):
        flash("Unauthorized access or no community assigned.", "error")
        return redirect(url_for('manager_home'))
    
    lease = LeaseAgreement.get_by_id(lease_id)
    if not lease:
        flash("Lease agreement not found.", "error")
        return redirect(url_for('manager_view_applications'))
    
    # Update lease status to completed
    LeaseAgreement.update_status(lease_id, 'completed')
    
    flash("Lease agreement completed. Please process the payment.", "success")
    return redirect(url_for('manager_lease_agreement', lease_id=lease_id))

@apartment.route('/manager_process_payment/<lease_id>', methods=['POST'])
def manager_process_payment(lease_id):
    if session.get("user_type") != "manager" or not session.get("community_id"):
        flash("Unauthorized access or no community assigned.", "error")
        return redirect(url_for('manager_home'))
    
    lease = LeaseAgreement.get_by_id(lease_id)
    if not lease:
        flash("Lease agreement not found.", "error")
        return redirect(url_for('manager_view_applications'))
    
    if lease.get('status') != 'completed':
        flash("Please complete the lease agreement before processing payment.", "error")
        return redirect(url_for('manager_lease_agreement', lease_id=lease_id))
    
    payment_method = request.form.get('payment_method')
    transaction_id = request.form.get('transaction_id')
    
    # Calculate total amount (security deposit + first month's rent)
    total_amount = lease.get('security_deposit') + lease.get('monthly_rent')
    
    # Create payment record
    payment_result = Payment.create_lease_payment(
        lease_id=lease_id,
        tenant_id=lease.get('tenant_id'),
        apartment_id=lease.get('apartment_id'),
        amount=total_amount,
        payment_method=payment_method,
        transaction_id=transaction_id
    )
    
    # Update lease status to active_paid
    LeaseAgreement.update_status(lease_id, 'active_paid')
    
    # Update application status to completed
    db = get_db()
    db.applications.update_one(
        {'_id': ObjectId(lease.get('application_id'))},
        {'$set': {'status': 'completed'}}
    )
    
    # Add tenant to current tenants collection
    tenant_data = db.tenants.find_one({'_id': ObjectId(lease.get('tenant_id'))})
    if tenant_data:
        current_tenant = {
            'tenant_id': lease.get('tenant_id'),
            'apartment_id': lease.get('apartment_id'),
            'lease_id': lease_id,
            'name': tenant_data.get('name'),
            'email': tenant_data.get('email'),
            'phone': tenant_data.get('phone'),
            'move_in_date': lease.get('start_date'),
            'lease_end_date': lease.get('end_date'),
            'monthly_rent': lease.get('monthly_rent'),
            'status': 'active'
        }
        db.current_tenants.insert_one(current_tenant)
    
    # Update payment status for the application
    Payment.update_status(lease.get('tenant_id'), lease.get('application_id'), 'paid')
    
    flash("Payment processed and lease activated successfully! Tenant has been added to current tenants.", "success")
    return redirect(url_for('manager_view_applications'))


# Tenant Management Routes for Managers
@apartment.route('/manager_view_tenants')
def manager_view_tenants():
    if session.get("user_type") != "manager" or not session.get("community_id"):
        flash("Unauthorized access or no community assigned.", "error")
        return redirect(url_for('manager_home'))
    
    community_id = session.get("community_id")

    # Get all apartments in this community
    apartments = list(Apartment.collection.find({"community_id": community_id}))
    apartment_ids = [str(apt['_id']) for apt in apartments]

    # Get all active leases for these apartments
    active_leases = list(LeaseAgreement.collection.find({
        "apartment_id": {"$in": apartment_ids},
        "status": "active_paid"
    }))

    tenants_info = []
    for lease in active_leases:
        tenant = Tenant.get_by_id(lease.get('tenant_id'))
        apartment = Apartment.get_by_id(lease.get('apartment_id'))
        if tenant and apartment:
            tenants_info.append({
                "tenant": tenant,
                "apartment": apartment,
                "lease": lease
            })

    return render_template('manager/manager_view_tenants.html', 
                          tenants_info=tenants_info)

@apartment.route('/manager_tenant_details/<tenant_id>')
def manager_tenant_details(tenant_id):
    if session.get("user_type") != "manager" or not session.get("community_id"):
        flash("Unauthorized access or no community assigned.", "error")
        return redirect(url_for('manager_home'))
    
    community_id = session.get("community_id")
    tenant = Tenant.get_by_id(tenant_id)
    
    if not tenant:
        flash("Tenant not found.", "error")
        return redirect(url_for('manager_view_tenants'))
    
    # Find approved applications for this tenant in this community
    applications = list(Application.collection.find({
        "tenant_id": tenant_id,
        "decision_date": {"$exists": True},
        "reviewed_by": session.get("user_id"),
        "status": "approved"
    }))
    
    tenant_apartments = []
    for app in applications:
        apartment = Apartment.get_by_id(app.get('apartment_id'))
        if apartment and apartment.get('community_id') == community_id:
            tenant_apartments.append({
                "apartment": apartment,
                "application": app
            })
    
    return render_template('manager/manager_tenant_details.html',
                          tenant=tenant,
                          tenant_apartments=tenant_apartments)

@apartment.route('/manager_mark_apartment_occupied/<apartment_id>', methods=['POST'])
def manager_mark_apartment_occupied(apartment_id):
    if session.get("user_type") != "manager" or not session.get("community_id"):
        flash("Unauthorized access or no community assigned.", "error")
        return redirect(url_for('manager_home'))
    
    community_id = session.get("community_id")
    apartment = Apartment.get_by_id(apartment_id)
    
    # Verify the apartment belongs to the manager's community
    if not apartment or apartment.get('community_id') != community_id:
        flash("Apartment not found or not in your community.", "error")
        return redirect(url_for('manager_view_apartments'))
    
    # Check if there's an active lease for this apartment
    active_lease = LeaseAgreement.find_one({
        'apartment_id': str(apartment_id),
        'status': 'active_paid'
    })
    
    if not active_lease:
        flash("Cannot mark apartment as occupied without an active lease.", "error")
        return redirect(url_for('manager_view_apartments'))
    
    # Update apartment status to occupied
    Apartment.update_status(apartment_id, 'occupied')
    
    flash("Apartment marked as occupied successfully!", "success")
    return redirect(url_for('manager_view_apartments'))
