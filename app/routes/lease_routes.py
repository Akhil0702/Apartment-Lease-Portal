from flask import render_template, request, redirect, url_for, session, flash, jsonify
from app import apartment
from app.models.tenants import Tenant
from app.models.apartments import Apartment
from app.models.applications import Application
from app.models.communities import Community
from app.models.managers import Manager
from app.models.lease_agreements import LeaseAgreement
from app.models.payments import Payment
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from .decorators import login_required
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@apartment.route('/create_lease_agreement/<application_id>', methods=['GET', 'POST'])
@login_required
def create_lease_agreement(application_id):
    if session.get("user_type") != "tenant":
        flash("Unauthorized access.", "error")
        return redirect(url_for('tenant_login'))
    
    tenant_id = session.get("user_id")
    
    # Get application details
    application = Application.get_by_id(application_id)
    
    if not application or application.get('tenant_id') != tenant_id:
        flash("Application not found or unauthorized access.", "error")
        return redirect(url_for('view_tenant_applications'))
    
    # Check if application is approved
    if application.get('status') != 'approved':
        flash("You can only create a lease agreement for approved applications.", "error")
        return redirect(url_for('application_details', application_id=application_id))
    
    # Check if a lease agreement already exists for this application
    existing_lease = LeaseAgreement.collection.find_one({
        "application_id": application_id
    })
    
    if existing_lease:
        flash("A lease agreement already exists for this application.", "info")
        return redirect(url_for('view_lease_agreement', lease_id=existing_lease['_id']))
    
    # Get apartment details
    apartment = Apartment.get_by_id(application.get('apartment_id'))
    
    if not apartment:
        flash("Apartment information not found.", "error")
        return redirect(url_for('view_tenant_applications'))
    
    if request.method == 'POST':
        # Calculate lease end date based on start date and term
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        lease_term = int(request.form.get('lease_term'))
        end_date = start_date + timedelta(days=lease_term * 30)  # Approximate months to days
        
        # Create lease agreement data
        lease_data = {
            "tenant_id": tenant_id,
            "apartment_id": application.get('apartment_id'),
            "application_id": application_id,
            "start_date": start_date,
            "end_date": end_date,
            "security_deposit": float(apartment.get('rent')),
            "monthly_rent": float(apartment.get('rent')),
            "lease_status": "pending",  # Will be set to active after payment
            "created_at": datetime.now(),
            "terms_accepted": True if request.form.get('terms_accepted') else False
        }
        
        # Create the lease agreement
        lease_id = LeaseAgreement.create(lease_data)
        
        flash("Lease agreement created successfully! Please proceed with the initial payment.", "success")
        return redirect(url_for('make_initial_payment', lease_id=lease_id))
    
    # Get community info
    community = None
    if apartment.get('community_id'):
        community = Community.get_by_id(apartment.get('community_id'))
    
    return render_template('tenant/create_lease_agreement.html',
                          application=application,
                          apartment=apartment,
                          community=community)

@apartment.route('/view_lease_agreement/<lease_id>')
@login_required
def view_lease_agreement(lease_id):
    if session.get("user_type") != "tenant":
        flash("Unauthorized access.", "error")
        return redirect(url_for('tenant_login'))
    
    tenant_id = session.get("user_id")
    
    # Get lease agreement details
    lease = LeaseAgreement.get_by_id(lease_id)
    
    if not lease or lease.get('tenant_id') != tenant_id:
        flash("Lease agreement not found or unauthorized access.", "error")
        return redirect(url_for('view_tenant_leases'))
    
    # Get apartment and application details
    apartment = Apartment.get_by_id(lease.get('apartment_id'))
    application = Application.get_by_id(lease.get('application_id'))
    
    # Get community info
    community = None
    if apartment and apartment.get('community_id'):
        community = Community.get_by_id(apartment.get('community_id'))
    
    # Get payment history for this lease
    payments = list(Payment.collection.find({"lease_id": lease_id}))
    
    return render_template('tenant/view_lease_agreement.html',
                          lease=lease,
                          apartment=apartment,
                          application=application,
                          community=community,
                          payments=payments)

