import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import { calculateLicenseStatus } from '@/lib/utils';

export async function GET(req: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { searchParams } = new URL(req.url);
    const companyId = searchParams.get('companyId');
    const status = searchParams.get('status');

    let whereClause: any = {};

    // Client users can only see their company's licenses
    if (session.user.role === 'CLIENT' && session.user.companyId) {
      whereClause.companyId = session.user.companyId;
    } else if (companyId) {
      whereClause.companyId = companyId;
    }

    if (status) {
      whereClause.status = status;
    }

    const licenses = await prisma.license.findMany({
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
      orderBy: {
        expirationDate: 'asc',
      },
    });

    return NextResponse.json(licenses);
  } catch (error) {
    console.error('Error fetching licenses:', error);
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
      licenseType,
      issuingBody,
      issueDate,
      expirationDate,
      documentPath,
      notes,
    } = body;

    if (!companyId || !licenseType || !issuingBody || !issueDate || !expirationDate) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    const status = calculateLicenseStatus(new Date(expirationDate));

    const license = await prisma.license.create({
      data: {
        companyId,
        licenseType,
        issuingBody,
        issueDate: new Date(issueDate),
        expirationDate: new Date(expirationDate),
        status,
        documentPath: documentPath || null,
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
        entityType: 'License',
        entityId: license.id,
        details: `Created license: ${license.licenseType} for ${license.company.name}`,
      },
    });

    return NextResponse.json(license);
  } catch (error) {
    console.error('Error creating license:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
