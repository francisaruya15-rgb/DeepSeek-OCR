import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { prisma } from '@/lib/prisma';

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
      remittanceType,
      period,
      month,
      year,
      amount,
      proofPath,
      status,
      notes,
    } = body;

    const remittance = await prisma.remittance.update({
      where: { id },
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
        entityType: 'Remittance',
        entityId: remittance.id,
        details: `Updated remittance: ${remittance.remittanceType} for ${remittance.company.name}`,
      },
    });

    return NextResponse.json(remittance);
  } catch (error) {
    console.error('Error updating remittance:', error);
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

    const remittance = await prisma.remittance.findUnique({
      where: { id },
      include: {
        company: {
          select: {
            name: true,
          },
        },
      },
    });

    if (!remittance) {
      return NextResponse.json({ error: 'Remittance not found' }, { status: 404 });
    }

    await prisma.remittance.delete({
      where: { id },
    });

    // Create audit log
    await prisma.auditLog.create({
      data: {
        userId: session.user.id,
        action: 'DELETE',
        entityType: 'Remittance',
        entityId: id,
        details: `Deleted remittance: ${remittance.remittanceType} for ${remittance.company.name}`,
      },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error deleting remittance:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
