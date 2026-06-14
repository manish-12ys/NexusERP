from app.extensions import db
from datetime import datetime


class Inventory(db.Model):
    __tablename__ = "inventories"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    warehouse = db.Column(db.String(80), default="Main")
    location = db.Column(db.String(80), default="Default")

    __table_args__ = (
        db.UniqueConstraint("product_id", "warehouse", "location", name="_product_warehouse_location_uc"),
    )
    on_hand_qty = db.Column(db.Float, default=0.0)
    reserved_qty = db.Column(db.Float, default=0.0)
    incoming_qty = db.Column(db.Float, default=0.0)
    outgoing_qty = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def free_to_use_qty(self):
        return self.on_hand_qty - self.reserved_qty

    @property
    def is_low_stock(self):
        return self.on_hand_qty <= self.product.safety_stock if self.product else False

    def __repr__(self):
        return f"<Inventory {self.product_id} OH={self.on_hand_qty}>"
