from app.extensions import db


class PurchaseOrderLine(db.Model):
    __tablename__ = "purchase_order_lines"

    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey("purchase_orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit_cost = db.Column(db.Float, default=0.0)
    tax_percent = db.Column(db.Float, default=0.0)
    received_qty = db.Column(db.Float, default=0.0)
    line_total = db.Column(db.Float, default=0.0)
    warehouse = db.Column(db.String(80))
    location = db.Column(db.String(80))


    def __repr__(self):
        return f"<PurchaseOrderLine {self.product_id} qty={self.quantity}>"
