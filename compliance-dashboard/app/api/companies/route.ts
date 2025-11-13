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

    const companies = await prisma.company.findMany({
      select: {
        id: true,
        name: true,
        description: true,
        createdAt: true,
      },
      orderBy: {
        name: 'asc',
      },
    });

    return NextResponse.json(companies);
  } catch (error) {
    console.error('Error fetching companies:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session || session.user.role !== 'ADMIN') {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await req.json();
    const { name, description } = body;

    if (!name) {
      return NextResponse.json({ error: 'Company name is required' }, { status: 400 });
    }

    const company = await prisma.company.create({
      data: {
        name,
        description: description || null,
      },
    });

    // Create audit log
    await prisma.auditLog.create({
      data: {
        userId: session.user.id,
        action: 'CREATE',
        entityType: 'Company',
        entityId: company.id,
        details: `Created company: ${company.name}`,
      },
    });

    return NextResponse.json(company);
  } catch (error) {
    console.error('Error creating company:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
