from sqlalchemy.orm import Session

from app.models import Category, ProductKind, User
from app.security import hash_password


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

    admin = db.query(User).filter(User.email == "admin@bancamoderna.local").first()
    if not admin:
        db.add(
            User(
                name="Administrador",
                email="admin@bancamoderna.local",
                password_hash=hash_password("admin123"),
                role="admin",
            )
        )

    db.query(User).filter(User.role.in_(["gerente", "vendedor", "estoquista"])).update(
        {User.role: "funcionario"},
        synchronize_session=False,
    )

    db.commit()
