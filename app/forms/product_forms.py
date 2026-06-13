from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    TextAreaField,
    FloatField,
    SelectField,
    BooleanField,
    SubmitField,
)
from wtforms.validators import DataRequired, Optional, Length


class ProductForm(FlaskForm):
    name = StringField("Product Name", validators=[DataRequired(), Length(max=200)])
    sku = StringField("SKU", validators=[DataRequired(), Length(max=80)])
    barcode = StringField("Barcode", validators=[Optional(), Length(max=80)])
    category_id = SelectField("Category", coerce=int, validators=[Optional()])
    description = TextAreaField("Description", validators=[Optional()])
    cost_price = FloatField("Cost Price", default=0.0)
    sales_price = FloatField("Sales Price", default=0.0)
    tax_percent = FloatField("Tax %", default=0.0)
    product_type = SelectField(
        "Product Type",
        choices=[
            ("finished_goods", "Finished Goods"),
            ("raw_material", "Raw Material"),
            ("semi_finished", "Semi-Finished"),
            ("service", "Service"),
        ],
        default="finished_goods",
    )
    unit_of_measure = SelectField(
        "Unit",
        choices=[("pcs", "Pieces"), ("kg", "Kg"), ("m", "Meter"), ("l", "Liter")],
        default="pcs",
    )
    reorder_level = FloatField("Minimum Stock Amount", default=0.0)
    safety_stock = FloatField("Extra Buffer Stock", default=0.0)
    procurement_type = SelectField(
        "Procurement Type",
        choices=[("mts", "Make to Stock"), ("mto", "Make to Order")],
        default="mts",
    )
    lead_time_days = FloatField("Lead Time (days)", default=0)
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save")


class CategoryForm(FlaskForm):
    name = StringField("Category Name", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Description", validators=[Optional()])
    submit = SubmitField("Save")
