from app.extensions import db
from app.models.category import Category
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.bom import Bom
from app.models.bom_component import BomComponent


def seed_sample_products():
    categories_data = [
        "Components", "Elements", "End Products", "Packaging", "Tools"
    ]
    for cat_name in categories_data:
        if not Category.query.filter_by(name=cat_name).first():
            db.session.add(Category(name=cat_name))
    db.session.flush()
    
    raw_cat = Category.query.filter_by(name="Components").first()
    finished_cat = Category.query.filter_by(name="End Products").first()
    
    products_data = [
        {"name": "Wood Legs", "sku": "RAW-WLG-001", "product_type": "raw_material", "cost_price": 500.00, "sales_price": 800.00, "category": raw_cat, "reorder_level": 100, "safety_stock": 40, "on_hand": 100, "procurement_type": "mts"},
        {"name": "Table Top", "sku": "RAW-TTP-001", "product_type": "raw_material", "cost_price": 2500.00, "sales_price": 3800.00, "category": raw_cat, "reorder_level": 25, "safety_stock": 10, "on_hand": 100, "procurement_type": "mts"},
        {"name": "Screws", "sku": "RAW-SCR-001", "product_type": "raw_material", "cost_price": 10.00, "sales_price": 15.00, "category": raw_cat, "reorder_level": 500, "safety_stock": 100, "on_hand": 1000, "procurement_type": "mts"},
        {"name": "Wood Polish/Paint", "sku": "RAW-PNT-001", "product_type": "raw_material", "cost_price": 300.00, "sales_price": 450.00, "category": raw_cat, "reorder_level": 20, "safety_stock": 10, "on_hand": 100, "procurement_type": "mts"},
        {"name": "Wood Planks", "sku": "RAW-WDP-001", "product_type": "raw_material", "cost_price": 800.00, "sales_price": 1200.00, "category": raw_cat, "reorder_level": 120, "safety_stock": 50, "on_hand": 100, "procurement_type": "mts"},
        {"name": "Chair Cushion", "sku": "RAW-CSH-001", "product_type": "raw_material", "cost_price": 400.00, "sales_price": 600.00, "category": raw_cat, "reorder_level": 30, "safety_stock": 15, "on_hand": 100, "procurement_type": "mts"},
        
        {"name": "Dining Table", "sku": "FG-TAB-001", "product_type": "finished_goods", "cost_price": 4920.00, "sales_price": 12000.00, "category": finished_cat, "reorder_level": 10, "safety_stock": 5, "on_hand": 5, "procurement_type": "mto"},
        {"name": "Office Chair", "sku": "FG-CHR-001", "product_type": "finished_goods", "cost_price": 2100.00, "sales_price": 4500.00, "category": finished_cat, "reorder_level": 20, "safety_stock": 10, "on_hand": 15, "procurement_type": "mto"},
        {"name": "Coffee Table", "sku": "FG-COF-001", "product_type": "finished_goods", "cost_price": 3500.00, "sales_price": 7500.00, "category": finished_cat, "reorder_level": 10, "safety_stock": 5, "on_hand": 8, "procurement_type": "mto"},
    ]
    
    for pd in products_data:
        on_hand_qty = pd.pop("on_hand", 100)
        if not Product.query.filter_by(sku=pd["sku"]).first():
            product = Product(**pd)
            db.session.add(product)
            db.session.flush()
            inv = Inventory(product_id=product.id, on_hand_qty=on_hand_qty)
            db.session.add(inv)
            
    db.session.commit()
    
    # Seeding BOMs
    # 1. Dining Table BOM
    table = Product.query.filter_by(sku="FG-TAB-001").first()
    legs = Product.query.filter_by(sku="RAW-WLG-001").first()
    top = Product.query.filter_by(sku="RAW-TTP-001").first()
    screws = Product.query.filter_by(sku="RAW-SCR-001").first()
    paint = Product.query.filter_by(sku="RAW-PNT-001").first()
    
    if table and legs and top and screws and paint:
        if not Bom.query.filter_by(product_id=table.id).first():
            bom = Bom(product_id=table.id, name="BOM for Dining Table", quantity=1, is_active=True)
            db.session.add(bom)
            db.session.flush()
            db.session.add(BomComponent(bom_id=bom.id, product_id=legs.id, quantity=4, unit_cost=legs.cost_price, total_cost=legs.cost_price * 4))
            db.session.add(BomComponent(bom_id=bom.id, product_id=top.id, quantity=1, unit_cost=top.cost_price, total_cost=top.cost_price * 1))
            db.session.add(BomComponent(bom_id=bom.id, product_id=screws.id, quantity=12, unit_cost=screws.cost_price, total_cost=screws.cost_price * 12))
            db.session.add(BomComponent(bom_id=bom.id, product_id=paint.id, quantity=1, unit_cost=paint.cost_price, total_cost=paint.cost_price * 1))
            bom.calculate_cost()
            
    # 2. Office Chair BOM
    chair = Product.query.filter_by(sku="FG-CHR-001").first()
    planks = Product.query.filter_by(sku="RAW-WDP-001").first()
    cushion = Product.query.filter_by(sku="RAW-CSH-001").first()
    
    if chair and planks and cushion and screws:
        if not Bom.query.filter_by(product_id=chair.id).first():
            bom = Bom(product_id=chair.id, name="BOM for Office Chair", quantity=1, is_active=True)
            db.session.add(bom)
            db.session.flush()
            db.session.add(BomComponent(bom_id=bom.id, product_id=planks.id, quantity=2, unit_cost=planks.cost_price, total_cost=planks.cost_price * 2))
            db.session.add(BomComponent(bom_id=bom.id, product_id=cushion.id, quantity=1, unit_cost=cushion.cost_price, total_cost=cushion.cost_price * 1))
            db.session.add(BomComponent(bom_id=bom.id, product_id=screws.id, quantity=10, unit_cost=screws.cost_price, total_cost=screws.cost_price * 10))
            bom.calculate_cost()

    # 3. Coffee Table BOM
    coffee = Product.query.filter_by(sku="FG-COF-001").first()
    
    if coffee and planks and paint:
        if not Bom.query.filter_by(product_id=coffee.id).first():
            bom = Bom(product_id=coffee.id, name="BOM for Coffee Table", quantity=1, is_active=True)
            db.session.add(bom)
            db.session.flush()
            db.session.add(BomComponent(bom_id=bom.id, product_id=planks.id, quantity=4, unit_cost=planks.cost_price, total_cost=planks.cost_price * 4))
            db.session.add(BomComponent(bom_id=bom.id, product_id=paint.id, quantity=1, unit_cost=paint.cost_price, total_cost=paint.cost_price * 1))
            bom.calculate_cost()

    db.session.commit()
