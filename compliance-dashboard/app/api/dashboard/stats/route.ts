import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { prisma } from '@/lib/prisma';

export async function GET(req: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    let whereClause: any = {};

    // Client users can only see their company's data
    if (session.user.role === 'CLIENT' && session.user.companyId) {
      whereClause.companyId = session.user.companyId;
    }

    // Count licenses by status
    const activeLicenses = await prisma.license.count({
      where: { ...whereClause, status: 'ACTIVE' },
    });

    const pendingRenewalLicenses = await prisma.license.count({
      where: { ...whereClause, status: 'PENDING_RENEWAL' },
    });

    const expiredLicenses = await prisma.license.count({
      where: { ...whereClause, status: 'EXPIRED' },
    });

    const totalLicenses = await prisma.license.count({
      where: whereClause,
    });

    // Count remittances by status
    const submittedRemittances = await prisma.remittance.count({
      where: { ...whereClause, status: 'SUBMITTED' },
    });

    const pendingRemittances = await prisma.remittance.count({
      where: { ...whereClause, status: 'PENDING' },
    });

    const verifiedRemittances = await prisma.remittance.count({
      where: { ...whereClause, status: 'VERIFIED' },
    });

    const totalRemittances = await prisma.remittance.count({
      where: whereClause,
    });

    // Get upcoming expiries (next 30 days)
    const thirtyDaysFromNow = new Date();
    thirtyDaysFromNow.setDate(thirtyDaysFromNow.getDate() + 30);

    const upcomingExpiries = await prisma.license.findMany({
      where: {
        ...whereClause,
        expirationDate: {
          gte: new Date(),
          lte: thirtyDaysFromNow,
        },
      },
      include: {
        company: {
          select: {
            name: true,
          },
        },
      },
      orderBy: {
        expirationDate: 'asc',
      },
      take: 10,
    });

    return NextResponse.json({
      licenses: {
        active: activeLicenses,
        pendingRenewal: pendingRenewalLicenses,
        expired: expiredLicenses,
        total: totalLicenses,
      },
      remittances: {
        submitted: submittedRemittances,
        pending: pendingRemittances,
        verified: verifiedRemittances,
        total: totalRemittances,
      },
      upcomingExpiries,
    });
  } catch (error) {
    console.error('Error fetching dashboard stats:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
