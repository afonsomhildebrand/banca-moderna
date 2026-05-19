from decimal import Decimal

import pytest

from app.invoices import issue_invoice
from app.models import Product, ProductKind, Supplier
from app.services import StockError, register_purchase, register_sale_items


def create_supplier(db_session, name="Fornecedor Teste"):
    supplier = Supplier(name=name, country="Brasil", currency="BRL")
    db_session.add(supplier)
    db_session.commit()
    db_session.refresh(supplier)
    return supplier


def create_product(db_session, sku="SKU-TESTE", name="Produto Teste", stock=0, price=Decimal("10.00")):
    product = Product(
        sku=sku,
        name=name,
        kind=ProductKind.editorial,
        sale_price=price,
        cost_price=Decimal("5.00"),
        quantity_on_hand=stock,
        min_quantity=1,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


def test_register_purchase_increases_stock_and_records_total(db_session):
    supplier = create_supplier(db_session)
    product = create_product(db_session, stock=2)

    purchase = register_purchase(
        db_session,
        supplier_id=supplier.id,
        product_id=product.id,
        quantity=5,
        unit_cost=Decimal("4.50"),
        document_number="NF-001",
    )

    db_session.refresh(product)
    assert product.quantity_on_hand == 7
    assert purchase.total == Decimal("22.50")
    assert purchase.items[0].quantity == 5


def test_register_sale_items_decreases_stock_and_calculates_total(db_session):
    product_a = create_product(db_session, sku="A", name="Revista", stock=10, price=Decimal("8.00"))
    product_b = create_product(db_session, sku="B", name="Doce", stock=5, price=Decimal("3.00"))

    sale = register_sale_items(
        db_session,
        items=[
            {"product_id": product_a.id, "quantity": 2, "unit_price": Decimal("8.00")},
            {"product_id": product_b.id, "quantity": 3, "unit_price": Decimal("3.00")},
        ],
        discount=Decimal("1.00"),
        payment_method="pix",
        employee_name="Teste",
    )

    db_session.refresh(product_a)
    db_session.refresh(product_b)
    assert product_a.quantity_on_hand == 8
    assert product_b.quantity_on_hand == 2
    assert sale.subtotal == Decimal("25.00")
    assert sale.discount == Decimal("1.00")
    assert sale.total == Decimal("24.00")
    assert len(sale.items) == 2


def test_register_sale_items_blocks_insufficient_stock(db_session):
    product = create_product(db_session, stock=1)

    with pytest.raises(StockError, match="Estoque insuficiente"):
        register_sale_items(
            db_session,
            items=[{"product_id": product.id, "quantity": 2, "unit_price": Decimal("10.00")}],
            discount=Decimal("0"),
            payment_method="dinheiro",
        )

    db_session.refresh(product)
    assert product.quantity_on_hand == 1


def test_issue_invoice_is_idempotent_for_sale(db_session):
    product = create_product(db_session, stock=3)
    sale = register_sale_items(
        db_session,
        items=[{"product_id": product.id, "quantity": 1, "unit_price": Decimal("10.00")}],
        discount=Decimal("0"),
        payment_method="cartao",
    )

    invoice_a = issue_invoice(db_session, sale)
    invoice_b = issue_invoice(db_session, sale)

    assert invoice_a.id == invoice_b.id
    assert invoice_a.number == 1
    assert invoice_a.access_key.startswith("BM")
