from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Category, ProductKind, User
from app.security import hash_password, validate_password_strength, verify_password


DEFAULT_CATEGORIES = [
    ("Jornais", ProductKind.editorial),
    ("Revistas", ProductKind.editorial),
    ("Livros", ProductKind.editorial),
    ("Revistinhas e Gibis", ProductKind.editorial),
    ("Colecoes", ProductKind.collectible),
    ("Albuns", ProductKind.collectible),
    ("Figurinhas e Cartas", ProductKind.collectible),
    ("Jogos", ProductKind.game),
    ("Comidas", ProductKind.food),
    ("Bebidas", ProductKind.drink),
    ("Doces", ProductKind.candy),
    ("Chicletes", ProductKind.gum),
]


def seed_database(db: Session) -> None:
    for name, kind in DEFAULT_CATEGORIES:
        exists = db.query(Category).filter(Category.name == name).first()
        if not exists:
            db.add(Category(name=name, kind=kind))

    settings = get_settings()
    admin_email = settings.initial_admin_email
    admin_password = settings.initial_admin_password
    if admin_email and admin_password:
        validate_password_strength(admin_password)
        admin = db.query(User).filter(User.email == admin_email.strip().lower()).first()
        if not admin:
            db.add(
                User(
                    name="Administrador",
                    email=admin_email.strip().lower(),
                    password_hash=hash_password(admin_password),
                    role="admin",
                )
            )
        elif verify_password("admin123", admin.password_hash):
            admin.password_hash = hash_password(admin_password)

    db.query(User).filter(User.role.in_(["gerente", "vendedor", "estoquista"])).update(
        {User.role: "funcionario"},
        synchronize_session=False,
    )

    db.commit()
