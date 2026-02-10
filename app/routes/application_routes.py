from flask import render_template, request, redirect, url_for, session, flash, jsonify
from app import apartment
from app.models.tenants import Tenant
from app.models.apartments import Apartment
from app.models.applications import Application
from bson import ObjectId
from app.models.payments import Payment
from app.models.communities import Community
from app.models.lease_agreements import LeaseAgreement
from app.models.managers import Manager
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from .decorators import login_required
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@apartment.route('/apply_for_apartment/<apartment_id>', methods=['GET', 'POST'])
@login_required
def apply_for_apartment(apartment_id):
    if session.get("user_type") != "tenant":
        flash("Unauthorized access.", "error")
        return redirect(url_for('tenant_login'))
    
    tenant_id = session.get("user_id")
    
    # Get apartment and tenant details
    apartment = Apartment.get_by_id(apartment_id)
    tenant = Tenant.get_by_id(tenant_id)
    
    if not apartment:
        flash("Apartment not found.", "error")
        return redirect(url_for('tenant_home'))
    
    if not tenant:
        flash("Tenant information not found.", "error")
        return redirect(url_for('tenant_login'))
    
    # Check if apartment is available
    if apartment.get('status') != 'available':
        flash("This apartment is not available for lease.", "error")
        return redirect(url_for('tenant_home'))
    
    # Check if tenant already has a pending application for this apartment
    existing_application = Application.collection.find_one({
        "tenant_id": tenant_id,
        "apartment_id": apartment_id,
        "status": "pending"
    })
    
    if existing_application:
        flash("You already have a pending application for this apartment.", "info")
        return redirect(url_for('view_tenant_applications'))
    
    if request.method == 'POST':
        # Create application data
        application_data = {
            "tenant_id": tenant_id,
            "apartment_id": apartment_id,
            "status": "pending",
            "application_date": datetime.now(),
            "move_in_date": datetime.strptime(request.form.get('move_in_date'), '%Y-%m-%d'),
            "lease_term": int(request.form.get('lease_term')),
            "additional_notes": request.form.get('additional_notes', ''),
            "application_fee": 50  # Adding $50 application fee
        }
        
        # Submit application
        application_id = Application.create(application_data).inserted_id
        
        # Create application fee payment record
        payment_data = {
            'payment_method': 'pending',
            'application_id': str(application_id),
            'tenant_id': tenant_id,
            'apartment_id': apartment_id,
            'amount': 50,  # $50 application fee
            'payment_type': 'application_fee',
            'payment_date': datetime.now(),
            'status': 'pending'  # Tenant will need to complete this payment
        }
        
        # Save the payment record
        Payment.create(payment_data)
        
        flash("Your application has been submitted successfully! Please pay the $50 application fee to proceed.", "success")
        return redirect(url_for('view_tenant_applications'))
    
    # Get the community info for the apartment
    community = None
    if apartment.get('community_id'):
        community = Community.get_by_id(apartment.get('community_id'))
    
    return render_template('tenant/apply_for_apartment.html', 
                          apartment=apartment,
                          tenant=tenant,
                          community=community)

@apartment.route('/view_tenant_applications')
@login_required
def view_tenant_applications():
    user_id = session.get('user_id')
    
    # Get all applications for the current tenant
    applications = Application.get_tenant_applications(user_id)
    current_time = datetime.now()
    
    # For each application, get apartment and lease details
    for app in applications:
        # Get apartment details
        app['apartment'] = Apartment.get_by_id(app.get('apartment_id'))
        
        # Convert application dates
        if 'application_date' in app and isinstance(app['application_date'], str):
            app['application_date'] = datetime.strptime(app['application_date'], '%Y-%m-%d')
        if 'move_in_date' in app and isinstance(app['move_in_date'], str):
            app['move_in_date'] = datetime.strptime(app['move_in_date'], '%Y-%m-%d')
        if 'end_date' in app and isinstance(app['end_date'], str):
            app['end_date'] = datetime.strptime(app['end_date'], '%Y-%m-%d')
        
        # For approved or completed applications, get lease agreement
        if app['status'] in ['approved', 'completed']:
            print(f"Getting lease for application {app['_id']}")  # Debug
            lease = LeaseAgreement.get_by_application_id(str(app['_id']))
            print(f"Found lease: {lease}")  # Debug
            
            if lease:
                # Convert lease dates if they're strings
                if 'start_date' in lease and isinstance(lease['start_date'], str):
                    lease['start_date'] = datetime.strptime(lease['start_date'], '%Y-%m-%d')
                if 'end_date' in lease and isinstance(lease['end_date'], str):
                    lease['end_date'] = datetime.strptime(lease['end_date'], '%Y-%m-%d')
                
                app['lease_agreement'] = lease
                print(f"Lease end date: {lease.get('end_date')}")  # Debug
                if lease.get('end_date'):
                    days_remaining = (lease['end_date'] - current_time).days
                    print(f"Days remaining: {days_remaining}")  # Debug
    
    print(f"Current time being passed to template: {current_time}")  # Debug
    
    return render_template('tenant/view_applications.html', 
                         applications=applications,
                         now=current_time)

