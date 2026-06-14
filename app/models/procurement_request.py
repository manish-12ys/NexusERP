from app.extensions import db
from datetime import datetime


class ProcurementRequest(db.Model):
    __tablename__ = "procurement_requests"

    id = db.Column(db.Integer, primary_key=True)
    request_number = db.Column(db.String(80), unique=True, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    source_type = db.Column(db.String(20))
    source_id = db.Column(db.Integer)
    status = db.Column(db.String(20), default="open")
    mo_id = db.Column(db.Integer, db.ForeignKey("manufacturing_orders.id"))
    po_id = db.Column(db.Integer, db.ForeignKey("purchase_orders.id"))
    stock_transfer_id = db.Column(db.Integer, db.ForeignKey("stock_transfers.id"))
    notes = db.Column(db.Text)
    warehouse = db.Column(db.String(80))
    location = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    closed_at = db.Column(db.DateTime)

    product = db.relationship("Product", backref="procurement_requests")
    mo = db.relationship("ManufacturingOrder", backref="procurement_requests")
    po = db.relationship("PurchaseOrder", backref="procurement_requests")
    stock_transfer = db.relationship("StockTransfer", backref="procurement_requests")

    def __repr__(self):
        return f"<ProcurementRequest {self.request_number}>"
