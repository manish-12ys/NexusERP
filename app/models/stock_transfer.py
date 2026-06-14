from app.extensions import db
from datetime import datetime


class StockTransfer(db.Model):
    __tablename__ = "stock_transfers"

    id = db.Column(db.Integer, primary_key=True)
    transfer_number = db.Column(db.String(80), unique=True, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    from_warehouse = db.Column(db.String(80), nullable=False)
    from_location = db.Column(db.String(80), nullable=False)
    to_warehouse = db.Column(db.String(80), nullable=False)
    to_location = db.Column(db.String(80), nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending, completed, cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = db.relationship("Product", backref="stock_transfers")

    def __repr__(self):
        return f"<StockTransfer {self.transfer_number} status={self.status}>"
