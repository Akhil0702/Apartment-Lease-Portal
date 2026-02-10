from flask import render_template, request, redirect, url_for, session, flash, jsonify, send_file
from app import apartment
from .decorators import login_required
import logging
from datetime import datetime, timedelta
from bson.objectid import ObjectId 
from flask import jsonify 
from app.models.tenants import Tenant 
from app.models.managers import Manager
from app.models.payments import Payment 
from app.models.applications import Application
from app.models.apartments import Apartment
from app.models.admin import Admin
from app.models.communities import Community
from werkzeug.security import generate_password_hash, check_password_hash
import io
import csv
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet





@apartment.route('/admin_assign_community', methods=['POST'])
@login_required
def admin_assign_community():
    if session["user_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))
    
    manager_id = request.form.get('manager_id')
    community_id = request.form.get('community_id')
    
    if not manager_id or not community_id:
        flash("Missing required information.", "error")
        return redirect(url_for('admin_view_managers'))
    
    # Get the manager to check if they're already assigned
    manager = Manager.get_by_id(manager_id)
    if not manager:
        flash("Manager not found.", "error")
        return redirect(url_for('admin_view_managers'))
    
    # Check if the manager is already assigned to a community
    if 'community_id' in manager and manager['community_id'] and str(manager['community_id']) != community_id:
        # Get the current community name for the error message
        current_community = Community.get_by_id(manager['community_id'])
        current_community_name = current_community['name'] if current_community else "another community"
        
        flash(f"This manager is already assigned to {current_community_name}. Please unassign them first.", "error")
        return redirect(url_for('admin_view_managers'))
    
    # Check if the community already has a manager assigned to it
    existing_managers = Manager.get_by_community(community_id)
    if existing_managers and (not 'community_id' in manager or manager.get('community_id') != community_id):
        # Get the existing manager's name for the error message
        existing_manager = existing_managers[0]
        existing_manager_name = f"{existing_manager.get('first_name', '')} {existing_manager.get('last_name', '')}"
        
        # Get community name for the error message
        community = Community.get_by_id(community_id)
        community_name = community['name'] if community else "this community"
        
        flash(f"{community_name} is already assigned to {existing_manager_name}. Please unassign them first.", "error")
        return redirect(url_for('admin_view_managers'))
    
    # Assign manager to community
    Manager.assign_to_community(manager_id, community_id)
    
    # Get community name for the flash message
    community = Community.get_by_id(community_id)
    community_name = community['name'] if community else "Unknown Community"
    
    flash(f"Manager assigned to {community_name}.", "success")
    return redirect(url_for('admin_view_managers'))

@apartment.route('/admin_reset_manager_password', methods=['POST'])
@login_required
def admin_reset_manager_password():
    if session["user_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))
    
    manager_id = request.form.get('manager_id')
    new_password = request.form.get('new_password')
    
    if not manager_id or not new_password:
        flash("Missing required information.", "error")
        return redirect(url_for('admin_view_managers'))
    
    # Reset manager password
    Manager.reset_password(manager_id, new_password)
    flash("Manager password has been reset.", "success")
    return redirect(url_for('admin_view_managers'))

@apartment.route('/admin_update_manager_phone', methods=['POST'])
@login_required
def admin_update_manager_phone():
    if session["user_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))
    
    manager_id = request.form.get('manager_id')
    new_phone = request.form.get('new_phone')
    
    if not manager_id or not new_phone:
        flash("Missing required information.", "error")
        return redirect(url_for('admin_view_managers'))
    
    # Update manager phone
    Manager.update_phone(manager_id, new_phone)
    flash("Manager phone number has been updated.", "success")
    return redirect(url_for('admin_view_managers'))

@apartment.route('/admin_logout')
@login_required
def admin_logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('admin_login'))

@apartment.route('/admin_view_communities', methods=['GET'])
@login_required
def admin_view_communities():
    if session["user_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))
    
    # Get filter parameter
    status = request.args.get('status')
    
    # Apply filter if provided
    query = {}
    if status:
        query['status'] = status
    
    # Get communities with filter
    communities = list(Community.collection.find(query)) if query else Community.get_all()
    
    return render_template('admin/admin_view_communities.html', 
                          communities=communities,
                          selected_status=status)

@apartment.route('/admin_create_community', methods=['GET', 'POST'])
@login_required
def admin_create_community():
    if session["user_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))
    
    if request.method == 'POST':
        community_name = request.form.get('community_name')
        location = request.form.get('location')
        city = request.form.get('city')
        state = request.form.get('state')
        zipcode = request.form.get('zipcode')
        status = request.form.get('status', 'active')
        
        if not community_name or not location or not city or not state or not zipcode:
            flash("All fields are required.", "error")
            return redirect(url_for('admin_create_community'))
        
        # Create community data
        community_data = {
            'name': community_name,
            'location': location,
            'city': city,
            'state': state,
            'zipcode': zipcode,
            'status': status,
            'created_at': datetime.now()
        }
        
        # Create community
        Community.create(community_data)
        flash("Community created successfully.", "success")
        return redirect(url_for('admin_view_communities'))
    
    return render_template('admin/admin_create_community.html')

@apartment.route('/admin_edit_community/<community_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_community(community_id):
    if session["user_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))
    
    # Get community
    community = Community.get_by_id(community_id)
    if not community:
        flash("Community not found.", "error")
        return redirect(url_for('admin_view_communities'))
    
    if request.method == 'POST':
        community_name = request.form.get('community_name')
        location = request.form.get('location')
        city = request.form.get('city')
        state = request.form.get('state')
        zipcode = request.form.get('zipcode')
        status = request.form.get('status')
        
        if not community_name or not location or not city or not state or not zipcode or not status:
            flash("All fields are required.", "error")
            return redirect(url_for('admin_edit_community', community_id=community_id))
        
        # Update community data
        community_data = {
            'name': community_name,
            'location': location,
            'city': city,
            'state': state,
            'zipcode': zipcode,
            'status': status,
            'updated_at': datetime.now()
        }
        
        # Update community
        Community.update(community_id, community_data)
        flash("Community updated successfully.", "success")
        return redirect(url_for('admin_view_communities'))
    
    return render_template('admin/admin_edit_community.html', community=community)

@apartment.route('/admin_delete_community', methods=['POST'])
@login_required
def admin_delete_community():
    if session["user_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))
    
    community_id = request.form.get('community_id')
    if not community_id:
        flash("Community ID is required.", "error")
        return redirect(url_for('admin_view_communities'))
    
    # Check if there are any apartments, managers, or tenants associated with this community
    # If there are, don't allow deletion
    
    # Delete community
    Community.delete(community_id)
    flash("Community deleted successfully.", "success")
    return redirect(url_for('admin_view_communities'))

@apartment.route('/admin_community_status', methods=['POST'])
@login_required
def admin_community_status():
    if session["user_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))
    
    community_id = request.form.get('community_id')
    new_status = request.form.get('status')
    
    if not community_id or not new_status:
        flash("Missing required information.", "error")
        return redirect(url_for('admin_view_communities'))
    
    # Update community status
    Community.update(community_id, {'status': new_status})
    flash(f"Community status updated to {new_status}.", "success")
    return redirect(url_for('admin_view_communities'))

@apartment.route('/admin_unassign_community', methods=['POST'])
@login_required
def admin_unassign_community():
    if session["user_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))
    
    manager_id = request.form.get('manager_id')
    
    if not manager_id:
        flash("Missing required information.", "error")
        return redirect(url_for('admin_view_managers'))
    
    # Get the manager to check if they're assigned to a community
    manager = Manager.get_by_id(manager_id)
    if not manager:
        flash("Manager not found.", "error")
        return redirect(url_for('admin_view_managers'))
    
    # Check if the manager is assigned to a community
    if 'community_id' not in manager or not manager['community_id']:
        flash("This manager is not assigned to any community.", "error")
        return redirect(url_for('admin_view_managers'))
    
    # Get community name for the flash message before unassigning
    community = Community.get_by_id(manager['community_id'])
    community_name = community['name'] if community else "Unknown Community"
    
    # Unassign manager from community
    Manager.unassign_from_community(manager_id)
    
    flash(f"Manager unassigned from {community_name}.", "success")
    return redirect(url_for('admin_view_managers'))