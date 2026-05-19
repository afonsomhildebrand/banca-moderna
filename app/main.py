from datetime import date
from decimal import Decimal

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.auth import ROLE_LABELS, get_current_user, has_permission, require_permission, visible_menu
from app.bootstrap import seed_database
from app.config import get_settings
from app.database import Base, engine, get_db
from app.invoices import issue_invoice, issue_service_invoice
from app.models import (
    Category,
    Customer,
    FiscalInvoice,
    PaymentCharge,
    Product,
    ProductKind,
    Purchase,
    Sale,
    ServiceInvoice,
    ServiceOrder,
    StockMovement,
    Supplier,
    User,
)
from app.security import hash_password, verify_password
from app.services import StockError, create_payment_charge, money, register_completed_service, register_purchase, register_sale_items


app = FastAPI(title="Banca Moderna")
app.add_middleware(SessionMiddleware, secret_key=get_settings().app_secret_key, same_site="lax")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        seed_database(db)


def redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


def parse_optional_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def template_context(request: Request, current_user: User, **extra):
    context = {
        "request": request,
        "current_user": current_user,
        "menu_items": visible_menu(current_user),
        "can": lambda permission: has_permission(current_user, permission),
        "role_labels": ROLE_LABELS,
    }
    context.update(extra)
    return context


@app.get("/login")
def login_form(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if user_id and db.get(User, user_id):
        return redirect("/")
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if user is None or not user.active or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "E-mail ou senha invalidos."},
            status_code=400,
        )

    request.session.clear()
    request.session["user_id"] = user.id
    return redirect("/" if user.role == "admin" else "/vendas")


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return redirect("/login")


@app.get("/")
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("dashboard.view")),
):
    product_count = db.scalar(select(func.count(Product.id))) or 0
    customer_count = db.scalar(select(func.count(Customer.id))) or 0
    supplier_count = db.scalar(select(func.count(Supplier.id))) or 0
    stock_units = db.scalar(select(func.coalesce(func.sum(Product.quantity_on_hand), 0))) or 0
    sales_total = db.scalar(select(func.coalesce(func.sum(Sale.total), 0))) or Decimal("0")
    purchases_total = db.scalar(select(func.coalesce(func.sum(Purchase.total), 0))) or Decimal("0")
    low_stock = (
        db.query(Product)
        .filter(Product.active.is_(True), Product.quantity_on_hand <= Product.min_quantity)
        .order_by(Product.name)
        .limit(8)
        .all()
    )
    latest_movements = db.query(StockMovement).order_by(desc(StockMovement.created_at)).limit(10).all()
    return templates.TemplateResponse(
        "dashboard.html",
        template_context(
            request,
            current_user,
            product_count=product_count,
            customer_count=customer_count,
            supplier_count=supplier_count,
            stock_units=stock_units,
            sales_total=sales_total,
            purchases_total=purchases_total,
            low_stock=low_stock,
            latest_movements=latest_movements,
        ),
    )


@app.get("/produtos")
def products(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("products.view")),
):
    rows = db.query(Product).order_by(Product.name).all()
    categories = db.query(Category).order_by(Category.name).all()
    suppliers = db.query(Supplier).order_by(Supplier.name).all()
    return templates.TemplateResponse(
        "products.html",
        template_context(
            request,
            current_user,
            products=rows,
            categories=categories,
            suppliers=suppliers,
            kinds=ProductKind,
        ),
    )


@app.post("/produtos")
def create_product(
    sku: str = Form(...),
    name: str = Form(...),
    kind: ProductKind = Form(ProductKind.other),
    sale_price: str = Form("0"),
    cost_price: str = Form("0"),
    min_quantity: int = Form(0),
    quantity_on_hand: int = Form(0),
    category_id: str | None = Form(None),
    supplier_id: str | None = Form(None),
    barcode: str | None = Form(None),
    origin_country: str = Form("Brasil"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("products.create")),
):
    product = Product(
        sku=sku.strip(),
        barcode=barcode.strip() if barcode else None,
        name=name.strip(),
        kind=kind,
        sale_price=money(sale_price),
        cost_price=money(cost_price),
        min_quantity=min_quantity,
        quantity_on_hand=quantity_on_hand,
        category_id=int(category_id) if category_id else None,
        supplier_id=int(supplier_id) if supplier_id else None,
        origin_country=origin_country.strip() or "Brasil",
    )
    db.add(product)
    db.commit()
    return redirect("/produtos")


@app.get("/clientes")
def customers(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customers.view")),
):
    rows = db.query(Customer).order_by(Customer.name).all()
    return templates.TemplateResponse("customers.html", template_context(request, current_user, customers=rows))


@app.post("/clientes")
def create_customer(
    name: str = Form(...),
    phone: str | None = Form(None),
    email: str | None = Form(None),
    document: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customers.create")),
):
    db.add(Customer(name=name.strip(), phone=phone, email=email, document=document, notes=notes))
    db.commit()
    return redirect("/clientes")


