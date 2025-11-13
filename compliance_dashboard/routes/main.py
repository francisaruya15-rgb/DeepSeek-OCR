from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, and_, or_
from datetime import datetime, date, timedelta
from models import db, Company, License, Remittance, AuditLog

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with analytics"""
    today = date.today()
    thirty_days = today + timedelta(days=30)
    
    # Base query for licenses based on user role
    if current_user.is_client():
        license_query = License.query.filter_by(company_id=current_user.company_id)
        remittance_query = Remittance.query.filter_by(company_id=current_user.company_id)
    else:
        license_query = License.query
        remittance_query = Remittance.query
    
    # Update license statuses
    all_licenses = license_query.all()
    for license in all_licenses:
        license.update_status()
    db.session.commit()
    
    # Calculate statistics
    total_licenses = license_query.count()
    active_licenses = license_query.filter_by(status='active').count()
    due_soon_licenses = license_query.filter_by(status='pending_renewal').count()
    expired_licenses = license_query.filter_by(status='expired').count()
    
    # Remittance statistics
    current_month = today.month
    current_year = today.year
    pending_remittances = remittance_query.filter_by(status='pending').count()
    submitted_remittances = remittance_query.filter_by(status='submitted').count()
    verified_remittances = remittance_query.filter_by(status='verified').count()
    
    # Recent licenses expiring soon
    upcoming_expiries = license_query.filter(
        License.expiry_date.between(today, thirty_days)
    ).order_by(License.expiry_date).limit(10).all()
    
    # Recent activity
    if current_user.is_client():
        recent_logs = AuditLog.query.join(License, and_(
            AuditLog.entity_type == 'license',
            AuditLog.entity_id == License.id,
            License.company_id == current_user.company_id
        )).order_by(AuditLog.timestamp.desc()).limit(10).all()
    else:
        recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()
    
    return render_template('dashboard.html',
                         total_licenses=total_licenses,
                         active_licenses=active_licenses,
                         due_soon_licenses=due_soon_licenses,
                         expired_licenses=expired_licenses,
                         pending_remittances=pending_remittances,
                         submitted_remittances=submitted_remittances,
                         verified_remittances=verified_remittances,
                         upcoming_expiries=upcoming_expiries,
                         recent_logs=recent_logs)


@main_bp.route('/api/dashboard-stats')
@login_required
def dashboard_stats():
    """API endpoint for dashboard statistics"""
    today = date.today()
    
    # Base query based on user role
    if current_user.is_client():
        license_query = License.query.filter_by(company_id=current_user.company_id)
    else:
        license_query = License.query
    
    # Get monthly expiry data for chart
    monthly_data = []
    for i in range(6):
        month_start = today.replace(day=1) + timedelta(days=32*i)
        month_start = month_start.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        count = license_query.filter(
            License.expiry_date.between(month_start, month_end)
        ).count()
        
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'count': count
        })
    
    return jsonify({
        'monthly_expiries': monthly_data
    })
