from datetime import datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FiscalInvoice, Sale, ServiceInvoice, ServiceOrder


def generate_access_key(reference_id: int, number: int, prefix: str = "BM") -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_part = uuid4().hex[:12].upper()
    return f"{prefix}{timestamp}{reference_id:06d}{number:06d}{random_part}"


def issue_invoice(db: Session, sale: Sale) -> FiscalInvoice:
    if sale.invoice:
        return sale.invoice

    next_number = (db.scalar(select(func.coalesce(func.max(FiscalInvoice.number), 0))) or 0) + 1
    invoice = FiscalInvoice(
        sale=sale,
        number=next_number,
        series="1",
        access_key=generate_access_key(sale.id, next_number),
        issuer_name="Banca Moderna",
        notes="Documento interno gerado pelo sistema. Para NF-e/NFC-e oficial, integrar com SEFAZ.",
    )
    db.add(invoice)
    db.flush()
    return invoice


def issue_service_invoice(db: Session, service_order: ServiceOrder) -> ServiceInvoice:
    if service_order.invoice:
        return service_order.invoice

    next_number = (db.scalar(select(func.coalesce(func.max(ServiceInvoice.number), 0))) or 0) + 1
    invoice = ServiceInvoice(
        service_order=service_order,
        number=next_number,
        series="S",
        access_key=generate_access_key(service_order.id, next_number, prefix="BMS"),
        issuer_name="Banca Moderna",
        notes="Documento interno de servico concluido. Para NFS-e oficial, integrar com a prefeitura/ambiente fiscal.",
    )
    db.add(invoice)
    db.flush()
    return invoice
