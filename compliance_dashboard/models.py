from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication and authorization"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='client')  # admin, compliance_officer, client
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    company = db.relationship('Company', foreign_keys=[company_id], backref='users')
    created_companies = db.relationship('Company', foreign_keys='Company.created_by', backref='creator')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'
    
    def is_compliance_officer(self):
        """Check if user is compliance officer"""
        return self.role == 'compliance_officer'
    
    def is_client(self):
        """Check if user is client"""
        return self.role == 'client'
    
    def can_edit(self):
        """Check if user can edit records"""
        return self.role in ['admin', 'compliance_officer']
    
    def can_delete(self):
        """Check if user can delete records"""
        return self.role == 'admin'
    
    def __repr__(self):
        return f'<User {self.email}>'


class Company(db.Model):
    """Company/Client model"""
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True, index=True)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    licenses = db.relationship('License', backref='company', lazy='dynamic', cascade='all, delete-orphan')
    remittances = db.relationship('Remittance', backref='company', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Company {self.name}>'


class License(db.Model):
    """License and regulatory certification model"""
    __tablename__ = 'licenses'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    license_type = db.Column(db.String(100), nullable=False)  # PENCOM, NSITF, ITF, TAX, BPP, CAC, etc.
    issuing_body = db.Column(db.String(100), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='active')  # active, pending_renewal, expired
    document_path = db.Column(db.String(500))
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def get_status_color(self):
        """Get color indicator based on status"""
        if self.status == 'expired':
            return 'red'
        elif self.status == 'pending_renewal':
            return 'yellow'
        else:
            return 'green'
    
    def update_status(self):
        """Update status based on expiry date"""
        from datetime import date, timedelta
        today = date.today()
        days_until_expiry = (self.expiry_date - today).days
        
        if days_until_expiry < 0:
            self.status = 'expired'
        elif days_until_expiry <= 30:
            self.status = 'pending_renewal'
        else:
            self.status = 'active'
    
    def __repr__(self):
        return f'<License {self.license_type} - {self.company.name}>'


class Remittance(db.Model):
    """Monthly statutory remittance tracker"""
    __tablename__ = 'remittances'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    remittance_type = db.Column(db.String(50), nullable=False)  # PAYE, PENCOM, NHF, NSITF, ITF
    month = db.Column(db.Integer, nullable=False)  # 1-12
    year = db.Column(db.Integer, nullable=False)
    period = db.Column(db.String(20), nullable=False)  # e.g., "2024-01"
    amount = db.Column(db.Numeric(15, 2))
    status = db.Column(db.String(20), nullable=False, default='pending')  # submitted, pending, verified
    proof_path = db.Column(db.String(500))
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def __repr__(self):
        return f'<Remittance {self.remittance_type} - {self.period}>'


class AuditLog(db.Model):
    """Audit log for tracking all actions"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False)  # created, updated, deleted, viewed
    entity_type = db.Column(db.String(50), nullable=False)  # license, remittance, company, user
    entity_id = db.Column(db.Integer, nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<AuditLog {self.action} {self.entity_type} by User {self.user_id}>'
