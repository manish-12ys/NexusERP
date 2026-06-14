from app.extensions import db
from datetime import datetime


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(80), unique=True, nullable=False)
    barcode = db.Column(db.String(80), unique=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    description = db.Column(db.Text)
    cost_price = db.Column(db.Float, default=0.0)
    sales_price = db.Column(db.Float, default=0.0)
    tax_percent = db.Column(db.Float, default=0.0)
    product_type = db.Column(db.String(20), default="finished_goods")
    unit_of_measure = db.Column(db.String(20), default="pcs")
    is_active = db.Column(db.Boolean, default=True)
    reorder_level = db.Column(db.Float, default=0.0)
    safety_stock = db.Column(db.Float, default=0.0)
    procurement_type = db.Column(db.String(20), default="mts")
    lead_time_days = db.Column(db.Integer, default=0)
    image = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = db.relationship("Category", backref="products")
    inventories = db.relationship("Inventory", backref="product")
    bom = db.relationship("Bom", backref="product", uselist=False)
    sale_lines = db.relationship("SalesOrderLine", backref="product", lazy="dynamic")
    purchase_lines = db.relationship("PurchaseOrderLine", backref="product", lazy="dynamic")

    @property
    def inventory(self):
        # Return the main/primary inventory if it exists, otherwise the first available
        if not self.inventories:
            return None
        # Return Main/Default warehouse, or Phase 1 if present
        main_inv = next((i for i in self.inventories if i.warehouse == "Main"), None)
        if main_inv:
            return main_inv
        return self.inventories[0]

    def __repr__(self):
        return f"<Product {self.name} ({self.sku})>"
