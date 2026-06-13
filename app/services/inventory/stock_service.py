from app.extensions import db
from app.models.inventory import Inventory
from app.models.stock_ledger import StockLedger
from app.models.product import Product


class StockService:
    @staticmethod
    def reserve_stock(product_id, quantity):
        inv = Inventory.query.filter_by(product_id=product_id).first()
        if not inv:
            return False, "No inventory record found"
        if inv.free_to_use_qty < quantity:
            return False, f"Insufficient stock: {inv.free_to_use_qty} available, {quantity} needed"
        inv.reserved_qty += quantity
        db.session.commit()
        return True, inv

    @staticmethod
    def unreserve_stock(product_id, quantity):
        inv = Inventory.query.filter_by(product_id=product_id).first()
        if not inv:
            return False, "No inventory record found"
        inv.reserved_qty = max(0, inv.reserved_qty - quantity)
        db.session.commit()
        return True, inv

    @staticmethod
    def consume_stock(product_id, quantity, user_id=None, commit=True):
        inv = Inventory.query.filter_by(product_id=product_id).first()
        if not inv:
            return False, "No inventory record found"
        before = inv.on_hand_qty
        inv.on_hand_qty -= quantity
        inv.reserved_qty = max(0, inv.reserved_qty - quantity)
        if inv.on_hand_qty < 0:
            return False, "Stock cannot be negative"
        db.session.flush()

        entry = StockLedger(
            product_id=product_id,
            movement_type="consumption",
            quantity=-quantity,
            before_qty=before,
            after_qty=inv.on_hand_qty,
            user_id=user_id,
        )
        db.session.add(entry)
        if commit:
            db.session.commit()
        return True, inv
