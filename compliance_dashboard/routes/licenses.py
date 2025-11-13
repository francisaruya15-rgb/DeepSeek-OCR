from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from models import db, License, Company
from auth import log_action, admin_required, compliance_officer_required
from utils.file_handler import allowed_file, save_upload_file

licenses_bp = Blueprint('licenses', __name__, url_prefix='/licenses')

@licenses_bp.route('/')
@login_required
def list_licenses():
    """List all licenses with filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Base query based on user role
    if current_user.is_client():
        query = License.query.filter_by(company_id=current_user.company_id)
    else:
        query = License.query
    
    # Apply filters
    company_id = request.args.get('company_id', type=int)
    license_type = request.args.get('license_type')
    status = request.args.get('status')
    
    if company_id:
        query = query.filter_by(company_id=company_id)
    if license_type:
        query = query.filter_by(license_type=license_type)
    if status:
        query = query.filter_by(status=status)
    
    # Order by expiry date
    query = query.order_by(License.expiry_date.asc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    licenses = pagination.items
    
    # Get companies for filter dropdown
    if current_user.is_client():
        companies = [current_user.company]
    else:
        companies = Company.query.order_by(Company.name).all()
    
    # Get unique license types
    license_types = db.session.query(License.license_type).distinct().all()
    license_types = [lt[0] for lt in license_types]
    
    return render_template('licenses/list.html',
                         licenses=licenses,
                         pagination=pagination,
                         companies=companies,
                         license_types=license_types)


@licenses_bp.route('/create', methods=['GET', 'POST'])
@compliance_officer_required
def create_license():
    """Create new license"""
    if request.method == 'POST':
        try:
            company_id = request.form.get('company_id', type=int)
            license_type = request.form.get('license_type', '').strip()
            issuing_body = request.form.get('issuing_body', '').strip()
            issue_date = datetime.strptime(request.form.get('issue_date'), '%Y-%m-%d').date()
            expiry_date = datetime.strptime(request.form.get('expiry_date'), '%Y-%m-%d').date()
            notes = request.form.get('notes', '').strip()
            
            # Validate required fields
            if not all([company_id, license_type, issuing_body, issue_date, expiry_date]):
                flash('Please fill in all required fields.', 'danger')
                return redirect(url_for('licenses.create_license'))
            
            # Handle file upload
            document_path = None
            if 'document' in request.files:
                file = request.files['document']
                if file and file.filename:
                    document_path = save_upload_file(file, 'licenses')
            
            # Create license
            license = License(
                company_id=company_id,
                license_type=license_type,
                issuing_body=issuing_body,
                issue_date=issue_date,
                expiry_date=expiry_date,
                notes=notes,
                document_path=document_path,
                created_by=current_user.id
            )
            license.update_status()
            
            db.session.add(license)
            db.session.commit()
            
            log_action('created', 'license', license.id, f'Created license {license_type} for company {company_id}')
            flash('License created successfully.', 'success')
            return redirect(url_for('licenses.list_licenses'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating license: {str(e)}', 'danger')
    
    # Get companies for dropdown
    companies = Company.query.order_by(Company.name).all()
    return render_template('licenses/create.html', companies=companies)


@licenses_bp.route('/<int:id>')
@login_required
def view_license(id):
    """View license details"""
    license = License.query.get_or_404(id)
    
    # Check permissions
    if current_user.is_client() and license.company_id != current_user.company_id:
        flash('You do not have permission to view this license.', 'danger')
        return redirect(url_for('licenses.list_licenses'))
    
    log_action('viewed', 'license', license.id, f'Viewed license {license.license_type}')
    return render_template('licenses/view.html', license=license)


@licenses_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@compliance_officer_required
def edit_license(id):
    """Edit license"""
    license = License.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            license.company_id = request.form.get('company_id', type=int)
            license.license_type = request.form.get('license_type', '').strip()
            license.issuing_body = request.form.get('issuing_body', '').strip()
            license.issue_date = datetime.strptime(request.form.get('issue_date'), '%Y-%m-%d').date()
            license.expiry_date = datetime.strptime(request.form.get('expiry_date'), '%Y-%m-%d').date()
            license.notes = request.form.get('notes', '').strip()
            
            # Handle file upload
            if 'document' in request.files:
                file = request.files['document']
                if file and file.filename:
                    document_path = save_upload_file(file, 'licenses')
                    license.document_path = document_path
            
            license.update_status()
            db.session.commit()
            
            log_action('updated', 'license', license.id, f'Updated license {license.license_type}')
            flash('License updated successfully.', 'success')
            return redirect(url_for('licenses.view_license', id=license.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating license: {str(e)}', 'danger')
    
    companies = Company.query.order_by(Company.name).all()
    return render_template('licenses/edit.html', license=license, companies=companies)


@licenses_bp.route('/<int:id>/delete', methods=['POST'])
@admin_required
def delete_license(id):
    """Delete license (admin only)"""
    license = License.query.get_or_404(id)
    
    try:
        log_action('deleted', 'license', license.id, f'Deleted license {license.license_type}')
        db.session.delete(license)
        db.session.commit()
        flash('License deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting license: {str(e)}', 'danger')
    
    return redirect(url_for('licenses.list_licenses'))
