from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.models import (
    PaymentCharge,
    Product,
    Purchase,
    PurchaseItem,
    Sale,
    SaleItem,
    ServiceOrder,
    StockMovement,
    StockMovementType,
)


class StockError(ValueError):
    pass


CHARGE_METHODS = {"boleto", "pix", "debito", "credito"}


def money(value: str | int | float | Decimal | None) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    normalized = str(value).strip().replace(",", ".")
    try:
        return Decimal(normalized).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise StockError("Valor monetario invalido.") from exc


def create_payment_charge(
    db: Session,
    *,
    amount: Decimal,
    method: str,
    sale: Sale | None = None,
    service_order: ServiceOrder | None = None,
    due_date=None,
    card_brand: str | None = None,
    installments: int = 1,
) -> PaymentCharge | None:
    if method not in CHARGE_METHODS:
        return None
    if sale is None and service_order is None:
        raise StockError("A cobranca precisa estar vinculada a uma venda ou servico.")

    scope = "VEN" if sale else "SRV"
    prefix = {"boleto": "BOL", "pix": "PIX", "debito": "DEB", "credito": "CRE"}[method]
    reference_id = sale.id if sale else service_order.id
    reference = f"{scope}-{prefix}-{reference_id:06d}"
    charge = PaymentCharge(
        sale=sale,
        service_order=service_order,
        method=method,
        amount=money(amount),
        due_date=due_date,
        reference=reference,
        card_brand=card_brand.strip() if card_brand else None,
        installments=max(1, installments or 1),
    )

    if method == "boleto":
        charge.digitable_line = f"34191.79001 01043.{reference_id:05d} 91020.150008 8 {reference_id:014d}"
        charge.notes = "Boleto interno para controle de cobranca. Nao registrado em banco."
    elif method == "pix":
        charge.pix_copy_paste = f"00020126330014BR.GOV.BCB.PIX0111BANCA-MOD{reference_id:06d}520400005303986540{charge.amount:.2f}5802BR5920BANCA MODERNA6009SAO PAULO62070503***6304"
        charge.notes = "Copia e cola Pix interno para controle de cobranca. Integre a um PSP para cobranca bancaria real."
    elif method == "debito":
        charge.notes = "Cobranca de debito registrada para conciliacao da maquininha."
    elif method == "credito":
        charge.notes = f"Cobranca de credito em {charge.installments} parcela(s) para conciliacao da maquininha."

    db.add(charge)
    return charge


def register_completed_service(
    db: Session,
    *,
    description: str,
    amount: Decimal,
    payment_method: str,
    customer_id: int | None = None,
    employee_name: str | None = None,
    due_date=None,
    card_brand: str | None = None,
    installments: int = 1,
) -> ServiceOrder:
    total = money(amount)
    if total <= 0:
        raise StockError("O valor do servico deve ser maior que zero.")
    if not description.strip():
        raise StockError("Informe a descricao do servico.")

    service_order = ServiceOrder(
        customer_id=customer_id,
        description=description.strip(),
        employee_name=employee_name,
        amount=total,
        payment_method=payment_method,
    )
    db.add(service_order)
    db.flush()
    create_payment_charge(
        db,
        amount=total,
        method=payment_method,
        service_order=service_order,
        due_date=due_date,
        card_brand=card_brand,
        installments=installments,
    )
    return service_order


def register_purchase(
    db: Session,
    supplier_id: int,
    product_id: int,
    quantity: int,
    unit_cost: Decimal,
    document_number: str | None = None,
) -> Purchase:
    product = db.get(Product, product_id, with_for_update=True)
    if product is None:
        raise StockError("Produto nao encontrado.")
    if quantity <= 0:
        raise StockError("A quantidade da compra deve ser maior que zero.")
    unit_cost = money(unit_cost)
    if unit_cost < 0:
        raise StockError("O custo unitario nao pode ser negativo.")

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
    db.flush()

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
    product = db.get(Product, product_id, with_for_update=True)
    if product is None:
        raise StockError("Produto nao encontrado.")
    if quantity <= 0:
        raise StockError("A quantidade da venda deve ser maior que zero.")
    unit_price = money(unit_price)
    discount = money(discount)
    if unit_price < 0:
        raise StockError("O preco unitario nao pode ser negativo.")
    if discount < 0:
        raise StockError("O desconto nao pode ser negativo.")
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
    db.flush()

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

    discount = money(discount)
    if discount < 0:
        raise StockError("O desconto nao pode ser negativo.")

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
        if unit_price < 0:
            raise StockError("O preco unitario nao pode ser negativo.")

        product = products_by_id.get(product_id) or db.get(Product, product_id, with_for_update=True)
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

    db.flush()
    return sale
