from flask import render_template, request, redirect, url_for, session, flash
from app import apartment
from app.models.tenants import Tenant
from app.models.admin import Admin
from app.models.applications import Application
from app.models.apartments import Apartment
from app.models.payments import Payment
from .decorators import login_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from bson import ObjectId

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@apartment.route('/checkout/<application_id>', methods=['GET', 'POST'])
def checkout(application_id):
    user_id = session.get('tenant_id')

    # Convert application_id to ObjectId for MongoDB query
    application = Application.get_application_by_id(ObjectId(application_id))
    apartment = Apartment.get_by_id(application['apartment_id'])  # Assuming apartment_id is in the application document

    if not application or not apartment:
        flash('Invalid application or apartment', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Get form data
        card_name = request.form.get('card_name')
        card_number = request.form.get('card_number')
        expiry_date = request.form.get('expiry_date')
        cvv = request.form.get('cvv')

        # Basic validation (you can expand this further)
        if not (card_name and card_number and expiry_date and cvv):
            flash('All fields are required', 'error')
            return redirect(url_for('checkout', application_id=application_id))

        # Simulate payment processing
        try:
            # In a real app, you'd integrate with a payment processor here
            payment_data = {
                'application_id': application['_id'],
                'tenant_id': user_id,
                'amount': application['price'],
                'status': 'completed',
                'created_at': datetime.now(),
                'payment_method': 'credit_card',
                'card_name': card_name,
                'card_number': card_number,  # Be cautious, never store raw card numbers in production
                'expiry_date': expiry_date,
                'cvv': cvv  # Never store CVV in production, this is just for demonstration
            }

            # Save payment details to the database
            Payment.create(payment_data)
            
            # Update application status to 'completed'
            Application.update(application['_id'], {'status': 'completed'})

            flash('Payment successful! Apartment rented.', 'success')
            return redirect(url_for('view_tenant_applications'))

        except Exception as e:
            logger.error(f"Payment error: {str(e)}")
            flash('Payment failed. Please try again.', 'error')

    return render_template('payment/checkout.html', application=application, apartment=apartment)
