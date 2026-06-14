from app.extensions import db
from app.models.manufacturing_order import ManufacturingOrder
from app.models.product import Product
from app.models.stock_ledger import StockLedger
from app.models.inventory import Inventory


class ProductionService:
    def finish_production(self, mo_id, user_id):
        mo = ManufacturingOrder.query.get(mo_id)
        if not mo:
            return None
        mo.status = "completed"
        mo.produced_qty = mo.quantity
        
        mo_wh = mo.warehouse or "Main"
        mo_loc = mo.location or "Default"

        # Consume raw materials from stock
        if mo.bom:
            for component in mo.bom.components.all():
                required_qty = component.quantity * mo.quantity
                inv = Inventory.query.filter_by(
                    product_id=component.product_id,
                    warehouse=mo_wh,
                    location=mo_loc
                ).first()
                if inv:
                    inv.on_hand_qty -= required_qty
                    entry = StockLedger(
                        product_id=component.product_id,
                        movement_type="production_consumption",
                        reference_type="manufacturing_order",
                        reference_id=mo.id,
                        reference_number=mo.mo_number,
                        quantity=-required_qty,
                        before_qty=inv.on_hand_qty + required_qty,
                        after_qty=inv.on_hand_qty,
                        unit_price=component.unit_cost,
                        total_value=required_qty * component.unit_cost,
                        user_id=user_id,
                        notes=f"Consumed for MO {mo.mo_number} at {mo_wh}:{mo_loc}",
                    )
                    db.session.add(entry)
        # Add finished product to stock
        from app.services.inventory.inventory_service import InventoryService
        inv = InventoryService.get_or_create_inventory(
            mo.product_id, warehouse=mo_wh, location=mo_loc
        )
        before = inv.on_hand_qty
        inv.on_hand_qty += mo.quantity
        entry = StockLedger(
            product_id=mo.product_id,
            movement_type="production_output",
            reference_type="manufacturing_order",
            reference_id=mo.id,
            reference_number=mo.mo_number,
            quantity=mo.quantity,
            before_qty=before,
            after_qty=inv.on_hand_qty,
            unit_price=mo.product.cost_price,
            total_value=mo.quantity * mo.product.cost_price,
            user_id=user_id,
            notes=f"Produced from MO {mo.mo_number} to {mo_wh}:{mo_loc}",
        )
        db.session.add(entry)
        db.session.commit()
        return mo
