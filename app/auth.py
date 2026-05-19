from collections.abc import Callable

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User


ROLE_LABELS = {
    "admin": "Administrador",
    "funcionario": "Funcionario",
}

ROLE_PERMISSIONS = {
    "admin": {"*"},
    "funcionario": {
        "sales.view",
        "sales.create",
    },
}

MENU_ITEMS = [
    {"label": "Dashboard", "href": "/", "permission": "dashboard.view"},
    {"label": "Produtos", "href": "/produtos", "permission": "products.view"},
    {"label": "Clientes", "href": "/clientes", "permission": "customers.view"},
    {"label": "Fornecedores", "href": "/fornecedores", "permission": "suppliers.view"},
    {"label": "Compras", "href": "/compras", "permission": "purchases.view"},
    {"label": "Vendas", "href": "/vendas", "permission": "sales.view"},
    {"label": "Estoque", "href": "/estoque", "permission": "stock.view"},
    {"label": "Usuarios", "href": "/usuarios", "permission": "users.manage"},
]


def has_permission(user: User | None, permission: str) -> bool:
    if user is None:
        return False
    permissions = ROLE_PERMISSIONS.get(user.role, set())
    return "*" in permissions or permission in permissions


def visible_menu(user: User) -> list[dict[str, str]]:
    return [item for item in MENU_ITEMS if has_permission(user, item["permission"])]


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=303, headers={"Location": "/login"})

    user = db.get(User, user_id)
    if user is None or not user.active:
        request.session.clear()
        raise HTTPException(status_code=303, headers={"Location": "/login"})

    return user


def require_permission(permission: str) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user, permission):
            raise HTTPException(status_code=403, detail="Seu usuario nao tem permissao para acessar esta area.")
        return user

    return dependency
