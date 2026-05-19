from datetime import date
from decimal import Decimal
from secrets import token_urlsafe
from time import monotonic
from urllib.parse import parse_qs

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.auth import ROLE_LABELS, get_current_user, has_permission, require_permission, visible_menu
from app.bootstrap import seed_database
from app.config import Settings, get_settings
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
from app.security import hash_password, validate_password_strength, verify_password
from app.services import StockError, create_payment_charge, money, register_completed_service, register_purchase, register_sale_items


settings = get_settings()
app = FastAPI(title="Banca Moderna")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
login_failures: dict[str, list[float]] = {}


def get_csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    if request.method == "POST":
        content_type = request.headers.get("content-type", "")
        if not content_type.startswith("application/x-www-form-urlencoded"):
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "status_code": 415, "detail": "Tipo de formulario nao suportado."},
                status_code=415,
            )
        body = await request.body()
        if len(body) > settings.csrf_max_body_bytes:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "status_code": 413, "detail": "Formulario muito grande."},
                status_code=413,
            )
        parsed_form = parse_qs(body.decode(), keep_blank_values=True)
        submitted_token = (parsed_form.get("csrf_token") or [None])[0]
        session_token = request.session.get("csrf_token")
        if not session_token or submitted_token != session_token:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "status_code": 403, "detail": "Token de seguranca invalido. Recarregue a pagina e tente novamente."},
                status_code=403,
            )

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive
    return await call_next(request)


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.app_secret_key,
    same_site="lax",
    https_only=settings.secure_cookies,
)


def login_rate_key(request: Request, email: str) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}:{email.strip().lower()}"


def too_many_login_attempts(request: Request, email: str, app_settings: Settings = settings) -> bool:
    now = monotonic()
    key = login_rate_key(request, email)
    window_start = now - app_settings.login_rate_limit_window_seconds
    attempts = [attempt for attempt in login_failures.get(key, []) if attempt >= window_start]
    login_failures[key] = attempts
    return len(attempts) >= app_settings.login_rate_limit_attempts


def record_login_failure(request: Request, email: str, app_settings: Settings = settings) -> None:
    key = login_rate_key(request, email)
    now = monotonic()
    window_start = now - app_settings.login_rate_limit_window_seconds
    attempts = [attempt for attempt in login_failures.get(key, []) if attempt >= window_start]
    attempts.append(now)
    login_failures[key] = attempts


def clear_login_failures(request: Request, email: str) -> None:
    login_failures.pop(login_rate_key(request, email), None)


def commit_or_error(db: Session, message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise StockError(message) from exc


def rollback_error(db: Session, exc: Exception) -> str:
    db.rollback()
    return str(exc)


def issue_invoice_with_retry(db: Session, sale_id: int, attempts: int = 3) -> FiscalInvoice:
    for attempt in range(attempts):
        sale = db.get(Sale, sale_id)
        if sale is None:
            raise HTTPException(status_code=404, detail="Venda nao encontrada.")
        try:
            invoice = issue_invoice(db, sale)
            db.commit()
            db.refresh(invoice)
            return invoice
        except IntegrityError as exc:
            db.rollback()
            if attempt == attempts - 1:
                raise StockError("Nao foi possivel emitir a nota. Tente novamente.") from exc
    raise StockError("Nao foi possivel emitir a nota. Tente novamente.")


def issue_service_invoice_with_retry(db: Session, service_id: int, attempts: int = 3) -> ServiceInvoice:
    for attempt in range(attempts):
        service_order = db.get(ServiceOrder, service_id)
        if service_order is None:
            raise HTTPException(status_code=404, detail="Servico nao encontrado.")
        try:
            invoice = issue_service_invoice(db, service_order)
            db.commit()
            db.refresh(invoice)
            return invoice
        except IntegrityError as exc:
            db.rollback()
            if attempt == attempts - 1:
                raise StockError("Nao foi possivel emitir a nota de servico. Tente novamente.") from exc
    raise StockError("Nao foi possivel emitir a nota de servico. Tente novamente.")


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
        "csrf_token": get_csrf_token(request),
    }
    context.update(extra)
    return context


def products_context(request: Request, current_user: User, db: Session, error: str | None = None):
    return template_context(
        request,
        current_user,
        products=db.query(Product).order_by(Product.name).all(),
        categories=db.query(Category).order_by(Category.name).all(),
        suppliers=db.query(Supplier).order_by(Supplier.name).all(),
        kinds=ProductKind,
        error=error,
    )