@apartment.route('/application/<application_id>')
@login_required
def application_details(application_id):
    if session.get("user_type") != "tenant":
        flash("Unauthorized access.", "error")
        return redirect(url_for('tenant_login'))
    
    tenant_id = session.get("user_id")
    
    # Get application details
    application = Application.get_by_id(application_id)
    
    if not application or application.get('tenant_id') != tenant_id:
        flash("Application not found or unauthorized access.", "error")
        return redirect(url_for('view_tenant_applications'))
    
    # Get apartment details
    apartment = Apartment.get_by_id(application.get('apartment_id'))
    
    # Get community info
    community = None
    if apartment and apartment.get('community_id'):
        community = Community.get_by_id(apartment.get('community_id'))
    
    # Check if a lease agreement exists for this application
    lease_agreement = LeaseAgreement.collection.find_one({
        "application_id": application_id
    })
    
    # Get payment information
    application_fee_payment = Payment.find_one({
        "application_id": application_id,
        "tenant_id": tenant_id,
        "payment_type": "application_fee"
    })
    
    initial_payment = Payment.find_one({
        "application_id": application_id,
        "tenant_id": tenant_id,
        "payment_type": "initial_payment"
    })
    
    return render_template('tenant/application_details.html',
                          application=application,
                          apartment=apartment,
                          community=community,
                          lease_agreement=lease_agreement,
                          application_fee_payment=application_fee_payment,
                          initial_payment=initial_payment)

@apartment.route('/rent_apartment/<apartment_id>', methods=['GET', 'POST'])
def rent_apartment(apartment_id):
    user_id = session.get('user_id')
    
    # Retrieve apartment and user details
    apartment = Apartment.get_by_id(apartment_id)
    user = Tenant.get_by_id(user_id)

    if not apartment:
        flash('Apartment not found', 'error')
        return redirect(url_for('index'))
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('tenant_login'))
        
    # Check if apartment is available
    if apartment.get('status') != 'available':
        flash('This apartment is not available for rent', 'error')
        return redirect(url_for('index'))

    # Calculate unavailable dates and the next available date dynamically
    applications = Application.get_by_apartment_id(apartment_id)
    unavailable_dates = []
    
    # Find apartments with active leases
    for application in applications:
        if application.get('status') in ['approved', 'active']:
            unavailable_dates.append(application.get('move_in_date'))

    # Find the latest end date to calculate next available date
    if unavailable_dates:
        latest_end_date = max(unavailable_dates)
        next_available_date = (latest_end_date + timedelta(days=2)).strftime("%Y-%m-%d")
    else:
        # If no applications, set the next available date to today's date + buffer
        next_available_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")

    # Convert unavailable dates to string format for JavaScript
    unavailable_dates = [date.strftime("%Y-%m-%d") if isinstance(date, datetime) else date for date in unavailable_dates]

    if request.method == 'POST':
        # Get lease details
        lease_term = int(request.form.get('lease_term', 12))
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        # Get payment details
        payment_method = request.form.get('payment_method')
        card_number = request.form.get('card_number')
        expiry_date = request.form.get('expiry_date')
        cvv = request.form.get('cvv')
        account_number = request.form.get('account_number')
        routing_number = request.form.get('routing_number')
        
        # Validate payment information
        if payment_method in ['credit_card', 'debit_card'] and (not card_number or not expiry_date or not cvv):
            flash("Please fill in all card details to complete your application.", "error")
            return redirect(url_for('rent_apartment', apartment_id=apartment_id))
        
        if payment_method == 'bank_transfer' and (not account_number or not routing_number):
            flash("Please fill in all bank account details to complete your application.", "error")
            return redirect(url_for('rent_apartment', apartment_id=apartment_id))

        # Convert dates
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        # Monthly rent from apartment
        monthly_rent = float(apartment.get('rent', 0))
        
        # Create application data
        application_data = {
            'apartment_id': apartment_id,
            'tenant_id': user_id,
            'status': 'pending',
            'application_date': datetime.now(),
            'move_in_date': start_date,
            'end_date': end_date,
            'lease_term': lease_term,
            'monthly_rent': monthly_rent,
            'application_fee': 50  # Adding $50 application fee
        }
        
        # Create the application
        application_result = Application.create(application_data)
        application_id = str(application_result.inserted_id)
        
        # Create application fee payment record with completed status
        payment_data = {
            'payment_method': payment_method,
            'application_id': application_id,
            'tenant_id': user_id,
            'apartment_id': apartment_id,
            'amount': 50,  # $50 application fee
            'payment_type': 'application_fee',
            'payment_date': datetime.now(),
            'status': 'completed'  # Payment is completed immediately
        }
        
        # Add payment details based on method
        if payment_method in ['credit_card', 'debit_card']:
            payment_data['card_number'] = card_number
            payment_data['expiry_date'] = expiry_date
            payment_data['cvv'] = cvv
        elif payment_method == 'bank_transfer':
            payment_data['account_number'] = account_number
            payment_data['routing_number'] = routing_number
        
        # Save the payment record
        Payment.create(payment_data)
        
        flash("Application submitted and application fee paid successfully. A community manager will review your application.", "success")
        return redirect(url_for('view_tenant_applications'))

    # Render the rental form with calculated dates
    return render_template(
        'apartments/rent_apartment.html',
        apartment=apartment,
        unavailable_dates=unavailable_dates,
        next_available_date=next_available_date
    )

