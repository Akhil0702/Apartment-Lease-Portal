from flask import render_template, request, redirect, url_for, session, jsonify, flash
from app import apartment
from app.models.tenants import Tenant
from app.models.admin import Admin 
from app.models.apartments import Apartment
from app.models.applications import Application
from app.models.communities import Community
from .decorators import login_required
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from functools import wraps





# Apartment Management Routes for Managers
@apartment.route('/manager_view_apartments')
def manager_view_apartments():
    if session.get("user_type") != "manager" or not session.get("community_id"):
        flash("Unauthorized access or no community assigned.", "error")
        return redirect(url_for('manager_home'))
    
    # Get apartments for the manager's assigned community
    community_id = session.get("community_id")
    apartments = list(Apartment.collection.find({"community_id": community_id}))
    
    # Get community details
    community = Community.get_by_id(community_id)
    
    return render_template('manager/manager_view_apartments.html', 
                          apartments=apartments,
                          community=community)

@apartment.route('/manager_add_apartment', methods=['GET', 'POST'])
def manager_add_apartment():
    if session.get("user_type") != "manager" or not session.get("community_id"):
        flash("Unauthorized access or no community assigned.", "error")
        return redirect(url_for('manager_home'))
    
    community_id = session.get("community_id")
    community = Community.get_by_id(community_id)
    
    if request.method == 'POST':
        apartment_data = {
            "community_id": community_id,
            "floor_number": request.form.get('floor_number'),
            "apartment_number": request.form.get('apartment_number'),
            "rent": float(request.form.get('rent')),
            "bedrooms": int(request.form.get('bedrooms')),
            "bathrooms": float(request.form.get('bathrooms')),
            "status": request.form.get('status', 'available'),
            "address": request.form.get('address'),
            "city": request.form.get('city'),
            "state": request.form.get('state'),
            "zipcode": request.form.get('zipcode'),
            "dimensions": request.form.get('dimensions'),
            "created_at": datetime.utcnow()
        }
        
        # Create the apartment
        Apartment.create(apartment_data)
        flash("Apartment added successfully!", "success")
        return redirect(url_for('manager_view_apartments'))
    
    return render_template('manager/manager_add_apartment.html', community=community)

@apartment.route('/manager_edit_apartment/<apartment_id>', methods=['GET', 'POST'])
def manager_edit_apartment(apartment_id):
    if session.get("user_type") != "manager" or not session.get("community_id"):
        flash("Unauthorized access or no community assigned.", "error")
        return redirect(url_for('manager_home'))
    
    community_id = session.get("community_id")
    apartment = Apartment.get_by_id(apartment_id)
    
    # Verify the apartment belongs to the manager's community
    if not apartment or apartment.get('community_id') != community_id:
        flash("Apartment not found or not in your community.", "error")
        return redirect(url_for('manager_view_apartments'))
    
    if request.method == 'POST':
        apartment_data = {
            "floor_number": request.form.get('floor_number'),
            "apartment_number": request.form.get('apartment_number'),
            "rent": float(request.form.get('rent')),
            "bedrooms": int(request.form.get('bedrooms')),
            "bathrooms": float(request.form.get('bathrooms')),
            "status": request.form.get('status'),
            "address": request.form.get('address'),
            "city": request.form.get('city'),
            "state": request.form.get('state'),
            "zipcode": request.form.get('zipcode'),
            "dimensions": request.form.get('dimensions')
        }
        
        # Update the apartment
        Apartment.update(apartment_id, apartment_data)
        flash("Apartment updated successfully!", "success")
        return redirect(url_for('manager_view_apartments'))
    
    return render_template('manager/manager_edit_apartment.html', apartment=apartment)