@apartment.route('/view_tenant_leases')
@login_required
def view_tenant_leases():
    if session.get("user_type") != "tenant":
        flash("Unauthorized access.", "error")
        return redirect(url_for('tenant_login'))
    
    tenant_id = session.get("user_id")
    
    # Get all lease agreements for this tenant
    leases = LeaseAgreement.get_by_tenant_id(tenant_id)
    
    # Get apartment details for each lease
    for lease in leases:
        lease['apartment'] = Apartment.get_by_id(lease.get('apartment_id'))
        
        # Get community details if available
        if lease['apartment'] and lease['apartment'].get('community_id'):
            lease['community'] = Community.get_by_id(lease['apartment'].get('community_id'))
        else:
            lease['community'] = None
    
    return render_template('tenant/view_leases.html', leases=leases)

@apartment.route('/make_initial_payment/<lease_id>', methods=['GET', 'POST'])
@login_required
def make_initial_payment(lease_id):
    if session.get("user_type") != "tenant":
        flash("Unauthorized access.", "error")
        return redirect(url_for('tenant_login'))
    
    tenant_id = session.get("user_id")
    
    # Get lease agreement details
    lease = LeaseAgreement.get_by_id(lease_id)
    
    if not lease or lease.get('tenant_id') != tenant_id:
        flash("Lease agreement not found or unauthorized access.", "error")
        return redirect(url_for('view_tenant_leases'))
    
    # Check if initial payment has already been made
    existing_payment = Payment.collection.find_one({
        "lease_id": lease_id,
        "payment_type": "initial"
    })
    
    if existing_payment:
        flash("Initial payment has already been made for this lease.", "info")
        return redirect(url_for('view_lease_agreement', lease_id=lease_id))
    
    # Get apartment details
    apartment = Apartment.get_by_id(lease.get('apartment_id'))
    
    if request.method == 'POST':
        # Calculate total amount (security deposit + first month's rent)
        total_amount = lease.get('security_deposit') + lease.get('monthly_rent')
        
        # Create payment data
        payment_data = {
            "lease_id": lease_id,
            "tenant_id": tenant_id,
            "total_amount": total_amount,
            "payment_method": request.form.get('payment_method'),
            "payment_type": "initial",  # To distinguish from regular rent payments
            "payment_status": "completed",
            "transaction_id": f"INIT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.now()
        }
        
        # Create the payment record
        Payment.create(payment_data)
        
        # Update lease status to active
        LeaseAgreement.update(lease_id, {
            "lease_status": "active",
            "payment_completed": True
        })
        
        # Update apartment status to occupied
        Apartment.update(lease.get('apartment_id'), {
            "status": "occupied"
        })
        
        flash("Initial payment completed successfully! Your lease is now active.", "success")
        return redirect(url_for('view_lease_agreement', lease_id=lease_id))
    
    # Calculate total amount due
    total_due = lease.get('security_deposit') + lease.get('monthly_rent')
    
    return render_template('tenant/make_initial_payment.html',
                          lease=lease,
                          apartment=apartment,
                          total_due=total_due)

@apartment.route('/make_rent_payment/<lease_id>', methods=['GET', 'POST'])
@login_required
def make_rent_payment(lease_id):
    if session.get("user_type") != "tenant":
        flash("Unauthorized access.", "error")
        return redirect(url_for('tenant_login'))
    
    tenant_id = session.get("user_id")
    
    # Get lease agreement details
    lease = LeaseAgreement.get_by_id(lease_id)
    
    if not lease or lease.get('tenant_id') != tenant_id:
        flash("Lease agreement not found or unauthorized access.", "error")
        return redirect(url_for('view_tenant_leases'))
    
    # Check if lease is active
    if lease.get('lease_status') != 'active':
        flash("You can only make payments for active leases.", "error")
        return redirect(url_for('view_lease_agreement', lease_id=lease_id))
    
    # Get apartment details
    apartment = Apartment.get_by_id(lease.get('apartment_id'))
    
    if request.method == 'POST':
        # Create payment data
        payment_data = {
            "lease_id": lease_id,
            "tenant_id": tenant_id,
            "total_amount": float(request.form.get('amount')),
            "payment_method": request.form.get('payment_method'),
            "payment_type": "rent",
            "payment_status": "completed",
            "transaction_id": f"RENT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "due_date": datetime.strptime(request.form.get('due_date'), '%Y-%m-%d'),
            "timestamp": datetime.now()
        }
        
        # Create the payment record
        Payment.create(payment_data)
        
        flash("Rent payment completed successfully!", "success")
        return redirect(url_for('view_lease_agreement', lease_id=lease_id))
    
    return render_template('tenant/make_rent_payment.html',
                          lease=lease,
                          apartment=apartment)
