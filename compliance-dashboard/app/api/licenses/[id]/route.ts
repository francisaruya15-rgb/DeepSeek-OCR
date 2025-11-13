import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import { calculateLicenseStatus } from '@/lib/utils';

export async function PUT(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getServerSession(authOptions);

    if (!session || !['ADMIN', 'COMPLIANCE_OFFICER'].includes(session.user.role)) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { id } = params;
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

    const status = calculateLicenseStatus(new Date(expirationDate));

    const license = await prisma.license.update({
      where: { id },
      data: {
        companyId,
        licenseType,
        issuingBody,
        issueDate: new Date(issueDate),
        expirationDate: new Date(expirationDate),
        status,
        documentPath: documentPath || null,
        notes: notes || null,
        updatedById: session.user.id,
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
        action: 'UPDATE',
        entityType: 'License',
        entityId: license.id,
        details: `Updated license: ${license.licenseType} for ${license.company.name}`,
      },
    });

    return NextResponse.json(license);
  } catch (error) {
    console.error('Error updating license:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getServerSession(authOptions);

    if (!session || session.user.role !== 'ADMIN') {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { id } = params;

    const license = await prisma.license.findUnique({
      where: { id },
      include: {
        company: {
          select: {
            name: true,
          },
        },
      },
    });

    if (!license) {
      return NextResponse.json({ error: 'License not found' }, { status: 404 });
    }

    await prisma.license.delete({
      where: { id },
    });

    // Create audit log
    await prisma.auditLog.create({
      data: {
        userId: session.user.id,
        action: 'DELETE',
        entityType: 'License',
        entityId: id,
        details: `Deleted license: ${license.licenseType} for ${license.company.name}`,
      },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error deleting license:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
