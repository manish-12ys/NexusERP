from app.extensions import db
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_line import PurchaseOrderLine
from app.models.product import Product
from datetime import datetime


class PurchaseService:
    @staticmethod
    def create_order(vendor_id, items=None, user_id=None, expected_date=None, notes=None):
        order = PurchaseOrder(
            order_number=PurchaseService._generate_order_number(),
            vendor_id=vendor_id,
            user_id=user_id,
            expected_date=expected_date,
            notes=notes,
            status="draft",
        )
        db.session.add(order)
        db.session.flush()

        subtotal = 0.0
        if items:
            for item in items:
                product = Product.query.get(item["product_id"])
                if not product:
                    return None, f"Product {item['product_id']} not found"
                qty = item["quantity"]
                unit_cost = item.get("unit_cost", product.cost_price)
                line_total = qty * unit_cost

                line = PurchaseOrderLine(
                    purchase_order_id=order.id,
                    product_id=product.id,
                    quantity=qty,
                    unit_cost=unit_cost,
                    line_total=line_total,
                )
                db.session.add(line)
                subtotal += line_total

        order.subtotal = subtotal
        order.total_amount = subtotal
        db.session.commit()
        return order, None

    @staticmethod
    def confirm_order(order_id):
        order = PurchaseOrder.query.get(order_id)
        if not order:
            return None, "Order not found"
        if order.status != "draft":
            return None, "Only draft orders can be confirmed"
        order.status = "confirmed"
        db.session.commit()
        return order, None

    @staticmethod
    def _generate_order_number():
        prefix = "PO"
        last = PurchaseOrder.query.order_by(PurchaseOrder.id.desc()).first()
        seq = (last.id + 1) if last else 1
        return f"{prefix}-{datetime.now().strftime('%Y%m')}-{seq:04d}"
