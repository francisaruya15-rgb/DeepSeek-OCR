from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User, Company
from auth import log_action, admin_required

users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.route('/')
@admin_required
def list_users():
    """List all users (admin only)"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = User.query.order_by(User.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items
    
    return render_template('users/list.html', users=users, pagination=pagination)


@users_bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    """Create new user (admin only)"""
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            role = request.form.get('role', 'client').strip()
            company_id = request.form.get('company_id', type=int)
            
            # Validate required fields
            if not all([email, password, role]):
                flash('Please fill in all required fields.', 'danger')
                return redirect(url_for('users.create_user'))
            
            # Check if email already exists
            if User.query.filter_by(email=email).first():
                flash('A user with this email already exists.', 'danger')
                return redirect(url_for('users.create_user'))
            
            # Validate role
            if role not in ['admin', 'compliance_officer', 'client']:
                flash('Invalid role selected.', 'danger')
                return redirect(url_for('users.create_user'))
            
            # Client users must have a company
            if role == 'client' and not company_id:
                flash('Client users must be assigned to a company.', 'danger')
                return redirect(url_for('users.create_user'))
            
            # Create user
            user = User(
                email=email,
                role=role,
                company_id=company_id if role == 'client' else None
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            log_action('created', 'user', user.id, f'Created user {email} with role {role}')
            flash('User created successfully.', 'success')
            return redirect(url_for('users.list_users'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'danger')
    
    companies = Company.query.order_by(Company.name).all()
    return render_template('users/create.html', companies=companies)


@users_bp.route('/<int:id>')
@admin_required
def view_user(id):
    """View user details (admin only)"""
    user = User.query.get_or_404(id)
    return render_template('users/view.html', user=user)


@users_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(id):
    """Edit user (admin only)"""
    user = User.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            user.email = request.form.get('email', '').strip().lower()
            user.role = request.form.get('role', 'client').strip()
            user.company_id = request.form.get('company_id', type=int)
            user.is_active = request.form.get('is_active') == 'on'
            
            # Update password if provided
            new_password = request.form.get('password', '').strip()
            if new_password:
                user.set_password(new_password)
            
            # Validate role
            if user.role not in ['admin', 'compliance_officer', 'client']:
                flash('Invalid role selected.', 'danger')
                return redirect(url_for('users.edit_user', id=id))
            
            # Client users must have a company
            if user.role == 'client' and not user.company_id:
                flash('Client users must be assigned to a company.', 'danger')
                return redirect(url_for('users.edit_user', id=id))
            
            db.session.commit()
            
            log_action('updated', 'user', user.id, f'Updated user {user.email}')
            flash('User updated successfully.', 'success')
            return redirect(url_for('users.view_user', id=user.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'danger')
    
    companies = Company.query.order_by(Company.name).all()
    return render_template('users/edit.html', user=user, companies=companies)


@users_bp.route('/<int:id>/delete', methods=['POST'])
@admin_required
def delete_user(id):
    """Delete user (admin only)"""
    user = User.query.get_or_404(id)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('users.list_users'))
    
    try:
        log_action('deleted', 'user', user.id, f'Deleted user {user.email}')
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
    
    return redirect(url_for('users.list_users'))
