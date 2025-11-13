import { differenceInDays } from 'date-fns';

export function getLicenseStatusColor(status: string): string {
  switch (status) {
    case 'ACTIVE':
      return 'bg-green-100 text-green-800';
    case 'PENDING_RENEWAL':
      return 'bg-yellow-100 text-yellow-800';
    case 'EXPIRED':
      return 'bg-red-100 text-red-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

export function getRemittanceStatusColor(status: string): string {
  switch (status) {
    case 'VERIFIED':
      return 'bg-green-100 text-green-800';
    case 'SUBMITTED':
      return 'bg-blue-100 text-blue-800';
    case 'PENDING':
      return 'bg-yellow-100 text-yellow-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

export function calculateLicenseStatus(expirationDate: Date): string {
  const today = new Date();
  const daysUntilExpiry = differenceInDays(expirationDate, today);

  if (daysUntilExpiry < 0) {
    return 'EXPIRED';
  } else if (daysUntilExpiry <= 30) {
    return 'PENDING_RENEWAL';
  } else {
    return 'ACTIVE';
  }
}

export function getDaysUntilExpiry(expirationDate: Date): number {
  return differenceInDays(expirationDate, new Date());
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-NG', {
    style: 'currency',
    currency: 'NGN',
  }).format(amount);
}

export function canDelete(userRole: string): boolean {
  return userRole === 'ADMIN';
}

export function canEdit(userRole: string): boolean {
  return ['ADMIN', 'COMPLIANCE_OFFICER'].includes(userRole);
}

export function canView(userRole: string): boolean {
  return ['ADMIN', 'COMPLIANCE_OFFICER', 'CLIENT'].includes(userRole);
}