@app.get("/fornecedores")
def suppliers(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("suppliers.view")),
):
    rows = db.query(Supplier).order_by(Supplier.name).all()
    return templates.TemplateResponse("suppliers.html", template_context(request, current_user, suppliers=rows))


@app.post("/fornecedores")
def create_supplier(
    name: str = Form(...),
    country: str = Form("Brasil"),
    currency: str = Form("BRL"),
    phone: str | None = Form(None),
    email: str | None = Form(None),
    document: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("suppliers.create")),
):
    db.add(
        Supplier(
            name=name.strip(),
            country=country.strip() or "Brasil",
            currency=currency.strip().upper() or "BRL",
            phone=phone,
            email=email,
            document=document,
        )
    )
    db.commit()
    return redirect("/fornecedores")


@app.get("/compras")
def purchases(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("purchases.view")),
):
    rows = db.query(Purchase).order_by(desc(Purchase.created_at)).all()
    products = db.query(Product).filter(Product.active.is_(True)).order_by(Product.name).all()
    suppliers = db.query(Supplier).order_by(Supplier.name).all()
    return templates.TemplateResponse(
        "purchases.html",
        template_context(
            request,
            current_user,
            purchases=rows,
            products=products,
            suppliers=suppliers,
            error=None,
        ),
    )


@app.post("/compras")
def create_purchase(
    request: Request,
    supplier_id: int = Form(...),
    product_id: int = Form(...),
    quantity: int = Form(...),
    unit_cost: str = Form(...),
    document_number: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("purchases.create")),
):
    try:
        register_purchase(db, supplier_id, product_id, quantity, money(unit_cost), document_number)
    except StockError as exc:
        products = db.query(Product).filter(Product.active.is_(True)).order_by(Product.name).all()
        suppliers = db.query(Supplier).order_by(Supplier.name).all()
        rows = db.query(Purchase).order_by(desc(Purchase.created_at)).all()
        return templates.TemplateResponse(
            "purchases.html",
            template_context(
                request,
                current_user,
                purchases=rows,
                products=products,
                suppliers=suppliers,
                error=str(exc),
            ),
            status_code=400,
        )
    return redirect("/compras")


@app.get("/vendas")
def sales(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("sales.view")),
):
    rows = db.query(Sale).order_by(desc(Sale.created_at)).all()
    products = db.query(Product).filter(Product.active.is_(True)).order_by(Product.name).all()
    customers = db.query(Customer).order_by(Customer.name).all()
    categories = db.query(Category).filter(Category.active.is_(True)).order_by(Category.name).all()
    return templates.TemplateResponse(
        "sales.html",
        template_context(
            request,
            current_user,
            sales=rows,
            products=products,
            customers=customers,
            categories=categories,
            error=None,
        ),
    )


@app.post("/vendas")
def create_sale(
    request: Request,
    product_id: list[int] = Form(...),
    quantity: list[int] = Form(...),
    unit_price: list[str] = Form(...),
    discount: str = Form("0"),
    payment_method: str = Form("dinheiro"),
    customer_id: str | None = Form(None),
    employee_name: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("sales.create")),
):
    try:
        if not (len(product_id) == len(quantity) == len(unit_price)):
            raise StockError("Itens da venda invalidos. Recarregue a tela e tente novamente.")
        items = [
            {"product_id": pid, "quantity": qty, "unit_price": price}
            for pid, qty, price in zip(product_id, quantity, unit_price, strict=True)
        ]
        sale = register_sale_items(
            db,
            items=items,
            discount=money(discount),
            payment_method=payment_method,
            customer_id=int(customer_id) if customer_id else None,
            employee_name=employee_name,
        )
        create_payment_charge(db, sale=sale, amount=sale.total, method=payment_method)
        db.commit()
    except StockError as exc:
        rows = db.query(Sale).order_by(desc(Sale.created_at)).all()
        products = db.query(Product).filter(Product.active.is_(True)).order_by(Product.name).all()
        customers = db.query(Customer).order_by(Customer.name).all()
        categories = db.query(Category).filter(Category.active.is_(True)).order_by(Category.name).all()
        return templates.TemplateResponse(
            "sales.html",
            template_context(
                request,
                current_user,
                sales=rows,
                products=products,
                customers=customers,
                categories=categories,
                error=str(exc),
            ),
            status_code=400,
        )
    return redirect("/vendas")


@app.post("/vendas/{sale_id}/emitir-nf")
def emit_invoice(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("sales.create")),
):
    sale = db.get(Sale, sale_id)
    if sale is None:
        raise HTTPException(status_code=404, detail="Venda nao encontrada.")
    invoice = issue_invoice(db, sale)
    return redirect(f"/notas/{invoice.id}")


