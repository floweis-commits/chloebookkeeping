"""
Report endpoints — list, generate, download.
"""

from datetime import datetime
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from backend.api.deps import get_current_user, get_tenant_permission
from backend.db.database import get_db
from backend.db.models import User, Report, Tenant
from backend.agents.report_generator import ReportGeneratorAgent
from backend.storage.file_store import file_store

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────

class GenerateReportRequest(BaseModel):
    """Request to generate a new report."""
    tenant_id: str
    period_start: datetime
    period_end: datetime
    client_name: Optional[str] = None
    bookkeeper_name: Optional[str] = None


class ReportListResponse(BaseModel):
    """Report metadata for list endpoints."""
    id: str
    title: str
    period_start: datetime
    period_end: datetime
    generated_at: datetime
    file_path: Optional[str]

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────

@router.get("/", response_model=list[ReportListResponse])
async def list_reports(
    tenant_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List generated reports for a tenant.
    If tenant_id not provided, uses the user's primary tenant.
    """
    # Determine which tenant to query
    if tenant_id:
        try:
            tenant_uuid = UUID(tenant_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant_id format",
            )
    else:
        # For now, get first tenant associated with user
        result = await db.execute(
            select(Tenant).limit(1)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            return []
        tenant_uuid = tenant.id

    # Check permissions
    await get_tenant_permission(tenant_uuid, current_user, db, min_level="viewer")

    # Query reports
    result = await db.execute(
        select(Report)
        .where(Report.tenant_id == tenant_uuid)
        .order_by(Report.period_end.desc())
    )
    reports = result.scalars().all()

    return [
        ReportListResponse(
            id=str(r.id),
            title=r.title,
            period_start=r.period_start,
            period_end=r.period_end,
            generated_at=r.generated_at,
            file_path=r.file_path,
        )
        for r in reports
    ]


@router.post("/generate", response_model=dict)
async def generate_report(
    req: GenerateReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger report generation for a given period.
    Pulls data from QuickBooks, generates AI insights, creates PDF.
    """
    # Validate and check permissions
    try:
        tenant_uuid = UUID(req.tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant_id format",
        )

    await get_tenant_permission(tenant_uuid, current_user, db, min_level="editor")

    # Get tenant name for report
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_uuid)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    client_name = req.client_name or tenant.name
    bookkeeper_name = req.bookkeeper_name or current_user.full_name

    try:
        # Generate report
        agent = ReportGeneratorAgent()
        report_result = await agent.generate_report(
            db=db,
            tenant_id=tenant_uuid,
            period_start=req.period_start,
            period_end=req.period_end,
            client_name=client_name,
            bookkeeper_name=bookkeeper_name,
        )

        # Save PDF to storage
        folder_year = req.period_end.strftime("%Y")
        filename = f"Management_Report_{req.period_start.strftime('%Y%m%d')}_{req.period_end.strftime('%Y%m%d')}.pdf"

        file_path = await file_store.save(
            str(tenant_uuid),
            f"{folder_year}/Reports",
            filename,
            report_result['pdf_bytes'],
        )

        # Create Report record in database
        report = Report(
            tenant_id=tenant_uuid,
            title=f"Management Report {req.period_start.strftime('%B %Y')}",
            period_start=req.period_start,
            period_end=req.period_end,
            file_path=file_path,
            data=report_result['report_data'],
            client_name=client_name,
            bookkeeper_name=bookkeeper_name,
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        return {
            "success": True,
            "report_id": str(report.id),
            "title": report.title,
            "file_path": file_path,
            "message": f"Report generated successfully for {client_name}",
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download a report PDF by ID.
    Streams the PDF file to the browser.
    """
    # Parse report_id
    try:
        report_uuid = UUID(report_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid report_id format",
        )

    # Fetch report
    result = await db.execute(
        select(Report).where(Report.id == report_uuid)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    # Check permissions
    await get_tenant_permission(report.tenant_id, current_user, db, min_level="viewer")

    # Read PDF from storage
    if not report.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found",
        )

    try:
        pdf_bytes = await file_store.read(report.file_path)

        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={report.title}.pdf",
            },
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found in storage",
        )
