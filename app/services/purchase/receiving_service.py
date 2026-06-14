from app.extensions import db
from app.models.purchase_order import PurchaseOrder
from app.services.inventory.stock_service import StockService
from app.services.inventory.ledger_service import LedgerService
from datetime import datetime


class ReceivingService:
    @staticmethod
    def receive_order(order_id, user_id=None):
        order = PurchaseOrder.query.get(order_id)
        if not order:
            return None, "Order not found"
        if order.status not in ("confirmed", "partially_received"):
            return None, "Order cannot be received"

        all_received = True
        for line in order.lines.all():
            remaining = line.quantity - line.received_qty
            if remaining > 0:
                from app.services.inventory.inventory_service import InventoryService

                inv = InventoryService.get_or_create_inventory(
                    line.product_id,
                    warehouse=line.warehouse or "Main",
                    location=line.location or "Default"
                )
                before = inv.on_hand_qty

                inv.on_hand_qty += remaining
                line.received_qty = line.quantity

                LedgerService.record_movement(
                    product_id=line.product_id,
                    movement_type="purchase_receipt",
                    quantity=remaining,
                    before_qty=before,
                    after_qty=inv.on_hand_qty,
                    reference_type="purchase_order",
                    reference_id=order.id,
                    reference_number=order.order_number,
                    unit_price=line.unit_cost,
                    user_id=user_id,
                )

        order.status = "received" if all_received else "partially_received"
        order.received_date = datetime.utcnow()
        db.session.commit()
        return order, None