@app.get("/notas/{invoice_id}")
def view_invoice(
    request: Request,
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("sales.view")),
):
    invoice = db.get(FiscalInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Nota fiscal nao encontrada.")
    return templates.TemplateResponse(
        "invoice.html",
        template_context(request, current_user, invoice=invoice),
    )


@app.get("/servicos")
def services_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("services.view")),
):
    rows = db.query(ServiceOrder).order_by(desc(ServiceOrder.created_at)).all()
    customers = db.query(Customer).order_by(Customer.name).all()
    return templates.TemplateResponse(
        "services.html",
        template_context(request, current_user, services=rows, customers=customers, error=None),
    )


@app.post("/servicos")
def create_service_order(
    request: Request,
    description: str = Form(...),
    amount: str = Form(...),
    payment_method: str = Form("pix"),
    customer_id: str | None = Form(None),
    employee_name: str | None = Form(None),
    due_date: str | None = Form(None),
    card_brand: str | None = Form(None),
    installments: int = Form(1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("services.create")),
):
    try:
        register_completed_service(
            db,
            description=description,
            amount=money(amount),
            payment_method=payment_method,
            customer_id=int(customer_id) if customer_id else None,
            employee_name=employee_name,
            due_date=parse_optional_date(due_date),
            card_brand=card_brand,
            installments=installments,
        )
    except (StockError, ValueError) as exc:
        rows = db.query(ServiceOrder).order_by(desc(ServiceOrder.created_at)).all()
        customers = db.query(Customer).order_by(Customer.name).all()
        return templates.TemplateResponse(
            "services.html",
            template_context(request, current_user, services=rows, customers=customers, error=str(exc)),
            status_code=400,
        )
    return redirect("/servicos")


@app.post("/servicos/{service_id}/emitir-nf")
def emit_service_invoice(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("services.create")),
):
    service_order = db.get(ServiceOrder, service_id)
    if service_order is None:
        raise HTTPException(status_code=404, detail="Servico nao encontrado.")
    invoice = issue_service_invoice(db, service_order)
    return redirect(f"/notas-servico/{invoice.id}")


@app.get("/notas-servico/{invoice_id}")
def view_service_invoice(
    request: Request,
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("services.view")),
):
    invoice = db.get(ServiceInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Nota fiscal de servico nao encontrada.")
    return templates.TemplateResponse(
        "service_invoice.html",
        template_context(request, current_user, invoice=invoice),
    )


@app.get("/cobrancas/{charge_id}")
def view_charge(
    request: Request,
    charge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    charge = db.get(PaymentCharge, charge_id)
    if charge is None:
        raise HTTPException(status_code=404, detail="Cobranca nao encontrada.")
    if charge.sale_id and not has_permission(current_user, "sales.view"):
        raise HTTPException(status_code=403, detail="Seu usuario nao tem permissao para acessar esta cobranca.")
    if charge.service_order_id and not has_permission(current_user, "services.view"):
        raise HTTPException(status_code=403, detail="Seu usuario nao tem permissao para acessar esta cobranca.")
    return templates.TemplateResponse("charge.html", template_context(request, current_user, charge=charge))


@app.get("/estoque")
def stock(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stock.view")),
):
    products = db.query(Product).order_by(Product.name).all()
    movements = db.query(StockMovement).order_by(desc(StockMovement.created_at)).limit(100).all()
    return templates.TemplateResponse(
        "stock.html",
        template_context(request, current_user, products=products, movements=movements),
    )


@app.get("/usuarios")
def users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.manage")),
):
    rows = db.query(User).order_by(User.name).all()
    return templates.TemplateResponse(
        "users.html",
        template_context(request, current_user, users=rows, roles=ROLE_LABELS, error=None),
    )


@app.post("/usuarios")
def create_user(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    active: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.manage")),
):
    normalized_email = email.strip().lower()
    if role not in ROLE_LABELS:
        raise HTTPException(status_code=400, detail="Perfil de acesso invalido.")
    if db.query(User).filter(User.email == normalized_email).first():
        rows = db.query(User).order_by(User.name).all()
        return templates.TemplateResponse(
            "users.html",
            template_context(
                request,
                current_user,
                users=rows,
                roles=ROLE_LABELS,
                error="Ja existe um usuario com este e-mail.",
            ),
            status_code=400,
        )

    db.add(
        User(
            name=name.strip(),
            email=normalized_email,
            password_hash=hash_password(password),
            role=role,
            active=active == "on",
        )
    )
    db.commit()
    return redirect("/usuarios")


@app.post("/usuarios/{user_id}/alternar-status")
def toggle_user_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.manage")),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado.")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Voce nao pode desativar o proprio usuario.")
    user.active = not user.active
    db.commit()
    return redirect("/usuarios")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 303 and exc.headers and "Location" in exc.headers:
        return RedirectResponse(exc.headers["Location"], status_code=303)
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "status_code": exc.status_code, "detail": exc.detail},
        status_code=exc.status_code,
    )