def customers_context(request: Request, current_user: User, db: Session, error: str | None = None):
    return template_context(
        request,
        current_user,
        customers=db.query(Customer).order_by(Customer.name).all(),
        error=error,
    )


def suppliers_context(request: Request, current_user: User, db: Session, error: str | None = None):
    return template_context(
        request,
        current_user,
        suppliers=db.query(Supplier).order_by(Supplier.name).all(),
        error=error,
    )


def users_context(request: Request, current_user: User, db: Session, error: str | None = None):
    return template_context(
        request,
        current_user,
        users=db.query(User).order_by(User.name).all(),
        roles=ROLE_LABELS,
        error=error,
    )


@app.get("/login")
def login_form(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if user_id and db.get(User, user_id):
        return redirect("/")
    return templates.TemplateResponse("login.html", {"request": request, "error": None, "csrf_token": get_csrf_token(request)})


@app.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    if too_many_login_attempts(request, email):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Muitas tentativas de login. Aguarde alguns minutos e tente novamente.", "csrf_token": get_csrf_token(request)},
            status_code=429,
        )
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if user is None or not user.active or not verify_password(password, user.password_hash):
        record_login_failure(request, email)
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "E-mail ou senha invalidos.", "csrf_token": get_csrf_token(request)},
            status_code=400,
        )

    clear_login_failures(request, email)
    csrf_token = get_csrf_token(request)
    request.session.clear()
    request.session["user_id"] = user.id
    request.session["csrf_token"] = csrf_token
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
    return templates.TemplateResponse(
        "products.html",
        products_context(request, current_user, db),
    )


@app.post("/produtos")
def create_product(
    request: Request,
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
    try:
        if min_quantity < 0 or quantity_on_hand < 0:
            raise StockError("Estoque inicial e estoque minimo nao podem ser negativos.")
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
        if not product.sku or not product.name:
            raise StockError("SKU e nome sao obrigatorios.")
        if product.sale_price < 0 or product.cost_price < 0:
            raise StockError("Precos nao podem ser negativos.")
        db.add(product)
        commit_or_error(db, "Ja existe produto com este SKU ou codigo de barras.")
    except StockError as exc:
        error = rollback_error(db, exc)
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
                error=error,
            ),
            status_code=400,
        )
    return redirect("/produtos")


@app.post("/produtos/{product_id}/editar")
def update_product(
    request: Request,
    product_id: int,
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
    try:
        product = db.get(Product, product_id)
        if product is None:
            raise StockError("Produto nao encontrado.")
        if min_quantity < 0 or quantity_on_hand < 0:
            raise StockError("Saldo e estoque minimo nao podem ser negativos.")
        product.sku = sku.strip()
        product.barcode = barcode.strip() if barcode else None
        product.name = name.strip()
        product.kind = kind
        product.sale_price = money(sale_price)
        product.cost_price = money(cost_price)
        product.min_quantity = min_quantity
        product.quantity_on_hand = quantity_on_hand
        product.category_id = int(category_id) if category_id else None
        product.supplier_id = int(supplier_id) if supplier_id else None
        product.origin_country = origin_country.strip() or "Brasil"
        if not product.sku or not product.name:
            raise StockError("SKU e nome sao obrigatorios.")
        if product.sale_price < 0 or product.cost_price < 0:
            raise StockError("Precos nao podem ser negativos.")
        commit_or_error(db, "Ja existe produto com este SKU ou codigo de barras.")
    except (StockError, ValueError) as exc:
        return templates.TemplateResponse(
            "products.html",
            products_context(request, current_user, db, rollback_error(db, exc)),
            status_code=400,
        )
    return redirect("/produtos")


@app.get("/clientes")
def customers(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customers.view")),
):
    return templates.TemplateResponse("customers.html", customers_context(request, current_user, db))


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
    customer_name = name.strip()
    if not customer_name:
        raise HTTPException(status_code=400, detail="Nome do cliente e obrigatorio.")
    db.add(Customer(name=customer_name, phone=phone, email=email, document=document, notes=notes))
    db.commit()
    return redirect("/clientes")


@app.post("/clientes/{customer_id}/editar")
def update_customer(
    request: Request,
    customer_id: int,
    name: str = Form(...),
    phone: str | None = Form(None),
    email: str | None = Form(None),
    document: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customers.create")),
):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado.")
    customer_name = name.strip()
    if not customer_name:
        return templates.TemplateResponse(
            "customers.html",
            customers_context(request, current_user, db, "Nome do cliente e obrigatorio."),
            status_code=400,
        )
    customer.name = customer_name
    customer.phone = phone
    customer.email = email
    customer.document = document
    customer.notes = notes
    db.commit()
    return redirect("/clientes")


@app.get("/fornecedores")
def suppliers(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("suppliers.view")),
):
    return templates.TemplateResponse("suppliers.html", suppliers_context(request, current_user, db))


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
    supplier_name = name.strip()
    if not supplier_name:
        raise HTTPException(status_code=400, detail="Nome do fornecedor e obrigatorio.")
    db.add(
        Supplier(
            name=supplier_name,
            country=country.strip() or "Brasil",
            currency=currency.strip().upper() or "BRL",
            phone=phone,
            email=email,
            document=document,
        )
    )
    db.commit()
    return redirect("/fornecedores")


