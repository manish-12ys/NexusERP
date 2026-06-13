import os
from flask import Flask
from config import Config
from app.extensions import db, login_manager, migrate, socketio, bcrypt
from app.services.audit.auto_audit import register_audit_hooks

try:
    import click
except ImportError:
    click = None


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    register_audit_hooks()

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)
    bcrypt.init_app(app)

    from app.routes.landing import landing_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.products import products_bp
    from app.routes.inventory import inventory_bp
    from app.routes.sales import sales_bp
    from app.routes.customers import customers_bp
    from app.routes.purchase import purchase_bp
    from app.routes.vendors import vendors_bp
    from app.routes.bom import bom_bp
    from app.routes.manufacturing import manufacturing_bp
    from app.routes.workorders import workorders_bp
    from app.routes.procurement import procurement_bp
    from app.routes.pos import pos_bp
    from app.routes.reports import reports_bp
    from app.routes.analytics import analytics_bp
    from app.routes.audit import audit_bp
    from app.routes.copilot import copilot_bp
    from app.routes.kanban import kanban_bp

    app.register_blueprint(landing_bp, url_prefix="/")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(products_bp, url_prefix="/products")
    app.register_blueprint(inventory_bp, url_prefix="/inventory")
    app.register_blueprint(sales_bp, url_prefix="/sales")
    app.register_blueprint(customers_bp, url_prefix="/customers")
    app.register_blueprint(purchase_bp, url_prefix="/purchase")
    app.register_blueprint(vendors_bp, url_prefix="/vendors")
    app.register_blueprint(bom_bp, url_prefix="/bom")
    app.register_blueprint(manufacturing_bp, url_prefix="/manufacturing")
    app.register_blueprint(workorders_bp, url_prefix="/workorders")
    app.register_blueprint(procurement_bp, url_prefix="/procurement")
    app.register_blueprint(pos_bp, url_prefix="/pos")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(analytics_bp, url_prefix="/analytics")
    app.register_blueprint(audit_bp, url_prefix="/audit")
    app.register_blueprint(copilot_bp, url_prefix="/copilot")
    app.register_blueprint(kanban_bp, url_prefix="/kanban")

    if click is not None:
        @app.cli.command("init-db")
        @click.option("--seed", is_flag=True, help="Seed with demo data")
        def init_db_command(seed):
            db.create_all()
            click.echo("Database tables created.")
            if seed:
                from app.seed.demo_data import seed_demo_data
                seed_demo_data()
                click.echo("Demo data seeded.")
    else:
        @app.cli.command("init-db")
        def init_db_command(seed=None):
            db.create_all()
            print("Database tables created.")
            if seed:
                from app.seed.demo_data import seed_demo_data
                seed_demo_data()
                print("Demo data seeded.")

    return app
