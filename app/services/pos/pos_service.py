from app.extensions import db
from app.models.pos_session import PosSession
from app.models.pos_order import PosOrder
from app.models.pos_order_line import PosOrderLine
from app.models.product import Product
from app.services.inventory.stock_service import StockService
from datetime import datetime


class PosService:
    def get_open_session(self, user_id):
        return PosSession.query.filter_by(user_id=user_id, status="open").first()

    def list_sessions(self):
        return PosSession.query.order_by(PosSession.opened_at.desc()).all()

    def get_order(self, order_id):
        return PosOrder.query.get_or_404(order_id)

    def open_session(self, user_id, opening_balance=0.0):
        session = PosSession(
            session_number=f"POS-{PosSession.query.count() + 1:05d}",
            user_id=user_id,
            opening_balance=opening_balance,
        )
        db.session.add(session)
        db.session.commit()
        return session

    def close_session(self, session_id, closing_balance=0.0):
        session = PosSession.query.get(session_id)
        if session:
            session.status = "closed"
            session.closed_at = datetime.utcnow()
            session.closing_balance = closing_balance
            db.session.commit()
        return session

    def create_order(self, session_id, items, user_id=None, customer_id=None, payment_method="cash"):
        session = PosSession.query.get(session_id)
        if not session:
            return None, "Open POS session not found."

        if not items:
            return None, "No items were added to the cart."

        order_number = f"POS-ORD-{PosOrder.query.count() + 1:05d}"
        receipt_number = f"RCPT-{PosOrder.query.count() + 1:05d}"
        order = PosOrder(
            order_number=order_number,
            receipt_number=receipt_number,
            session_id=session_id,
            customer_id=customer_id,
            payment_method=payment_method,
            payment_status="paid",
        )

        db.session.add(order)
        db.session.flush()

        subtotal = 0
        tax_total = 0

        for item in items:
            product = Product.query.get(item["product_id"])
            if not product:
                db.session.rollback()
                return None, "One of the selected products does not exist."

            quantity = float(item["quantity"])
            if quantity <= 0:
                db.session.rollback()
                return None, "Each cart item must have a quantity greater than zero."

            inventory = product.inventory
            if not inventory or inventory.free_to_use_qty < quantity:
                db.session.rollback()
                return None, f"Insufficient stock for {product.name}."

            unit_price = product.sales_price
            line_total = quantity * unit_price
            line_tax = line_total * product.tax_percent / 100

            line = PosOrderLine(
                pos_order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=unit_price,
                tax_percent=product.tax_percent,
                line_total=line_total,
            )
            db.session.add(line)
            subtotal += line_total
            tax_total += line_tax

            success, result = StockService.consume_stock(product.id, quantity, user_id=user_id, commit=False)
            if not success:
                db.session.rollback()
                return None, result

        order.subtotal = subtotal
        order.tax_amount = tax_total
        order.total_amount = subtotal + tax_total
        session.total_sales += order.total_amount

        db.session.commit()
        return order, None