@app.post("/fornecedores/{supplier_id}/editar")
def update_supplier(
    request: Request,
    supplier_id: int,
    name: str = Form(...),
    country: str = Form("Brasil"),
    currency: str = Form("BRL"),
    phone: str | None = Form(None),
    email: str | None = Form(None),
    document: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("suppliers.create")),
):
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Fornecedor nao encontrado.")
    supplier_name = name.strip()
    if not supplier_name:
        return templates.TemplateResponse(
            "suppliers.html",
            suppliers_context(request, current_user, db, "Nome do fornecedor e obrigatorio."),
            status_code=400,
        )
    supplier.name = supplier_name
    supplier.country = country.strip() or "Brasil"
    supplier.currency = currency.strip().upper() or "BRL"
    supplier.phone = phone
    supplier.email = email
    supplier.document = document
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
        purchase = register_purchase(db, supplier_id, product_id, quantity, money(unit_cost), document_number)
        commit_or_error(db, "Nao foi possivel registrar a compra.")
        db.refresh(purchase)
    except (StockError, ValueError) as exc:
        error = rollback_error(db, exc)
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
                error=error,
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
        commit_or_error(db, "Nao foi possivel finalizar a venda.")
        db.refresh(sale)
    except (StockError, ValueError) as exc:
        error = rollback_error(db, exc)
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
                error=error,
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
    try:
        invoice = issue_invoice_with_retry(db, sale_id)
    except StockError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
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
        service_order = register_completed_service(
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
        commit_or_error(db, "Nao foi possivel registrar o servico.")
        db.refresh(service_order)
    except (StockError, ValueError) as exc:
        error = rollback_error(db, exc)
        rows = db.query(ServiceOrder).order_by(desc(ServiceOrder.created_at)).all()
        customers = db.query(Customer).order_by(Customer.name).all()
        return templates.TemplateResponse(
            "services.html",
            template_context(request, current_user, services=rows, customers=customers, error=error),
            status_code=400,
        )
    return redirect("/servicos")


@app.post("/servicos/{service_id}/emitir-nf")
def emit_service_invoice(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("services.create")),
):
    try:
        invoice = issue_service_invoice_with_retry(db, service_id)
    except StockError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
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
    return templates.TemplateResponse(
        "users.html",
        users_context(request, current_user, db),
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
    if not name.strip():
        raise HTTPException(status_code=400, detail="Nome e obrigatorio.")
    try:
        validate_password_strength(password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
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
    return redirect("/usuarios")


@app.post("/usuarios/{user_id}/editar")
def update_user(
    request: Request,
    user_id: int,
    name: str = Form(...),
    email: str = Form(...),
    password: str | None = Form(None),
    role: str = Form(...),
    active: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.manage")),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado.")
    normalized_email = email.strip().lower()
    if role not in ROLE_LABELS:
        return templates.TemplateResponse(
            "users.html",
            users_context(request, current_user, db, "Perfil de acesso invalido."),
            status_code=400,
        )
    if not name.strip():
        return templates.TemplateResponse(
            "users.html",
            users_context(request, current_user, db, "Nome e obrigatorio."),
            status_code=400,
        )
    if password:
        try:
            validate_password_strength(password)
        except ValueError as exc:
            return templates.TemplateResponse(
                "users.html",
                users_context(request, current_user, db, str(exc)),
                status_code=400,
            )
        user.password_hash = hash_password(password)
    user.name = name.strip()
    user.email = normalized_email
    if user.id != current_user.id:
        user.role = role
        user.active = active == "on"
    else:
        user.active = True
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            "users.html",
            users_context(request, current_user, db, "Ja existe um usuario com este e-mail."),
            status_code=400,
        )
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
