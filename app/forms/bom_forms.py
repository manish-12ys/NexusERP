from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    TextAreaField,
    FloatField,
    SelectField,
    SubmitField,
)
from wtforms.validators import DataRequired, Optional, Length


class BomForm(FlaskForm):
    product_id = SelectField("Product", coerce=int, validators=[DataRequired()])
    name = StringField("Recipe Name", validators=[DataRequired(), Length(max=200)])
    version = StringField("Version", default="1.0")
    quantity = FloatField("Quantity", default=1.0)
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save")


class ProcurementRuleForm(FlaskForm):
    product_id = SelectField("Product", coerce=int, validators=[DataRequired()])
    procurement_type = SelectField(
        "Procurement Type",
        choices=[("mts", "Make to Stock"), ("mto", "Make to Order")],
    )
    source_type = SelectField(
        "Source Type",
        choices=[("purchase", "Purchase"), ("manufacture", "Manufacture")],
    )
    vendor_id = SelectField("Preferred Supplier", coerce=int, validators=[Optional()])
    lead_time_days = FloatField("Lead Time (days)", default=0)
    min_order_qty = FloatField("Min Order Qty", default=0.0)
    max_order_qty = FloatField("Max Order Qty", default=0.0)
    multiple_qty = FloatField("Multiple Qty", default=0.0)
    submit = SubmitField("Save")
