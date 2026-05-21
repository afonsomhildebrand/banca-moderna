from decimal import Decimal
from re import search
from urllib.parse import urlencode

from app.models import Customer, PaymentCharge, Product, ProductKind, Purchase, Sale, ServiceOrder, Supplier, User
from app.security import hash_password


def csrf_token(client, path: str = "/login") -> str:
    response = client.get(path)
    match = search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match is not None
    return match.group(1)


def login(client, email: str = "admin@bancamoderna.local", password: str = "admin12345"):
    return client.post(
        "/login",
        data={"email": email, "password": password, "csrf_token": csrf_token(client)},
        follow_redirects=False,
    )


def post_sale(client, product_id: int, quantity: int, unit_price: str, discount: str = "0", payment_method: str = "pix"):
    body = urlencode(
        {
            "product_id": product_id,
            "quantity": quantity,
            "unit_price": unit_price,
            "discount": discount,
            "payment_method": payment_method,
            "customer_id": "",
            "employee_name": "Admin",
            "csrf_token": csrf_token(client, "/vendas"),
        }
    )
    return client.post(
        "/vendas",
        content=body,
        headers={"content-type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )


def test_login_admin_sees_full_menu(client):
    response = login(client)
    assert response.status_code == 303

    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert "Dashboard" in dashboard.text
    assert "Produtos" in dashboard.text
    assert "Usuarios" in dashboard.text
    assert "Servicos" in dashboard.text


def test_funcionario_only_accesses_sales(client, db_session):
    user = User(
        name="Funcionario Teste",
        email="funcionario@teste.local",
        password_hash=hash_password("teste123"),
        role="funcionario",
        active=True,
    )
    db_session.add(user)
    db_session.commit()

    response = login(client, "funcionario@teste.local", "teste123")
    assert response.status_code == 303
    assert response.headers["location"] == "/vendas"

    sales = client.get("/vendas")
    assert sales.status_code == 200
    assert "Vendas" in sales.text
    assert 'href="/produtos"' not in sales.text
    assert 'href="/usuarios"' not in sales.text
    assert 'href="/servicos"' not in sales.text

    assert client.get("/produtos").status_code == 403
    assert client.get("/servicos").status_code == 403
    assert client.get("/").status_code == 403


def test_sales_page_requires_login(client):
    response = client.get("/vendas", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_admin_can_create_product_and_make_sale(client, db_session):
    login(client)

    product_response = client.post(
        "/produtos",
        data={
            "csrf_token": csrf_token(client, "/produtos"),
            "sku": "FUNC-001",
            "barcode": "7891234567890",
            "name": "Revista Funcional",
            "kind": "editorial",
            "category_id": "",
            "supplier_id": "",
            "origin_country": "Brasil",
            "cost_price": "5.00",
            "sale_price": "12.00",
            "quantity_on_hand": "4",
            "min_quantity": "1",
        },
        follow_redirects=False,
    )
    assert product_response.status_code == 303

    product = db_session.query(Product).filter(Product.sku == "FUNC-001").one()
    assert product.barcode == "7891234567890"

    sales_page = client.get("/vendas")
    assert sales_page.status_code == 200
    assert 'id="barcodeScanner"' in sales_page.text
    assert 'data-barcode="7891234567890"' in sales_page.text
    assert 'value="boleto"' in sales_page.text
    assert 'value="debito"' in sales_page.text
    assert 'value="credito"' in sales_page.text

    sale_response = post_sale(client, product.id, 2, "12.00", "1.00", payment_method="boleto")
    assert sale_response.status_code == 303

    db_session.refresh(product)
    assert product.quantity_on_hand == 2
    charge = db_session.query(PaymentCharge).filter(PaymentCharge.method == "boleto").one()
    assert charge.digitable_line


def test_admin_can_update_product_registration(client, db_session):
    login(client)
    supplier = Supplier(name="Distribuidora Antiga", country="Brasil", currency="BRL")
    product = Product(
        sku="EDIT-001",
        barcode="1112223334445",
        name="Produto Antigo",
        kind=ProductKind.other,
        cost_price=Decimal("2.50"),
        sale_price=Decimal("8.90"),
        quantity_on_hand=3,
        min_quantity=1,
    )
    db_session.add_all([supplier, product])
    db_session.commit()

    response = client.post(
        f"/produtos/{product.id}/editar",
        data={
            "csrf_token": csrf_token(client, "/produtos"),
            "sku": "EDIT-002",
            "barcode": "9998887776665",
            "name": "Produto Atualizado",
            "kind": "editorial",
            "category_id": "",
            "supplier_id": str(supplier.id),
            "origin_country": "Argentina",
            "cost_price": "4.20",
            "sale_price": "12.30",
            "quantity_on_hand": "9",
            "min_quantity": "2",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    db_session.refresh(product)
    assert product.sku == "EDIT-002"
    assert product.barcode == "9998887776665"
    assert product.name == "Produto Atualizado"
    assert product.kind == ProductKind.editorial
    assert product.supplier_id == supplier.id
    assert product.origin_country == "Argentina"
    assert product.cost_price == Decimal("4.20")
    assert product.sale_price == Decimal("12.30")
    assert product.quantity_on_hand == 9
    assert product.min_quantity == 2


def test_admin_can_update_customer_registration(client, db_session):
    login(client)
    customer = Customer(name="Cliente Antigo", phone="11999990000", email="antigo@example.com", document="123")
    db_session.add(customer)
    db_session.commit()

    response = client.post(
        f"/clientes/{customer.id}/editar",
        data={
            "csrf_token": csrf_token(client, "/clientes"),
            "name": "Cliente Atualizado",
            "phone": "11888887777",
            "email": "novo@example.com",
            "document": "456",
            "notes": "Prefere entrega pela manha",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    db_session.refresh(customer)
    assert customer.name == "Cliente Atualizado"
    assert customer.phone == "11888887777"
    assert customer.email == "novo@example.com"
    assert customer.document == "456"
    assert customer.notes == "Prefere entrega pela manha"


def test_admin_can_update_supplier_registration(client, db_session):
    login(client)
    supplier = Supplier(name="Fornecedor Antigo", country="Brasil", currency="BRL", phone="1133332222")
    db_session.add(supplier)
    db_session.commit()

    response = client.post(
        f"/fornecedores/{supplier.id}/editar",
        data={
            "csrf_token": csrf_token(client, "/fornecedores"),
            "name": "Fornecedor Atualizado",
            "document": "99.999.999/0001-99",
            "country": "Portugal",
            "currency": "eur",
            "phone": "+351 210000000",
            "email": "comercial@fornecedor.example",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    db_session.refresh(supplier)
    assert supplier.name == "Fornecedor Atualizado"
    assert supplier.document == "99.999.999/0001-99"
    assert supplier.country == "Portugal"
    assert supplier.currency == "EUR"
    assert supplier.phone == "+351 210000000"
    assert supplier.email == "comercial@fornecedor.example"


def test_admin_can_update_user_registration_and_password(client, db_session):
    login(client)
    user = User(
        name="Operador Antigo",
        email="operador-antigo@example.com",
        password_hash=hash_password("senha-antiga"),
        role="funcionario",
        active=True,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        f"/usuarios/{user.id}/editar",
        data={
            "csrf_token": csrf_token(client, "/usuarios"),
            "name": "Operador Atualizado",
            "email": "operador-novo@example.com",
            "password": "SenhaForte123",
            "role": "admin",
            "active": "on",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    db_session.refresh(user)
    assert user.name == "Operador Atualizado"
    assert user.email == "operador-novo@example.com"
    assert user.role == "admin"
    assert user.active is True

    client.post("/logout", data={"csrf_token": csrf_token(client, "/")}, follow_redirects=False)
    assert login(client, "operador-novo@example.com", "SenhaForte123").status_code == 303


def test_admin_can_update_purchase_and_adjust_stock(client, db_session):
    login(client)
    supplier = Supplier(name="Fornecedor Compra", country="Brasil", currency="BRL")
    product = Product(
        sku="COMPRA-EDIT-001",
        name="Produto Compra",
        kind=ProductKind.other,
        cost_price=Decimal("1.00"),
        sale_price=Decimal("5.00"),
        quantity_on_hand=0,
        min_quantity=1,
    )
    db_session.add_all([supplier, product])
    db_session.commit()

    create_response = client.post(
        "/compras",
        data={
            "csrf_token": csrf_token(client, "/compras"),
            "supplier_id": str(supplier.id),
            "product_id": str(product.id),
            "quantity": "2",
            "unit_cost": "3.00",
            "document_number": "NF-1",
        },
        follow_redirects=False,
    )
    assert create_response.status_code == 303
    purchase = db_session.query(Purchase).filter(Purchase.document_number == "NF-1").one()
    db_session.refresh(product)
    assert product.quantity_on_hand == 2

    update_response = client.post(
        f"/compras/{purchase.id}/editar",
        data={
            "csrf_token": csrf_token(client, "/compras"),
            "supplier_id": str(supplier.id),
            "product_id": str(product.id),
            "quantity": "5",
            "unit_cost": "4.50",
            "document_number": "NF-1-EDIT",
        },
        follow_redirects=False,
    )

    assert update_response.status_code == 303
    db_session.refresh(product)
    db_session.refresh(purchase)
    assert product.quantity_on_hand == 5
    assert product.cost_price == Decimal("4.50")
    assert purchase.document_number == "NF-1-EDIT"
    assert purchase.total == Decimal("22.50")
    assert purchase.items[0].quantity == 5


def test_admin_can_update_sale_payment_and_discount(client, db_session):
    login(client)
    product = Product(
        sku="VENDA-EDIT-001",
        name="Produto Venda Editavel",
        kind=ProductKind.other,
        sale_price=Decimal("10.00"),
        cost_price=Decimal("4.00"),
        quantity_on_hand=5,
        min_quantity=1,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    sale_response = post_sale(client, product.id, 2, "10.00", "0", payment_method="pix")
    assert sale_response.status_code == 303
    sale = db_session.query(Sale).order_by(Sale.id.desc()).first()
    assert sale.total == Decimal("20.00")
    assert sale.charges[0].method == "pix"

    update_response = client.post(
        f"/vendas/{sale.id}/editar",
        data={
            "csrf_token": csrf_token(client, "/vendas"),
            "customer_id": "",
            "employee_name": "Operador Editado",
            "discount": "3.50",
            "payment_method": "dinheiro",
        },
        follow_redirects=False,
    )

    assert update_response.status_code == 303
    db_session.refresh(sale)
    assert sale.employee_name == "Operador Editado"
    assert sale.discount == Decimal("3.50")
    assert sale.total == Decimal("16.50")
    assert sale.payment_method == "dinheiro"
    assert sale.charges == []


def test_admin_can_update_service_and_charge(client, db_session):
    login(client)
    response = client.post(
        "/servicos",
        data={
            "csrf_token": csrf_token(client, "/servicos"),
            "description": "Servico Editavel",
            "amount": "20.00",
            "payment_method": "pix",
            "customer_id": "",
            "employee_name": "Admin",
            "due_date": "",
            "card_brand": "",
            "installments": "1",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    service = db_session.query(ServiceOrder).filter(ServiceOrder.description == "Servico Editavel").one()
    assert service.charges[0].method == "pix"

    update_response = client.post(
        f"/servicos/{service.id}/editar",
        data={
            "csrf_token": csrf_token(client, "/servicos"),
            "description": "Servico Editado",
            "amount": "45.75",
            "payment_method": "boleto",
            "customer_id": "",
            "employee_name": "Tecnico Editado",
            "due_date": "2026-05-20",
            "card_brand": "",
            "installments": "1",
        },
        follow_redirects=False,
    )

    assert update_response.status_code == 303
    db_session.refresh(service)
    assert service.description == "Servico Editado"
    assert service.amount == Decimal("45.75")
    assert service.payment_method == "boleto"
    assert service.employee_name == "Tecnico Editado"
    assert service.charges[0].method == "boleto"
    assert service.charges[0].amount == Decimal("45.75")
    assert service.charges[0].digitable_line


def test_issue_invoice_from_sale_history(client, db_session):
    login(client)
    product = Product(
        sku="NF-FUNC-001",
        name="Produto NF",
        kind=ProductKind.candy,
        sale_price=5,
        cost_price=2,
        quantity_on_hand=3,
        min_quantity=1,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    sale_response = post_sale(client, product.id, 1, "5.00")
    assert sale_response.status_code == 303

    from app.models import Sale

    sale = db_session.query(Sale).order_by(Sale.id.desc()).first()
    response = client.post(
        f"/vendas/{sale.id}/emitir-nf",
        data={"csrf_token": csrf_token(client, "/vendas")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/notas/")

    invoice_page = client.get(response.headers["location"])
    assert invoice_page.status_code == 200
    assert "Nota Fiscal" in invoice_page.text
    assert "Produto NF" in invoice_page.text


def test_admin_can_register_service_issue_invoice_and_charge(client, db_session):
    login(client)

    page = client.get("/servicos")
    assert page.status_code == 200
    assert "Servicos Concluidos" in page.text

    response = client.post(
        "/servicos",
        data={
            "csrf_token": csrf_token(client, "/servicos"),
            "description": "Plastificacao de documento",
            "amount": "35.90",
            "payment_method": "pix",
            "customer_id": "",
            "employee_name": "Admin",
            "due_date": "2026-05-20",
            "card_brand": "",
            "installments": "1",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    service = db_session.query(ServiceOrder).filter(ServiceOrder.description == "Plastificacao de documento").one()
    assert service.amount == Decimal("35.90")
    assert service.charges[0].pix_copy_paste

    charge_page = client.get(f"/cobrancas/{service.charges[0].id}")
    assert charge_page.status_code == 200
    assert "Pix copia e cola" in charge_page.text

    invoice_response = client.post(
        f"/servicos/{service.id}/emitir-nf",
        data={"csrf_token": csrf_token(client, "/servicos")},
        follow_redirects=False,
    )
    assert invoice_response.status_code == 303
    assert invoice_response.headers["location"].startswith("/notas-servico/")

    invoice_page = client.get(invoice_response.headers["location"])
    assert invoice_page.status_code == 200
    assert "Nota Fiscal de Servico" in invoice_page.text
    assert "Plastificacao de documento" in invoice_page.text
