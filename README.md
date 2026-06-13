# NexusERP

**NexusERP** is a Flask-based manufacturing ERP built for factory operations that need one connected place for sales, inventory, purchasing, production, POS, reporting, and role-based administration.

The current demo dataset is shaped around a furniture manufacturing workflow: components, end products, product recipes, sales demand, purchasing suggestions, production orders, production tasks, and stock movements.

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-D71F00)
![SQLite](https://img.shields.io/badge/SQLite-Development-003B57?logo=sqlite&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?logo=bootstrap&logoColor=white)

---

## What It Does

NexusERP brings the core factory loop into one web app:

- **Command dashboard** for orders, inventory value, shortages, delayed work, and production progress.
- **Product and category management** with component and end product support.
- **Inventory control** with stock views, adjustments, transfers, low-stock checks, and ledger history.
- **Sales order workflow** with customers, order lines, confirmation, delivery, and reservation logic.
- **Purchasing workflow** with suppliers, purchase orders, receiving, and stock updates.
- **Product Recipes** for end product costing and production planning.
- **Production orders and production tasks** for factory execution.
- **Smart Purchasing automation** for reorder, make-to-stock, and make-to-order planning.
- **Point of sale terminal** for cashier-led retail transactions.
- **Reports and analytics** with KPI services and Chart.js-powered views.
- **Audit logs and permissions** for operational traceability.
- **AI Operations Copilot** that can summarize live ERP state and provide business guidance when `GEMINI_API_KEY` is configured.

---

## Tech Stack

| Layer | Tools |
| --- | --- |
| Backend | Python 3.14, Flask 3.1 |
| Database | SQLAlchemy, Flask-Migrate, SQLite for local development |
| Auth | Flask-Login, Flask-Bcrypt, role-based permissions |
| Forms | Flask-WTF, WTForms |
| Frontend | Jinja templates, Bootstrap 5.3, Bootstrap Icons, custom CSS |
| Charts | Chart.js |
| Realtime-ready extension | Flask-SocketIO |
| AI integration | Google Gemini via `google-genai` |
| Testing | Pytest |
| Packaging | `pyproject.toml`, `uv.lock`, optional `requirements.txt` |

---

## Project Structure

```text
NexusERP/
+-- app/
|   +-- models/              # SQLAlchemy domain models
|   +-- routes/              # Flask blueprints
|   +-- services/            # Business logic by module
|   +-- forms/               # WTForms definitions
|   +-- templates/           # Jinja UI templates
|   +-- static/              # CSS, JavaScript, images
|   +-- seed/                # Demo data and database reset scripts
|   +-- extensions/          # Flask extension instances
|   +-- utils/               # Decorators, helpers, validators
+-- migrations/              # Alembic/Flask-Migrate migration setup
+-- tests/                   # Pytest coverage for core workflows
+-- instance/                # Local SQLite database location
+-- app.py                   # Development entry point
+-- config.py                # App configuration classes
+-- pyproject.toml           # Project metadata and dependencies
+-- requirements.txt         # Pinned pip dependencies
```

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/manish-12ys/NexusERP.git
cd NexusERP
```

### 2. Create a local environment

Using `uv`:

```bash
uv sync
```

Or using `pip`:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
SECRET_KEY=change-this-in-development
DATABASE_URL=sqlite:///instance/nexuserp.db
GEMINI_API_KEY=
```

`GEMINI_API_KEY` is optional. Without it, the Copilot route returns a local mock response instead of calling Gemini.

### 4. Initialize and seed the database

```bash
uv run python app/seed/reset_db.py
```

If you are using an activated virtual environment without `uv`:

```bash
python app/seed/reset_db.py
```

### 5. Start the app

```bash
uv run flask --app app.py run
```

Or:

```bash
python app.py
```

Open the app at [http://localhost:5000](http://localhost:5000).

---

## Demo Accounts

Seed data creates operational users for each role.

| Username | Password | Role | Best For |
| --- | --- | --- | --- |
| `admin` | `admin123` | Admin | User, role, and full-system management |
| `owner` | `owner123` | Business Owner | Dashboard, reports, audit visibility |
| `inventory` | `inventory123` | Inventory Manager | Products, stock, adjustments, smart purchasing |
| `sales` | `sales123` | Sales User | Customers and sales order flow |
| `purchase` | `purchase123` | Purchase User | Suppliers, purchase orders, receiving |
| `manufacturing` | `manufacturing123` | Manufacturing User | Product Recipes, production orders, production tasks |
| `cashier` | `cashier123` | POS Cashier | POS terminal |

---

## Core URLs

| Area | Path |
| --- | --- |
| Landing page | `/` |
| Login | `/auth/login` |
| Dashboard | `/dashboard/` |
| Products | `/products/` |
| Inventory | `/inventory/` |
| Sales | `/sales/` |
| Purchases | `/purchase/` |
| Manufacturing | `/manufacturing/` |
| Smart Purchasing | `/procurement/` |
| POS | `/pos/` |
| Reports | `/reports/` |
| Analytics | `/analytics/` |
| Audit logs | `/audit/` |
| AI Copilot | `/copilot/` |
| Kanban | `/kanban/` |

---

## Database Commands

Create tables through the Flask CLI:

```bash
uv run flask --app app.py init-db
```

Create tables and seed demo data:

```bash
uv run flask --app app.py init-db --seed
```

Reset the local SQLite database and reseed the furniture demo catalog:

```bash
uv run python app/seed/reset_db.py
```

Run migrations:

```bash
uv run flask --app app.py db upgrade
```

---

## Testing

Run the test suite:

```bash
uv run pytest
```

The tests use `TestingConfig` with an in-memory SQLite database and seed the role/permission matrix for each test.

---

## Demo Data

The seed scripts create a compact furniture manufacturing dataset, including:

- Components such as wood legs, table tops, screws, wood polish, planks, and cushions.
- End products such as dining tables, office chairs, and coffee tables.
- BOM recipes that calculate component cost for manufactured products.
- Sample customers, suppliers, inventory balances, roles, permissions, and demo users.

---

## Configuration Notes

- Local data is stored in `instance/nexuserp.db` by default.
- Set `DATABASE_URL` to use a different database backend.
- Set a strong `SECRET_KEY` outside development.
- Keep `.env`, local SQLite databases, and virtual environments out of Git.
- The repository includes Flask-Migrate scaffolding under `migrations/`.

---

## Development Notes

- Put route-level HTTP behavior in `app/routes/`.
- Put business rules in `app/services/`.
- Keep model relationships and persistence concerns in `app/models/`.
- Use permission checks from `app/utils/decorators.py` for protected workflows.
- Update seed data when adding new roles, permissions, or demo entities.
- Add focused tests under `tests/` for each workflow change.

---

## License

No license file is currently included. Add one before distributing or deploying this project beyond private/internal use.
