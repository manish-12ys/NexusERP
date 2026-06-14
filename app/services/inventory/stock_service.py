from app.extensions import db
from app.models.inventory import Inventory
from app.models.stock_ledger import StockLedger
from app.models.product import Product


class StockService:
    @staticmethod
    # Reserve stock
    def reserve_stock(product_id, quantity, warehouse=None, location=None):
        # Fetch inventory record for the specified product and location
        query = Inventory.query.filter_by(product_id=product_id)
        if warehouse:
            query = query.filter_by(warehouse=warehouse)
        if location:
            query = query.filter_by(location=location)
        inv = query.first()
        
        if not inv:
            return False, "No inventory record found"
        # Check if free stock covers the reservation amount
        if inv.free_to_use_qty < quantity:
            return False, f"Insufficient stock: {inv.free_to_use_qty} available, {quantity} needed"
        # Increment reserved quantity and commit
        inv.reserved_qty += quantity
        db.session.commit()
        return True, inv

    @staticmethod
    # Release stock
    def unreserve_stock(product_id, quantity, warehouse=None, location=None):
        # Fetch inventory record for the specified product and location
        query = Inventory.query.filter_by(product_id=product_id)
        if warehouse:
            query = query.filter_by(warehouse=warehouse)
        if location:
            query = query.filter_by(location=location)
        inv = query.first()
        
        if not inv:
            return False, "No inventory record found"
        # Decrement reserved quantity, ensuring it never goes below zero
        inv.reserved_qty = max(0, inv.reserved_qty - quantity)
        db.session.commit()
        return True, inv

    @staticmethod
    # Consume stock
    def consume_stock(product_id, quantity, user_id=None, commit=True, warehouse=None, location=None):
        # Fetch inventory record for the specified product and location
        query = Inventory.query.filter_by(product_id=product_id)
        if warehouse:
            query = query.filter_by(warehouse=warehouse)
        if location:
            query = query.filter_by(location=location)
        inv = query.first()
        
        if not inv:
            return False, "No inventory record found"
        # Decrement physical stock and free up the reservation
        before = inv.on_hand_qty
        inv.on_hand_qty -= quantity
        inv.reserved_qty = max(0, inv.reserved_qty - quantity)
        # Ensure stock does not fall below zero
        if inv.on_hand_qty < 0:
            return False, "Stock cannot be negative"
        db.session.flush()

        # Log movement entry into stock ledger
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
