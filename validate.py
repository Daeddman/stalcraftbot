"""Quick validation of all changes."""
import sys
sys.path.insert(0, '.')

# 1. Check InvalidItemError
from api.client import StalcraftClient, InvalidItemError
print("[OK] api.client - InvalidItemError imported")

# 2. Check auction imports
from api.auction import get_active_lots, get_price_history
print("[OK] api.auction - imports OK")

# 3. Check GameItem.api_supported
from services.item_loader import GameItem, ItemDatabase, item_db
short = GameItem('test', 'a', 'b', 'c', 'd', '', '')
long = GameItem('8AjTFOVB', 'a', 'b', 'c', 'd', '', '')
assert short.api_supported == True, "Short ID should be api_supported"
assert long.api_supported == False, "Long ID should NOT be api_supported"
print(f"[OK] GameItem.api_supported: short={short.api_supported}, long={long.api_supported}")

# 4. Check ItemDatabase.is_api_supported
db = ItemDatabase()
assert db.is_api_supported('test') == True
assert db.is_api_supported('8AjTFOVB') == False
print("[OK] ItemDatabase.is_api_supported works")

# 5. Check web app imports
from web.app import app
print("[OK] web.app imported")

# 6. Check custom_icons dir
from pathlib import Path
icons_dir = Path('custom_icons')
assert icons_dir.exists(), "custom_icons dir should exist"
pngs = list(icons_dir.glob('*.png'))
print(f"[OK] custom_icons: {len(pngs)} PNG files")

print("\n=== ALL CHECKS PASSED ===")

