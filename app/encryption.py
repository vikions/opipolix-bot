"""
Модуль для шифрования/расшифрования приватных ключей
"""
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

# Получаем MASTER_KEY из .env
MASTER_KEY = os.environ.get("MASTER_KEY")

if not MASTER_KEY:
    raise ValueError(
        "MASTER_KEY not found in .env file!\n"
        "Run: python generate_master_key.py"
    )

# Создаем cipher для шифрования/расшифрования
cipher = Fernet(MASTER_KEY.encode())


def encrypt_private_key(private_key: str) -> str:
    """
    Шифрует приватный ключ
    
    Args:
        private_key: Приватный ключ в формате '0x...'
    
    Returns:
        Зашифрованная строка
    """
    if not private_key:
        raise ValueError("Private key cannot be empty")
    
    # Шифруем
    encrypted = cipher.encrypt(private_key.encode())
    
    # Возвращаем как строку
    return encrypted.decode()


def decrypt_private_key(encrypted_key: str) -> str:
    """
    Расшифровывает приватный ключ
    
    Args:
        encrypted_key: Зашифрованная строка из БД
    
    Returns:
        Оригинальный приватный ключ '0x...'
    """
    if not encrypted_key:
        raise ValueError("Encrypted key cannot be empty")
    
    # Расшифровываем
    decrypted = cipher.decrypt(encrypted_key.encode())
    
    # Возвращаем как строку
    return decrypted.decode()


# Тестовые функции
def test_encryption():
    """Тест шифрования/расшифрования"""
    print("🧪 Testing encryption module...\n")
    
    # Тестовый приватный ключ
    test_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    
    print(f"Original key: {test_key[:20]}...")
    
    # Шифруем
    encrypted = encrypt_private_key(test_key)
    print(f"Encrypted: {encrypted[:40]}...")
    
    # Расшифровываем
    decrypted = decrypt_private_key(encrypted)
    print(f"Decrypted: {decrypted[:20]}...")
    
    # Проверяем
    if test_key == decrypted:
        print("\n✅ Encryption/Decryption works correctly!")
        return True
    else:
        print("\n❌ Error: Decrypted key doesn't match!")
        return False


if __name__ == "__main__":
    # Запускаем тест
    test_encryption()