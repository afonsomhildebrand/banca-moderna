from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
COMMON_PASSWORDS = {"admin123", "password", "senha123", "123456", "12345678", "banca123"}


def validate_password_strength(password: str) -> None:
    if len(password) < 10:
        raise ValueError("A senha deve ter pelo menos 10 caracteres.")
    if password.lower() in COMMON_PASSWORDS:
        raise ValueError("Escolha uma senha menos comum.")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)
