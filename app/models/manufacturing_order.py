from app.extensions import db
from datetime import datetime


class ManufacturingOrder(db.Model):
    __tablename__ = "manufacturing_orders"

    id = db.Column(db.Integer, primary_key=True)
    mo_number = db.Column(db.String(80), unique=True, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    bom_id = db.Column(db.Integer, db.ForeignKey("boms.id"))
    quantity = db.Column(db.Float, nullable=False)
    produced_qty = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(30), default="draft")
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    notes = db.Column(db.Text)
    warehouse = db.Column(db.String(80))
    location = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = db.relationship("Product", backref="manufacturing_orders")
    bom = db.relationship("Bom", backref="manufacturing_orders")
    assignee = db.relationship("User", backref="manufacturing_orders")
    work_orders = db.relationship("WorkOrder", backref="mo", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ManufacturingOrder {self.mo_number}>"
