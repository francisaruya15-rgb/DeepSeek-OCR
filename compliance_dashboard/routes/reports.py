from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, date
from models import db, License, Remittance, Company, AuditLog
from utils.export import generate_pdf_report, generate_excel_report
import io

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')
@login_required
def reports_page():
    """Reports and export page"""
    companies = Company.query.order_by(Company.name).all() if not current_user.is_client() else [current_user.company]
    license_types = db.session.query(License.license_type).distinct().all()
    license_types = [lt[0] for lt in license_types]
    
    return render_template('reports/index.html', companies=companies, license_types=license_types)


@reports_bp.route('/export/pdf')
@login_required
def export_pdf():
    """Export licenses to PDF"""
    try:
        # Get filter parameters
        company_id = request.args.get('company_id', type=int)
        license_type = request.args.get('license_type')
        status = request.args.get('status')
        
        # Base query
        if current_user.is_client():
            query = License.query.filter_by(company_id=current_user.company_id)
        else:
            query = License.query
        
        # Apply filters
        if company_id:
            query = query.filter_by(company_id=company_id)
        if license_type:
            query = query.filter_by(license_type=license_type)
        if status:
            query = query.filter_by(status=status)
        
        licenses = query.order_by(License.expiry_date).all()
        
        # Generate PDF
        pdf_buffer = generate_pdf_report(licenses, 'licenses')
        
        # Log action
        from auth import log_action
        log_action('exported', 'license', 0, 'Exported licenses to PDF')
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'licenses_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}', 'danger')
        return redirect(url_for('reports.reports_page'))


@reports_bp.route('/export/excel')
@login_required
def export_excel():
    """Export licenses to Excel"""
    try:
        # Get filter parameters
        company_id = request.args.get('company_id', type=int)
        license_type = request.args.get('license_type')
        status = request.args.get('status')
        
        # Base query
        if current_user.is_client():
            query = License.query.filter_by(company_id=current_user.company_id)
        else:
            query = License.query
        
        # Apply filters
        if company_id:
            query = query.filter_by(company_id=company_id)
        if license_type:
            query = query.filter_by(license_type=license_type)
        if status:
            query = query.filter_by(status=status)
        
        licenses = query.order_by(License.expiry_date).all()
        
        # Generate Excel
        excel_buffer = generate_excel_report(licenses, 'licenses')
        
        # Log action
        from auth import log_action
        log_action('exported', 'license', 0, 'Exported licenses to Excel')
        
        return send_file(
            excel_buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'licenses_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
    except Exception as e:
        flash(f'Error generating Excel: {str(e)}', 'danger')
        return redirect(url_for('reports.reports_page'))


@reports_bp.route('/audit-log')
@login_required
def audit_log():
    """View audit log"""
    # Only admin and compliance officers can view full audit log
    if current_user.is_client():
        flash('You do not have permission to view the audit log.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    query = AuditLog.query.order_by(AuditLog.timestamp.desc())
    
    # Apply filters
    user_id = request.args.get('user_id', type=int)
    action = request.args.get('action')
    entity_type = request.args.get('entity_type')
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    if action:
        query = query.filter_by(action=action)
    if entity_type:
        query = query.filter_by(entity_type=entity_type)
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items
    
    return render_template('reports/audit_log.html', logs=logs, pagination=pagination)
