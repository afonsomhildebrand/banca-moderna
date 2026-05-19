from app.models import Product, ProductKind, User
from app.security import hash_password


def login(client, email: str = "admin@bancamoderna.local", password: str = "admin123"):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=False)


def post_sale(client, product_id: int, quantity: int, unit_price: str, discount: str = "0"):
    body = (
        f"product_id={product_id}"
        f"&quantity={quantity}"
        f"&unit_price={unit_price}"
        f"&discount={discount}"
        "&payment_method=pix"
        "&customer_id="
        "&employee_name=Admin"
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

    assert client.get("/produtos").status_code == 403
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

    sale_response = post_sale(client, product.id, 2, "12.00", "1.00")
    assert sale_response.status_code == 303

    db_session.refresh(product)
    assert product.quantity_on_hand == 2


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
    response = client.post(f"/vendas/{sale.id}/emitir-nf", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/notas/")

    invoice_page = client.get(response.headers["location"])
    assert invoice_page.status_code == 200
    assert "Nota Fiscal" in invoice_page.text
    assert "Produto NF" in invoice_page.text
