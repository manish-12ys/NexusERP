from app.extensions import db
from app.models.sales_order import SalesOrder
from app.models.sales_order_line import SalesOrderLine
from app.models.product import Product
from app.models.audit_log import AuditLog
from datetime import datetime


class SalesService:
    @staticmethod
    def create_order(customer_id, items=None, user_id=None, expected_date=None, notes=None):
        order = SalesOrder(
            order_number=SalesService._generate_order_number(),
            customer_id=customer_id,
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
                unit_price = item.get("unit_price", product.sales_price)
                tax_pct = item.get("tax_percent", product.tax_percent)
                line_total = qty * unit_price

                line = SalesOrderLine(
                    sales_order_id=order.id,
                    product_id=product.id,
                    quantity=qty,
                    unit_price=unit_price,
                    tax_percent=tax_pct,
                    line_total=line_total,
                )
                db.session.add(line)
                subtotal += line_total

        order.subtotal = subtotal
        order.total_amount = subtotal
        db.session.commit()
        return order, None

    @staticmethod
    def confirm_order(order_id, user_id=None):
        order = SalesOrder.query.get(order_id)
        if not order:
            return None, "Order not found"
        if order.status != "draft":
            return None, "Only draft orders can be confirmed"

        from app.services.inventory.stock_service import StockService

        for line in order.lines.all():
            success, _ = StockService.reserve_stock(line.product_id, line.quantity)
            if not success:
                order.status = "cancelled"
                db.session.commit()
                return None, f"Insufficient stock for {line.product.name}"

        order.status = "confirmed"
        db.session.commit()
        return order, None

    @staticmethod
    def _generate_order_number():
        prefix = "SO"
        last = SalesOrder.query.order_by(SalesOrder.id.desc()).first()
        seq = (last.id + 1) if last else 1
        return f"{prefix}-{datetime.now().strftime('%Y%m')}-{seq:04d}"