@apartment.route('/tenant/lease-agreement/<application_id>')
def tenant_lease_agreement(application_id):
    if session.get("user_type") != "tenant":
        flash("Unauthorized access.", "error")
        return redirect(url_for('tenant_home'))
    
    tenant_id = session.get("user_id")
    
    # Get application using Application model
    application = Application.find_one({
        '_id': ObjectId(application_id),
        'tenant_id': tenant_id
    })
    
    if not application:
        flash("Application not found.", "error")
        return redirect(url_for('view_tenant_applications'))
    
    # Get lease agreement using LeaseAgreement model
    lease = LeaseAgreement.find_one({
        'application_id': application_id,
        'tenant_id': tenant_id
    })
    
    if not lease:
        flash("Lease agreement not found.", "error")
        return redirect(url_for('view_tenant_applications'))
    
    # Get tenant and apartment using their respective models
    tenant = Tenant.get_by_id(tenant_id)
    apartment = Apartment.get_by_id(application['apartment_id'])
    
    return render_template('tenant/lease_agreement.html',
                         lease=lease,
                         tenant=tenant,
                         apartment=apartment,
                         application=application)

@apartment.route('/tenant/complete-lease/<lease_id>', methods=['POST'])
def tenant_complete_lease(lease_id):
    if session.get("user_type") != "tenant":
        flash("Unauthorized access.", "error")
        return redirect(url_for('tenant_home'))
    
    tenant_id = session.get("user_id")
    
    # Get lease agreement using LeaseAgreement model
    lease = LeaseAgreement.get_by_id(lease_id)
    
    if not lease or lease.get('tenant_id') != tenant_id:
        flash("Lease agreement not found.", "error")
        return redirect(url_for('view_tenant_applications'))
    
    # Update lease status using LeaseAgreement model method
    LeaseAgreement.update_status(lease_id, 'completed')
    
    flash("Lease agreement completed. Please contact the property manager to process your payment.", "success")
    return redirect(url_for('tenant_lease_agreement', application_id=lease['application_id']))

