from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Company
from auth import log_action, compliance_officer_required, admin_required

companies_bp = Blueprint('companies', __name__, url_prefix='/companies')

@companies_bp.route('/')
@login_required
def list_companies():
    """List all companies"""
    # Client users can only see their own company
    if current_user.is_client():
        companies = [current_user.company] if current_user.company else []
        pagination = None
    else:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        query = Company.query.order_by(Company.name)
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        companies = pagination.items
    
    return render_template('companies/list.html', companies=companies, pagination=pagination)


@companies_bp.route('/create', methods=['GET', 'POST'])
@compliance_officer_required
def create_company():
    """Create new company"""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            
            # Validate required fields
            if not name:
                flash('Company name is required.', 'danger')
                return redirect(url_for('companies.create_company'))
            
            # Check if company already exists
            if Company.query.filter_by(name=name).first():
                flash('A company with this name already exists.', 'danger')
                return redirect(url_for('companies.create_company'))
            
            # Create company
            company = Company(
                name=name,
                description=description,
                created_by=current_user.id
            )
            
            db.session.add(company)
            db.session.commit()
            
            log_action('created', 'company', company.id, f'Created company {name}')
            flash('Company created successfully.', 'success')
            return redirect(url_for('companies.list_companies'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating company: {str(e)}', 'danger')
    
    return render_template('companies/create.html')


@companies_bp.route('/<int:id>')
@login_required
def view_company(id):
    """View company details"""
    company = Company.query.get_or_404(id)
    
    # Check permissions
    if current_user.is_client() and company.id != current_user.company_id:
        flash('You do not have permission to view this company.', 'danger')
        return redirect(url_for('companies.list_companies'))
    
    # Get company statistics
    total_licenses = company.licenses.count()
    active_licenses = company.licenses.filter_by(status='active').count()
    expired_licenses = company.licenses.filter_by(status='expired').count()
    total_remittances = company.remittances.count()
    
    return render_template('companies/view.html', 
                         company=company,
                         total_licenses=total_licenses,
                         active_licenses=active_licenses,
                         expired_licenses=expired_licenses,
                         total_remittances=total_remittances)


@companies_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@compliance_officer_required
def edit_company(id):
    """Edit company"""
    company = Company.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            company.name = request.form.get('name', '').strip()
            company.description = request.form.get('description', '').strip()
            
            if not company.name:
                flash('Company name is required.', 'danger')
                return redirect(url_for('companies.edit_company', id=id))
            
            db.session.commit()
            
            log_action('updated', 'company', company.id, f'Updated company {company.name}')
            flash('Company updated successfully.', 'success')
            return redirect(url_for('companies.view_company', id=company.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating company: {str(e)}', 'danger')
    
    return render_template('companies/edit.html', company=company)


@companies_bp.route('/<int:id>/delete', methods=['POST'])
@admin_required
def delete_company(id):
    """Delete company (admin only)"""
    company = Company.query.get_or_404(id)
    
    try:
        log_action('deleted', 'company', company.id, f'Deleted company {company.name}')
        db.session.delete(company)
        db.session.commit()
        flash('Company deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting company: {str(e)}', 'danger')
    
    return redirect(url_for('companies.list_companies'))
