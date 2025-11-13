from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from models import db, Remittance, Company
from auth import log_action, compliance_officer_required
from utils.file_handler import save_upload_file

remittances_bp = Blueprint('remittances', __name__, url_prefix='/remittances')

@remittances_bp.route('/')
@login_required
def list_remittances():
    """List all remittances with filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Base query based on user role
    if current_user.is_client():
        query = Remittance.query.filter_by(company_id=current_user.company_id)
    else:
        query = Remittance.query
    
    # Apply filters
    company_id = request.args.get('company_id', type=int)
    remittance_type = request.args.get('remittance_type')
    status = request.args.get('status')
    year = request.args.get('year', type=int)
    
    if company_id:
        query = query.filter_by(company_id=company_id)
    if remittance_type:
        query = query.filter_by(remittance_type=remittance_type)
    if status:
        query = query.filter_by(status=status)
    if year:
        query = query.filter_by(year=year)
    
    # Order by period descending
    query = query.order_by(Remittance.year.desc(), Remittance.month.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    remittances = pagination.items
    
    # Get companies for filter dropdown
    if current_user.is_client():
        companies = [current_user.company]
    else:
        companies = Company.query.order_by(Company.name).all()
    
    # Get unique remittance types
    remittance_types = db.session.query(Remittance.remittance_type).distinct().all()
    remittance_types = [rt[0] for rt in remittance_types]
    
    # Get years
    years = db.session.query(Remittance.year).distinct().order_by(Remittance.year.desc()).all()
    years = [y[0] for y in years]
    
    return render_template('remittances/list.html',
                         remittances=remittances,
                         pagination=pagination,
                         companies=companies,
                         remittance_types=remittance_types,
                         years=years)


@remittances_bp.route('/create', methods=['GET', 'POST'])
@compliance_officer_required
def create_remittance():
    """Create new remittance"""
    if request.method == 'POST':
        try:
            company_id = request.form.get('company_id', type=int)
            remittance_type = request.form.get('remittance_type', '').strip()
            month = request.form.get('month', type=int)
            year = request.form.get('year', type=int)
            amount = request.form.get('amount', type=float)
            status = request.form.get('status', 'pending').strip()
            notes = request.form.get('notes', '').strip()
            
            # Validate required fields
            if not all([company_id, remittance_type, month, year]):
                flash('Please fill in all required fields.', 'danger')
                return redirect(url_for('remittances.create_remittance'))
            
            # Create period string
            period = f"{year}-{month:02d}"
            
            # Handle file upload
            proof_path = None
            if 'proof' in request.files:
                file = request.files['proof']
                if file and file.filename:
                    proof_path = save_upload_file(file, 'remittances')
            
            # Create remittance
            remittance = Remittance(
                company_id=company_id,
                remittance_type=remittance_type,
                month=month,
                year=year,
                period=period,
                amount=amount,
                status=status,
                notes=notes,
                proof_path=proof_path,
                created_by=current_user.id
            )
            
            db.session.add(remittance)
            db.session.commit()
            
            log_action('created', 'remittance', remittance.id, f'Created remittance {remittance_type} for {period}')
            flash('Remittance created successfully.', 'success')
            return redirect(url_for('remittances.list_remittances'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating remittance: {str(e)}', 'danger')
    
    # Get companies for dropdown
    companies = Company.query.order_by(Company.name).all()
    
    # Common remittance types
    remittance_types = ['PAYE', 'PENCOM', 'NHF', 'NSITF', 'ITF']
    
    return render_template('remittances/create.html', 
                         companies=companies,
                         remittance_types=remittance_types)


@remittances_bp.route('/<int:id>')
@login_required
def view_remittance(id):
    """View remittance details"""
    remittance = Remittance.query.get_or_404(id)
    
    # Check permissions
    if current_user.is_client() and remittance.company_id != current_user.company_id:
        flash('You do not have permission to view this remittance.', 'danger')
        return redirect(url_for('remittances.list_remittances'))
    
    log_action('viewed', 'remittance', remittance.id, f'Viewed remittance {remittance.remittance_type}')
    return render_template('remittances/view.html', remittance=remittance)


@remittances_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@compliance_officer_required
def edit_remittance(id):
    """Edit remittance"""
    remittance = Remittance.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            remittance.company_id = request.form.get('company_id', type=int)
            remittance.remittance_type = request.form.get('remittance_type', '').strip()
            remittance.month = request.form.get('month', type=int)
            remittance.year = request.form.get('year', type=int)
            remittance.period = f"{remittance.year}-{remittance.month:02d}"
            remittance.amount = request.form.get('amount', type=float)
            remittance.status = request.form.get('status', 'pending').strip()
            remittance.notes = request.form.get('notes', '').strip()
            
            # Handle file upload
            if 'proof' in request.files:
                file = request.files['proof']
                if file and file.filename:
                    proof_path = save_upload_file(file, 'remittances')
                    remittance.proof_path = proof_path
            
            db.session.commit()
            
            log_action('updated', 'remittance', remittance.id, f'Updated remittance {remittance.remittance_type}')
            flash('Remittance updated successfully.', 'success')
            return redirect(url_for('remittances.view_remittance', id=remittance.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating remittance: {str(e)}', 'danger')
    
    companies = Company.query.order_by(Company.name).all()
    remittance_types = ['PAYE', 'PENCOM', 'NHF', 'NSITF', 'ITF']
    
    return render_template('remittances/edit.html', 
                         remittance=remittance, 
                         companies=companies,
                         remittance_types=remittance_types)


@remittances_bp.route('/<int:id>/delete', methods=['POST'])
@compliance_officer_required
def delete_remittance(id):
    """Delete remittance"""
    remittance = Remittance.query.get_or_404(id)
    
    # Only admin can delete
    if not current_user.is_admin():
        flash('Only administrators can delete remittances.', 'danger')
        return redirect(url_for('remittances.list_remittances'))
    
    try:
        log_action('deleted', 'remittance', remittance.id, f'Deleted remittance {remittance.remittance_type}')
        db.session.delete(remittance)
        db.session.commit()
        flash('Remittance deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting remittance: {str(e)}', 'danger')
    
    return redirect(url_for('remittances.list_remittances'))
