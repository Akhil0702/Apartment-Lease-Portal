from flask import render_template, request, redirect, url_for, session, flash
from app import apartment
from .decorators import login_required
import logging
from datetime import datetime, timedelta
from bson.objectid import ObjectId 
from flask import jsonify 
from app.models.tenants import Tenant 
from app.models.payments import Payment 
from app.models.applications import Application
from app.models.apartments import Apartment
from app.models.admin import Admin
from werkzeug.security import generate_password_hash, check_password_hash



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@apartment.route('/return_apartment/<application_id>', methods=['POST'])
@login_required
def return_apartment(application_id):
    application = Application.get_application_by_id(application_id)
    if not application:
        flash("Application not found.", "error")
        return redirect(url_for('view_tenant_applications'))

    if application.get('status') != 'completed':
        flash("Only completed applications can be returned.", "error")
        return redirect(url_for('view_tenant_applications'))

    # Calculate fine if overdue
    current_date = datetime.now()
    rent_end_date = application['booked_period']['end_date']
    overdue_status = current_date > rent_end_date
    fine = 0
    if overdue_status:
        overdue_days = (current_date - rent_end_date).days
        fine = overdue_days * 2  # $2 fine per day (example logic)

    # Update application status to "return_initiated"
    Application.update(application_id, {
        "return_details.return_initiated_date": current_date,
        "overdue_status": overdue_status,
        "fine_if_applicable": fine,
        "status": "return_initiated"
    })

    flash("Return process initiated successfully. Please wait for manager confirmation.", "success")
    return redirect(url_for('view_tenant_applications'))



@apartment.route('/initiate_return/<application_id>', methods=['POST'])
@login_required
def initiate_return(application_id):
    logger.info(f"Initiating return for application_id: {application_id}")
    
    # Fetch the application
    application = Application.get_application_by_id(application_id)
    if not application:
        logger.error(f"Application not found for ID: {application_id}")
        flash("Application not found.", "error")
        return redirect(url_for('view_tenant_applications'))

    # Check if the application is eligible for return
    if application.get('status') != 'delivered':
        logger.error(f"Application status is not 'delivered': {application.get('status')}")
        flash("Only delivered applications can be returned.", "error")
        return redirect(url_for('view_tenant_applications'))

    # Record return initiation date
    return_initiated_date = datetime.now()

    # Calculate overdue status and fine (if applicable)
    rent_end_date = application['booked_period']['end_date']
    overdue_status = return_initiated_date > rent_end_date
    fine = 0.0

    if overdue_status:
        # Calculate fine as $2 per overdue day (example logic)
        overdue_days = (return_initiated_date - rent_end_date).days
        fine = overdue_days * 2

    # Update the application with return details
    Application.update(application_id, {
        "return_details.return_initiated_date": return_initiated_date,
        "overdue_status": overdue_status,
        "fine_if_applicable": fine,
        "status": "return_initiated"
    })

    logger.info(f"Return initiated successfully for application_id: {application_id}")
    flash("Return initiated successfully.", "success")
    return redirect(url_for('view_tenant_applications'))



@apartment.route('/confirm_return/<application_id>', methods=['POST', 'GET'])
@login_required
def confirm_return(application_id):
    logger.info(f"Confirming return for application_id: {application_id}")

    # Fetch the application
    application = Application.get_application_by_id(application_id)
    if not application:
        logger.error(f"Application not found for ID: {application_id}")
        flash("Application not found.", "error")
        return redirect(url_for('manager_view_applications'))

    # Check if return was initiated
    if application.get('status') != 'return_initiated':
        logger.error(f"Application status is not 'return_initiated': {application.get('status')}")
        flash("Return must be initiated before confirmation.", "error")
        return redirect(url_for('manager_view_applications'))

    # Record return received date
    return_received_date = datetime.now()

    # Update apartment availability
    apartment_id = application['apartment_id']
    Apartment.update_availability(apartment_id, {"availability": "available"})

    # Update the payment details if fine exists
    payment_id = application['payment_id']
    fine = application.get('fine_if_applicable', 0)

    if payment_id:
        payment = Payment.get_by_id(payment_id)
        if payment:
            total_amount = payment['amount'] + fine
            admin_commission = total_amount * 0.10
            manager_earning = total_amount - admin_commission

            Payment.update(payment_id, {
                'fine': fine,
                'amount': total_amount,
                'admin_commission': admin_commission,
                'manager_earning': manager_earning
            })

    # Update the application with final return details
    Application.update(application_id, {
        "return_details.return_received_date": return_received_date,
        "status": "returned"
    })

    logger.info(f"Return confirmed for application_id: {application_id}")
    flash("Return confirmed successfully.", "success")
    return redirect(url_for('manager_view_applications'))





@apartment.route('/update_application_status/<application_id>', methods=['POST'])
@login_required
def update_application_status(application_id):
    new_status = request.form.get('status')
    if not new_status:
        flash("Invalid status update.", "error")
        return redirect(url_for('manager_view_applications'))

    # Update the application status
    Application.update(application_id, {"status": new_status})

    flash("Application status updated successfully.", "success")
    return redirect(url_for('manager_view_applications'))
