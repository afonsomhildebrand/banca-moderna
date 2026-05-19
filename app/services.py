from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    Product,
    Purchase,
    PurchaseItem,
    Sale,
    SaleItem,
    StockMovement,
    StockMovementType,
)


class StockError(ValueError):
    pass


def money(value: str | int | float | Decimal | None) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value)).quantize(Decimal("0.01"))


def register_purchase(
    db: Session,
    supplier_id: int,
    product_id: int,
    quantity: int,
    unit_cost: Decimal,
    document_number: str | None = None,
) -> Purchase:
    product = db.get(Product, product_id)
    if product is None:
        raise StockError("Produto nao encontrado.")
    if quantity <= 0:
        raise StockError("A quantidade da compra deve ser maior que zero.")

    total = money(unit_cost * quantity)
    purchase = Purchase(
        supplier_id=supplier_id,
        document_number=document_number,
        total=total,
    )
    purchase.items.append(
        PurchaseItem(
            product_id=product_id,
            quantity=quantity,
            unit_cost=unit_cost,
            total=total,
        )
    )

    product.quantity_on_hand += quantity
    product.cost_price = unit_cost
    movement = StockMovement(
        product=product,
        movement_type=StockMovementType.purchase,
        quantity=quantity,
        unit_cost=unit_cost,
        reference_type="purchase",
        notes="Entrada por compra",
    )
    db.add(movement)
    db.add(purchase)
    db.flush()
    movement.reference_id = purchase.id

    db.commit()
    db.refresh(purchase)
    return purchase


def register_sale(
    db: Session,
    product_id: int,
    quantity: int,
    unit_price: Decimal,
    discount: Decimal,
    payment_method: str,
    customer_id: int | None = None,
    employee_name: str | None = None,
) -> Sale:
    product = db.get(Product, product_id)
    if product is None:
        raise StockError("Produto nao encontrado.")
    if quantity <= 0:
        raise StockError("A quantidade da venda deve ser maior que zero.")
    if product.quantity_on_hand < quantity:
        raise StockError(f"Estoque insuficiente. Saldo atual: {product.quantity_on_hand}.")

    subtotal = money(unit_price * quantity)
    total = money(subtotal - discount)
    if total < 0:
        raise StockError("O desconto nao pode ser maior que o subtotal.")

    sale = Sale(
        customer_id=customer_id,
        employee_name=employee_name,
        subtotal=subtotal,
        discount=discount,
        total=total,
        payment_method=payment_method,
    )
    sale.items.append(
        SaleItem(
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
            discount=discount,
            total=total,
        )
    )

    product.quantity_on_hand -= quantity
    movement = StockMovement(
        product=product,
        movement_type=StockMovementType.sale,
        quantity=-quantity,
        unit_cost=product.cost_price,
        reference_type="sale",
        notes="Saida por venda",
    )
    db.add(movement)
    db.add(sale)
    db.flush()
    movement.reference_id = sale.id

    db.commit()
    db.refresh(sale)
    return sale


def register_sale_items(
    db: Session,
    items: list[dict[str, Decimal | int]],
    discount: Decimal,
    payment_method: str,
    customer_id: int | None = None,
    employee_name: str | None = None,
) -> Sale:
    if not items:
        raise StockError("Inclua pelo menos um item na venda.")

    sale = Sale(
        customer_id=customer_id,
        employee_name=employee_name,
        discount=discount,
        payment_method=payment_method,
    )

    subtotal = Decimal("0")
    products_by_id: dict[int, Product] = {}
    requested_by_product: dict[int, int] = {}

    for item in items:
        product_id = int(item["product_id"])
        requested_by_product[product_id] = requested_by_product.get(product_id, 0) + int(item["quantity"])

    for item in items:
        product_id = int(item["product_id"])
        quantity = int(item["quantity"])
        unit_price = money(item["unit_price"])

        if quantity <= 0:
            raise StockError("Todos os itens devem ter quantidade maior que zero.")

        product = products_by_id.get(product_id) or db.get(Product, product_id)
        if product is None:
            raise StockError("Produto nao encontrado.")
        products_by_id[product_id] = product

        requested_quantity = requested_by_product[product_id]
        if product.quantity_on_hand < requested_quantity:
            raise StockError(f"Estoque insuficiente para {product.name}. Saldo atual: {product.quantity_on_hand}.")

        line_total = money(unit_price * quantity)
        subtotal += line_total
        sale.items.append(
            SaleItem(
                product=product,
                quantity=quantity,
                unit_price=unit_price,
                discount=Decimal("0"),
                total=line_total,
            )
        )

    subtotal = money(subtotal)
    total = money(subtotal - discount)
    if total < 0:
        raise StockError("O desconto nao pode ser maior que o subtotal.")

    sale.subtotal = subtotal
    sale.total = total
    db.add(sale)
    db.flush()

    for sale_item in sale.items:
        product = sale_item.product
        product.quantity_on_hand -= sale_item.quantity
        db.add(
            StockMovement(
                product=product,
                movement_type=StockMovementType.sale,
                quantity=-sale_item.quantity,
                unit_cost=product.cost_price,
                reference_type="sale",
                reference_id=sale.id,
                notes="Saida por venda",
            )
        )

    db.commit()
    db.refresh(sale)
    return sale
