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
    sku = StringField("SKU", validators=[Optional(), Length(max=80)])
    barcode = StringField("Barcode", validators=[Optional(), Length(max=80)])
    category_id = SelectField("Category", coerce=int, validators=[Optional()])
    description = TextAreaField("Description", validators=[Optional()])
    cost_price = FloatField("Unit Cost", default=0.0)
    sales_price = FloatField("Selling Price", default=0.0)
    tax_percent = FloatField("Tax Rate (%)", default=0.0)
    product_type = SelectField(
        "Category Type",
        choices=[
            ("finished_goods", "End Products"),
            ("raw_material", "Components"),
            ("semi_finished", "Work-in-Progress"),
            ("service", "Service"),
        ],
        default="finished_goods",
    )
    unit_of_measure = SelectField(
        "Measurement Unit",
        choices=[("pcs", "Pieces"), ("kg", "Kilograms"), ("m", "Meters"), ("l", "Liters")],
        default="pcs",
    )
    reorder_level = FloatField("Minimum Stock Amount", default=0.0)
    safety_stock = FloatField("Extra Buffer Stock", default=0.0)
    procurement_type = SelectField(
        "Sourcing Method",
        choices=[("mts", "Stock Before Demand"), ("mto", "Stock After Demand")],
        default="mts",
    )
    lead_time_days = FloatField("Days to Deliver", default=0)
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save")


class CategoryForm(FlaskForm):
    name = StringField("Category Name", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Description", validators=[Optional()])
    submit = SubmitField("Save")
