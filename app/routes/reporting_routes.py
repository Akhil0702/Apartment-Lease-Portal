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




@apartment.route('/admin_application_stats', methods=['GET'])
@login_required
def admin_application_stats():
    if session["tenant_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))
    
    # Get timeframe parameter
    timeframe = request.args.get('timeframe', 'week')
    
    # Get application statistics
    stats = Application.get_stats_by_timeframe(timeframe)
    
    # Get community summary
    community_stats = Application.get_summary_by_community()
    
    # Get community names
    communities = Community.get_all()
    community_names = {str(comm['_id']): comm['name'] for comm in communities}
    
    return render_template('admin/application_stats.html',
                          stats=stats,
                          community_stats=community_stats,
                          community_names=community_names,
                          selected_timeframe=timeframe)






@apartment.route('/admin_export_lease_summary', methods=['GET'])
@login_required
def admin_export_lease_summary():
    if session["tenant_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))
    
    # Get filter parameters
    status = request.args.get('status')
    community_id = request.args.get('community_id')
    
    # Apply filters if provided
    filters = {}
    if status:
        filters['status'] = status
    if community_id:
        filters['community_id'] = community_id
    
    # Get applications with filters
    applications = Application.get_filtered(filters) if filters else Application.get_all()
    
    # Get community names
    communities = Community.get_all()
    community_names = {str(comm['_id']): comm['name'] for comm in communities}
    
    # Create CSV buffer
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    
    # Write header row
    writer.writerow(['Application ID', 'Tenant ID', 'Tenant Name', 'Community', 'Status', 'Created Date'])
    
    # Write application data
    for app in applications:
        tenant = Tenant.get_by_id(app['tenant_id'])
        tenant_name = tenant['name'] if tenant else "Unknown Tenant"
        community_name = community_names.get(app.get('community_id', ''), 'Unknown Community')
        
        writer.writerow([
            str(app.get('_id', '')),
            app.get('tenant_id', 'N/A'),
            tenant_name,
            community_name,
            app.get('status', 'unknown'),
            app.get('created_at', 'N/A')
        ])
    
    # Reset buffer position to the beginning
    buffer.seek(0)
    
    # Create a response with the CSV
    return send_file(
        io.BytesIO(buffer.getvalue().encode()),
        as_attachment=True,
        download_name=f"lease_summary_{datetime.now().strftime('%Y%m%d')}.csv",
        mimetype='text/csv'
    )





@apartment.route('/admin_generate_invoice/<payment_id>', methods=['GET'])
@login_required
def admin_generate_invoice(payment_id):
    if session["tenant_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))
    
    # Get payment details
    payment = Payment.get_by_id(payment_id)
    if not payment:
        flash("Payment not found.", "error")
        return redirect(url_for('admin_view_payments'))
    
    # Get tenant details
    tenant = Tenant.get_by_id(payment.get('tenant_id', ''))
    tenant_name = f"{tenant.get('first_name', '')} {tenant.get('last_name', '')}" if tenant else "Unknown Tenant"
    
    # Get community details
    community = Community.get_by_id(payment.get('community_id', ''))
    community_name = community.get('name', 'Unknown Community') if community else "Unknown Community"
    
    # Generate PDF invoice
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from io import BytesIO
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Create content
    elements = []
    
    # Title
    title = Paragraph(f"<b>INVOICE</b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Invoice information
    invoice_info = [
        ["Invoice Number:", f"{payment.get('_id', 'Unknown')}"],
        ["Date:", f"{payment.get('payment_date', datetime.now()).strftime('%Y-%m-%d')}"],
        ["Status:", f"{payment.get('status', 'Unknown')}"],
    ]
    
    t = Table(invoice_info, colWidths=[120, 300])
    t.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))
    
    # Customer information
    customer_info = [
        ["Customer:", tenant_name],
        ["Community:", community_name],
        ["Apartment:", payment.get('apartment_id', 'Unknown')],
    ]
    
    t = Table(customer_info, colWidths=[120, 300])
    t.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))
    
    # Payment details
    payment_details = [
        ["Description", "Amount"],
        ["Rent Payment", f"${payment.get('amount', '0.00')}"],
    ]
    
    t = Table(payment_details, colWidths=[300, 120])
    t.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))
    
    # Total
    total = [
        ["", "Total:", f"${payment.get('amount', '0.00')}"],
    ]
    
    t = Table(total, colWidths=[200, 100, 120])
    t.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('LINEABOVE', (1, 0), (2, 0), 1, colors.black),
    ]))
    elements.append(t)
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    # Create response
    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=invoice_{payment_id}.pdf'
    
    return response

@apartment.route('/admin_export_payments', methods=['GET'])
@login_required
def admin_export_payments():
    if session["tenant_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))
    
    # Get filter parameters (same as in admin_view_payments)
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
    
    # Create CSV data
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Payment ID', 'Tenant ID', 'Tenant Name', 'Community', 'Apartment', 'Amount', 'Status', 'Date'])
    
    # Write data
    for payment in payments:
        tenant = Tenant.get_by_id(payment.get('tenant_id', ''))
        tenant_name = f"{tenant.get('first_name', '')} {tenant.get('last_name', '')}" if tenant else "Unknown"
        
        community = Community.get_by_id(payment.get('community_id', ''))
        community_name = community.get('name', 'Unknown') if community else "Unknown"
        
        writer.writerow([
            payment.get('_id', ''),
            payment.get('tenant_id', ''),
            tenant_name,
            community_name,
            payment.get('apartment_id', ''),
            payment.get('amount', ''),
            payment.get('status', ''),
            payment.get('payment_date', '').strftime('%Y-%m-%d') if payment.get('payment_date') else ''
        ])
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=payments.csv'
    
    return response

@apartment.route('/admin_revenue_summary', methods=['GET'])
@login_required
def admin_revenue_summary():
    if session["tenant_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_home'))
    
    # Get filter parameters
    community_id = request.args.get('community_id')
    period = request.args.get('period', 'monthly')  # Default to monthly
    
    # Get revenue summary
    summary = Payment.get_revenue_summary(community_id, period)
    
    # Get all communities for the filter dropdown
    communities = Community.get_all()
    
    return render_template('admin/revenue_summary.html',
                          summary=summary,
                          communities=communities,
                          selected_community=community_id,
                          selected_period=period)
