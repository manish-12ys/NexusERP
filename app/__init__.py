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
    # Initialize the Flask application object
    app = Flask(__name__, instance_relative_config=True)
    # Load configuration parameters
    app.config.from_object(config_class)

    # Register audit hooks for capturing database changes
    register_audit_hooks()

    # Ensure the instance directory exists for SQLite database files
    os.makedirs(app.instance_path, exist_ok=True)

    # Initialize database, migration, and auth extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)
    bcrypt.init_app(app)

    # Ensure all tables exist (safe for first-run and SQLite dev use)
    with app.app_context():
        # Import all models so SQLAlchemy is aware of them before create_all
        from app.models import (  # noqa: F401
            user, role, permission, product, category, customer, vendor,
            inventory, sales_order, sales_order_line, purchase_order,
            purchase_order_line, bom, bom_component, bom_operation,
            manufacturing_order, work_order, work_center, stock_ledger,
            stock_transfer, warehouse, procurement_request, procurement_rule,
            pos_session, pos_order, pos_order_line, audit_log, notification,
            invoice, invoice_line,
        )
        db.create_all()

        # Auto-seed default roles and users on first run (no-op if already seeded)
        from app.models.user import User
        if User.query.count() == 0:
            from app.seed.demo_data import seed_demo_data
            seed_demo_data()

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
    from app.routes.invoices import invoices_bp

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
    app.register_blueprint(invoices_bp, url_prefix="/invoices")

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
