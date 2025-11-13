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

    const { searchParams } = new URL(req.url);
    const companyId = searchParams.get('companyId');
    const status = searchParams.get('status');
    const year = searchParams.get('year');
    const month = searchParams.get('month');

    let whereClause: any = {};

    // Client users can only see their company's remittances
    if (session.user.role === 'CLIENT' && session.user.companyId) {
      whereClause.companyId = session.user.companyId;
    } else if (companyId) {
      whereClause.companyId = companyId;
    }

    if (status) {
      whereClause.status = status;
    }

    if (year) {
      whereClause.year = parseInt(year);
    }

    if (month) {
      whereClause.month = parseInt(month);
    }

    const remittances = await prisma.remittance.findMany({
      where: whereClause,
      include: {
        company: {
          select: {
            id: true,
            name: true,
          },
        },
        createdBy: {
          select: {
            name: true,
            email: true,
          },
        },
      },
      orderBy: [
        { year: 'desc' },
        { month: 'desc' },
      ],
    });

    return NextResponse.json(remittances);
  } catch (error) {
    console.error('Error fetching remittances:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session || !['ADMIN', 'COMPLIANCE_OFFICER'].includes(session.user.role)) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await req.json();
    const {
      companyId,
      remittanceType,
      period,
      month,
      year,
      amount,
      proofPath,
      status,
      notes,
    } = body;

    if (!companyId || !remittanceType || !period || !month || !year) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    const remittance = await prisma.remittance.create({
      data: {
        companyId,
        remittanceType,
        period,
        month: parseInt(month),
        year: parseInt(year),
        amount: amount ? parseFloat(amount) : null,
        proofPath: proofPath || null,
        status: status || 'PENDING',
        notes: notes || null,
        createdById: session.user.id,
      },
      include: {
        company: {
          select: {
            name: true,
          },
        },
      },
    });

    // Create audit log
    await prisma.auditLog.create({
      data: {
        userId: session.user.id,
        action: 'CREATE',
        entityType: 'Remittance',
        entityId: remittance.id,
        details: `Created remittance: ${remittance.remittanceType} for ${remittance.company.name}`,
      },
    });

    return NextResponse.json(remittance);
  } catch (error) {
    console.error('Error creating remittance:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