@apartment.route('/tenant/complete-lease-and-payment/<application_id>', methods=['POST'])
def tenant_complete_lease_and_payment(application_id):
    if session.get("user_type") != "tenant":
        flash("Unauthorized access.", "error")
        return redirect(url_for('tenant_home'))
    
    tenant_id = session.get("user_id")
    
    # Get application
    application = Application.find_one({
        '_id': ObjectId(application_id),
        'tenant_id': tenant_id
    })
    
    if not application:
        flash("Application not found.", "error")
        return redirect(url_for('view_tenant_applications'))
    
    # Determine payment type
    payment_type = request.form.get('payment_type', 'initial_payment')
    
    # Get existing payment record
    payment = Payment.find_one({
        'application_id': application_id,
        'tenant_id': tenant_id,
        'status': 'pending',
        'payment_type': payment_type
    })
    
    if not payment:
        flash("Payment record not found.", "error")
        return redirect(url_for('view_tenant_applications'))
    
    # Get payment method details from form
    payment_method = request.form.get('payment_method')
    if not payment_method:
        flash("Please select a payment method.", "error")
        return redirect(url_for('application_details', application_id=application_id))
    
    # Update payment with payment method details
    payment_update = {
        'payment_method': payment_method,
        'status': 'completed',
        'payment_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Add payment details based on method
    if payment_method in ['credit_card', 'debit_card']:
        card_number = request.form.get('card_number')
        expiry_date = request.form.get('expiry_date')
        cvv = request.form.get('cvv')
        
        if not card_number or not expiry_date or not cvv:
            flash("Please fill in all card details.", "error")
            return redirect(url_for('application_details', application_id=application_id))
        
        payment_update['card_number'] = card_number
        payment_update['expiry_date'] = expiry_date
        payment_update['cvv'] = cvv
        
    elif payment_method == 'bank_transfer':
        account_number = request.form.get('account_number')
        routing_number = request.form.get('routing_number')
        
        if not account_number or not routing_number:
            flash("Please fill in all bank account details.", "error")
            return redirect(url_for('application_details', application_id=application_id))
        
        payment_update['account_number'] = account_number
        payment_update['routing_number'] = routing_number
    
    # Update payment record
    Payment.update(payment['_id'], payment_update)
    
    # If this is an application fee payment, just update the status and return
    if payment_type == 'application_fee':
        flash("Application fee payment completed successfully! Your application will now be reviewed by a manager.", "success")
        return redirect(url_for('view_tenant_applications'))
    
    # For initial payment (after application approval), proceed with lease creation
    # Get apartment details
    apartment = Apartment.find_one({'_id': ObjectId(application['apartment_id'])})
    if not apartment:
        flash("Apartment not found.", "error")
        return redirect(url_for('view_tenant_applications'))
    
    # Create lease agreement now that payment is completed
    lease_data = {
        'tenant_id': application['tenant_id'],
        'apartment_id': str(application['apartment_id']),
        'application_id': application_id,
        'start_date': application['move_in_date'],
        'decision_date': application.get('decision_date', datetime.now()),
        'reviewed_by': application.get('reviewed_by'),
        'end_date': application['end_date'],
        'security_deposit': payment.get('security_deposit', apartment['rent']),
        'monthly_rent': apartment['rent'],
        'status': 'active_paid',
        'created_at': datetime.now()
    }
    
    # Create the lease agreement
    lease_id = LeaseAgreement.create(lease_data)
    
    # Update application status to completed
    Application.update_status(application_id, 'completed')
    
    # Note: We don't update the apartment status here since it should remain available
    # until the manager explicitly marks it as occupied
    
    flash("Payment completed and lease agreement created successfully! Welcome to your new home!", "success")
    return redirect(url_for('view_tenant_applications'))

@apartment.route('/tenant/withdraw-application/<application_id>', methods=['POST'])
def withdraw_application(application_id):
    if session.get("user_type") != "tenant":
        flash("Unauthorized access.", "error")
        return redirect(url_for('tenant_home'))
    
    tenant_id = session.get("user_id")
    
    # Get application
    application = Application.find_one({
        '_id': ObjectId(application_id),
        'tenant_id': tenant_id
    })
    
    if not application:
        flash("Application not found.", "error")
        return redirect(url_for('view_tenant_applications'))
    
    if application['status'] != 'pending':
        flash("Only pending applications can be withdrawn.", "error")
        return redirect(url_for('application_details', application_id=application_id))
    
    # Get payment record
    payment = Payment.find_one({
        'application_id': str(application['_id']),
        'tenant_id': tenant_id
    })
    
    if payment:
        # Update payment status to withdrawn
        Payment.update_status(payment['_id'], 'withdrawn')
    
    # Update application status
    Application.update_status(application_id, 'withdrawn')
    
    flash("Application has been withdrawn successfully.", "success")
    return redirect(url_for('view_tenant_applications'))

@apartment.route('/initiate_lease_renewal/<lease_id>', methods=['POST'])
@login_required
def initiate_lease_renewal(lease_id):
    user_id = session.get('user_id')
    
    # Get the current lease agreement
    current_lease = LeaseAgreement.get_by_id(lease_id)
    if not current_lease:
        flash("Lease agreement not found.", "error")
        return redirect(url_for('view_tenant_applications'))
    
    # Verify the lease belongs to this tenant
    if str(current_lease['tenant_id']) != str(user_id):
        flash("Unauthorized access.", "error")
        return redirect(url_for('view_tenant_applications'))
    
    # Check if renewal is allowed (60 days or less remaining)
    days_remaining = (current_lease['end_date'] - datetime.now()).days
    if days_remaining > 60:
        flash("Early renewal requires manager approval. Please contact your property manager.", "warning")
        return redirect(url_for('view_tenant_applications'))
    
    # Create a new application for renewal
    application_data = {
        'tenant_id': user_id,
        'apartment_id': current_lease['apartment_id'],
        'status': 'pending',
        'application_date': datetime.now(),
        'move_in_date': current_lease['end_date'],  # Start new lease when current one ends
        'end_date': current_lease['end_date'] + timedelta(days=365),  # Default to 1 year renewal
        'lease_term': 12,  # Default to 12 months
        'monthly_rent': current_lease['monthly_rent'],
        'is_renewal': True,
        'previous_lease_id': lease_id
    }
    
    # Create the renewal application
    Application.create(application_data)
    
    flash("Lease renewal application submitted successfully.", "success")
    return redirect(url_for('view_tenant_applications'))
