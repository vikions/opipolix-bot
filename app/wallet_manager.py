"""
Модуль для управления кошельками пользователей
Создание EOA, деплой Safe через Relayer
"""
import os
from eth_account import Account
from dotenv import load_dotenv
from database import Database
from encryption import encrypt_private_key, decrypt_private_key
from relayer_client import UserRelayerClient, setup_user_for_trading

# Загружаем переменные окружения
load_dotenv()

# Включаем генерацию случайных ключей
Account.enable_unaudited_hdwallet_features()


class WalletManager:
    """Менеджер кошельков с интеграцией Relayer"""
    
    def __init__(self):
        self.db = Database()
    
    def create_wallet_for_user(self, telegram_id: int) -> dict:
        """
        Создает новый кошелек для пользователя
        
        Returns:
            dict: {
                'telegram_id': int,
                'eoa_address': str,
                'safe_address': str (будет None до деплоя)
            }
        """
        print(f"🔑 Creating wallet for user {telegram_id}...")
        
        # Проверяем, есть ли уже кошелек
        existing_wallet = self.db.get_wallet(telegram_id)
        if existing_wallet:
            print(f"⚠️  Wallet already exists for user {telegram_id}")
            return {
                'telegram_id': telegram_id,
                'eoa_address': existing_wallet['eoa_address'],
                'safe_address': existing_wallet['safe_address']
            }
        
        # 1. Генерируем новый EOA кошелек
        account = Account.create()
        eoa_address = account.address
        eoa_private_key = account.key.hex()  # 0x...
        
        print(f"✅ Generated EOA: {eoa_address}")
        
        # 2. Шифруем приватный ключ
        encrypted_key = encrypt_private_key(eoa_private_key)
        print(f"✅ Private key encrypted")
        
        # 3. Сохраняем в БД (Safe адрес пока None)
        success = self.db.create_wallet(
            telegram_id=telegram_id,
            eoa_address=eoa_address,
            eoa_private_key=encrypted_key,
            safe_address=None
        )
        
        if success:
            print(f"✅ Wallet saved to database")
            return {
                'telegram_id': telegram_id,
                'eoa_address': eoa_address,
                'safe_address': None
            }
        else:
            raise Exception("Failed to save wallet to database")
    
    def get_wallet(self, telegram_id: int) -> dict:
        """Получить кошелек пользователя"""
        wallet = self.db.get_wallet(telegram_id)
        if not wallet:
            return None
        
        return {
            'telegram_id': wallet['telegram_id'],
            'eoa_address': wallet['eoa_address'],
            'safe_address': wallet['safe_address']
        }
    
    def get_private_key(self, telegram_id: int) -> str:
        """
        Получить расшифрованный приватный ключ
        ОСТОРОЖНО! Используй только для подписания транзакций!
        """
        wallet = self.db.get_wallet(telegram_id)
        if not wallet:
            raise ValueError(f"Wallet not found for user {telegram_id}")
        
        # Расшифровываем
        private_key = decrypt_private_key(wallet['eoa_private_key'])
        return private_key
    
    def deploy_safe_and_setup(self, telegram_id: int) -> dict:
        """
        Деплой Safe и approve токенов через Relayer (GASLESS!)
        
        Returns:
            dict: {
                'safe_address': str,
                'safe_tx_hash': str,
                'usdc_tx_hash': str,
                'ctf_tx_hash': str,
                'status': 'success' | 'failed'
            }
        """
        # 1. Получаем приватный ключ
        private_key = self.get_private_key(telegram_id)
        
        # 2. Деплоим Safe и approve через Relayer
        print(f"\n🚀 Deploying Safe for user {telegram_id} via Relayer...")
        result = setup_user_for_trading(private_key, telegram_id)
        
        # 3. Если успешно - сохраняем Safe адрес в БД
        if result['status'] == 'success':
            safe_address = result['safe_address']
            self.db.update_safe_address(telegram_id, safe_address)
            print(f"✅ Safe address saved to DB: {safe_address}")
        
        return result
    
    def is_safe_deployed(self, telegram_id: int) -> bool:
        """Проверить задеплоен ли Safe"""
        wallet = self.db.get_wallet(telegram_id)
        return wallet and wallet['safe_address'] is not None


# Тестовые функции
def test_wallet_creation():
    """Тест создания кошелька"""
    print("🧪 Testing wallet creation...\n")
    
    manager = WalletManager()
    
    # Тестовый пользователь
    test_telegram_id = 123456789
    
    # Создаем кошелек
    wallet = manager.create_wallet_for_user(test_telegram_id)
    
    print("\n📊 Created wallet:")
    print(f"   Telegram ID: {wallet['telegram_id']}")
    print(f"   EOA Address: {wallet['eoa_address']}")
    print(f"   Safe Address: {wallet['safe_address'] or 'Not deployed yet'}")
    
    # Проверяем что можем получить приватный ключ
    try:
        private_key = manager.get_private_key(test_telegram_id)
        print(f"\n✅ Can decrypt private key: {private_key[:10]}...")
        
        # Проверяем что ключ валидный
        from eth_account import Account
        account = Account.from_key(private_key)
        
        if account.address.lower() == wallet['eoa_address'].lower():
            print("✅ Private key matches EOA address!")
        else:
            print("❌ ERROR: Key doesn't match address!")
            
    except Exception as e:
        print(f"❌ Error getting private key: {e}")
    
    print("\n✅ Wallet creation test completed!")


def test_safe_deployment():
    """Тест деплоя Safe через Relayer"""
    print("\n🧪 Testing Safe deployment via Relayer...\n")
    
    manager = WalletManager()
    test_telegram_id = 123456789
    
    # Проверяем что кошелек создан
    wallet = manager.get_wallet(test_telegram_id)
    if not wallet:
        print("❌ Create wallet first with test_wallet_creation()")
        return
    
    print(f"📊 Current wallet:")
    print(f"   EOA: {wallet['eoa_address']}")
    print(f"   Safe: {wallet['safe_address'] or 'Not deployed'}")
    
    if wallet['safe_address']:
        print("\n⚠️  Safe already deployed!")
        return
    
    print("\n🚀 Deploying Safe via Relayer...")
    print("   (This may take 30-60 seconds)\n")
    
    try:
        result = manager.deploy_safe_and_setup(test_telegram_id)
        
        if result['status'] == 'success':
            print("\n✅ Safe deployment successful!")
            print(f"   Safe Address: {result['safe_address']}")
            print(f"   Safe TX: {result['safe_tx_hash']}")
            print(f"   USDC Approve TX: {result['usdc_tx_hash']}")
            print(f"   CTF Approve TX: {result['ctf_tx_hash']}")
            print("\n💰 User is ready to trade!")
        else:
            print(f"\n❌ Deployment failed: {result.get('error')}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "deploy":
        # python wallet_manager.py deploy
        test_safe_deployment()
    else:
        # python wallet_manager.py
        test_wallet_creation()