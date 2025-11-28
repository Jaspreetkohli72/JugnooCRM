import pandas as pd
import math
from fpdf import FPDF
from datetime import datetime
from io import BytesIO

# ---------------------------
# GLOBAL CONSTANTS
# ---------------------------
CONVERSIONS = {'pcs': 1.0, 'each': 1.0, 'm': 1.0, 'cm': 0.01, 'ft': 0.3048, 'in': 0.0254}
P_L_STATUS = ["Work Done", "Closed"]
ACTIVE_STATUSES = ["Estimate Given", "Order Received", "Work In Progress"]
INACTIVE_STATUSES = ["Work Done", "Closed"]

# --- PROFESSIONAL PDF GENERATOR ---
class PDFGenerator:
    def __init__(self):
        self.pdf = FPDF()

    def _add_header(self, title):
        self.pdf.add_page()
        self.pdf.set_font("Arial", 'B', 20)
        self.pdf.cell(0, 10, "Jugnoo", ln=True, align='L')
        self.pdf.set_font("Arial", 'I', 10)
        self.pdf.cell(0, 6, "Smart Automation Solutions", ln=True, align='L')
        self.pdf.line(10, 28, 200, 28)
        self.pdf.ln(15)
        self.pdf.set_font("Arial", 'B', 12)
        self.pdf.cell(0, 8, title, ln=True)
        self.pdf.set_font("Arial", '', 10)
        self.pdf.cell(0, 8, f"Date: {datetime.now().strftime('%d-%b-%Y')}", ln=True)
        self.pdf.ln(5)

    def generate_client_invoice(self, client_name, items, labor_days, labor_total, grand_total, advance_amount, is_final=False):
        title = f"INVOICE For: {client_name}" if is_final else f"Estimate For: {client_name}"
        self._add_header(title)
        
        self.pdf.set_fill_color(240, 240, 240)
        self.pdf.set_font("Arial", 'B', 10)
        self.pdf.cell(100, 10, "Description", 1, 0, 'L', 1)
        self.pdf.cell(15, 10, "Qty", 1, 0, 'C', 1)
        self.pdf.cell(15, 10, "Unit", 1, 0, 'C', 1)
        self.pdf.cell(60, 10, "Amount (INR)", 1, 1, 'R', 1)
        
        self.pdf.set_font("Arial", '', 10)
        for item in items:
            self.pdf.cell(100, 8, str(item.get('Item', '')), 1)
            self.pdf.cell(15, 8, str(item.get('Qty', 0)), 1, 0, 'C')
            self.pdf.cell(15, 8, str(item.get('Unit', '')), 1, 0, 'C')
            self.pdf.cell(60, 8, f"{item.get('Total Price', 0):,.2f}", 1, 1, 'R')
            
        self.pdf.set_font("Arial", '', 10)
        self.pdf.cell(130, 8, f"Labor / Installation ({labor_days} Days)", 1, 0, 'R')
        self.pdf.cell(60, 8, f"{labor_total:,.2f}", 1, 1, 'R')
        
        self.pdf.set_font("Arial", 'B', 12)
        self.pdf.cell(130, 10, "Grand Total", 1, 0, 'R')
        self.pdf.cell(60, 10, f"Rs. {grand_total:,.2f}", 1, 1, 'R')
        
        self.pdf.ln(10)
        self.pdf.set_font("Arial", 'B', 10)
        
        if is_final:
            self.pdf.multi_cell(0, 5, f"Total Amount: Rs. {grand_total:,.2f}")
            self.pdf.ln(5)
            self.pdf.set_font("Arial", 'I', 10)
            self.pdf.multi_cell(0, 5, "Thank you for your business!")
        else:
            self.pdf.multi_cell(0, 5, f"Advance Payment Required: Rs. {advance_amount:,.2f}")
            self.pdf.ln(5)
            self.pdf.set_font("Arial", 'I', 8)
            self.pdf.set_text_color(100, 100, 100)
            self.pdf.multi_cell(0, 5, "NOTE: This is an estimate only. Final rates may vary based on actual site conditions and market fluctuations. Valid for 7 days.")
        
        pdf_output = BytesIO()
        pdf_string = self.pdf.output(dest='S')
        pdf_output.write(pdf_string.encode('latin-1'))
        return pdf_output.getvalue()

    def generate_internal_report(self, client_name, items, labor_days, labor_cost, labor_charged, grand_total, total_profit):
        self._add_header(f"INTERNAL PROFIT REPORT (CONFIDENTIAL) - {client_name}")
        
        self.pdf.set_fill_color(220, 220, 220)
        self.pdf.set_font("Arial", 'B', 9)
        self.pdf.cell(70, 8, "Item Description", 1, 0, 'L', 1)
        self.pdf.cell(15, 8, "Qty", 1, 0, 'C', 1)
        self.pdf.cell(35, 8, "Base Rate", 1, 0, 'R', 1)
        self.pdf.cell(35, 8, "Sold At", 1, 0, 'R', 1)
        self.pdf.cell(35, 8, "Profit", 1, 1, 'R', 1)

        self.pdf.set_font("Arial", '', 9)
        for item in items:
            qty = float(item.get('Qty', 0))
            base = float(item.get('Base Rate', 0))
            total_sell = float(item.get('Total Price', 0))
            unit_sell = total_sell / qty if qty > 0 else 0
            row_profit = total_sell - (base * qty)
            
            self.pdf.cell(70, 8, str(item.get('Item', ''))[:35], 1)
            self.pdf.cell(15, 8, str(qty), 1, 0, 'C')
            self.pdf.cell(35, 8, f"{base:,.2f}", 1, 0, 'R')
            self.pdf.cell(35, 8, f"{unit_sell:,.2f}", 1, 0, 'R')
            self.pdf.set_text_color(0, 150, 0); self.pdf.cell(35, 8, f"{row_profit:,.2f}", 1, 1, 'R'); self.pdf.set_text_color(0, 0, 0)

        labor_profit = labor_charged - labor_cost
        self.pdf.ln(5)
        self.pdf.set_font("Arial", 'B', 10)
        self.pdf.cell(120, 8, f"Labor ({labor_days} Days)", 1, 0, 'R')
        self.pdf.cell(35, 8, f"Cost: {labor_cost:,.2f}", 1, 0, 'R')
        self.pdf.cell(35, 8, f"Chrg: {labor_charged:,.2f}", 1, 1, 'R')

        self.pdf.ln(10)
        self.pdf.set_font("Arial", 'B', 12)
        self.pdf.cell(120, 10, "TOTAL REVENUE:", 1, 0, 'R')
        self.pdf.cell(70, 10, f"Rs. {grand_total:,.2f}", 1, 1, 'R')
        self.pdf.cell(120, 10, "NET PROFIT:", 1, 0, 'R')
        self.pdf.set_text_color(0, 150, 0); self.pdf.cell(70, 10, f"Rs. {total_profit:,.2f}", 1, 1, 'R')

        pdf_output = BytesIO()
        pdf_string = self.pdf.output(dest='S')
        pdf_output.write(pdf_string.encode('latin-1'))
        return pdf_output.getvalue()

def create_pdf(*args, **kwargs):
    pdf_gen = PDFGenerator()
    return pdf_gen.generate_client_invoice(*args, **kwargs)

def create_internal_pdf(*args, **kwargs):
    pdf_gen = PDFGenerator()
    return pdf_gen.generate_internal_report(*args, **kwargs)


def normalize_margins(margins_data, global_settings):
    """
    Normalize margins from stored format to standard format.
    Handles both {'p': val, 'l': val, 'e': val} and {'part_margin': val, ...} formats.
    
    Args:
        margins_data: Can be None, short format {'p', 'l', 'e'}, or full format
        global_settings: The global settings dict with defaults
        
    Returns:
        dict: Standardized margins dict with 'part_margin', 'labor_margin', 'extra_margin' keys
    """
    if margins_data is None:
        return {
            'part_margin': float(global_settings.get('part_margin', 15.0)),
            'labor_margin': float(global_settings.get('labor_margin', 20.0)),
            'extra_margin': float(global_settings.get('extra_margin', 5.0))
        }
    
    # Handle short format {'p': val, 'l': val, 'e': val}
    if 'p' in margins_data or 'l' in margins_data or 'e' in margins_data:
        return {
            'part_margin': float(margins_data.get('p', global_settings.get('part_margin', 15.0))),
            'labor_margin': float(margins_data.get('l', global_settings.get('labor_margin', 20.0))),
            'extra_margin': float(margins_data.get('e', global_settings.get('extra_margin', 5.0)))
        }
    
    # Handle full format or return as-is
    return {
        'part_margin': float(margins_data.get('part_margin', global_settings.get('part_margin', 15.0))),
        'labor_margin': float(margins_data.get('labor_margin', global_settings.get('labor_margin', 20.0))),
        'extra_margin': float(margins_data.get('extra_margin', 5.0))
    }


def get_advance_percentage(settings):
    """Get advance percentage from settings"""
    return float(settings.get('advance_percentage', 10.0))


def calculate_estimate_details(edf_items_list, days, margins, global_settings):
    """
    Calculates various financial details for an estimate.
    CENTRALIZED calculation - ensures consistency across all tabs.

    Args:
        edf_items_list (list): A list of dictionaries representing the items in the estimate.
        days (float): The number of labor days for the estimate.
        margins (dict): A dictionary of margins to apply to the estimate.
        global_settings (dict): A dictionary of global settings.

    Returns:
        dict: A dictionary containing the calculated financial details.
    """
    # Normalize margins to standard format
    normalized_margins = normalize_margins(margins, global_settings)
    
    mm = 1 + (normalized_margins.get('part_margin', 0)/100) + (normalized_margins.get('labor_margin', 0)/100) + (normalized_margins.get('extra_margin', 0)/100)

    def calc_total_item(row):
        try:
            qty = float(row.get('Qty', 0))
            base = float(row.get('Base Rate', 0))
            unit_name = row.get('Unit', 'pcs')
            factor = CONVERSIONS.get(unit_name, 1.0)
            return base * qty * factor * mm
        except (ValueError, TypeError):
            return 0.0

    edf_details_df = pd.DataFrame(edf_items_list)
    if not edf_details_df.empty:
        edf_details_df['Total Price'] = edf_details_df.apply(calc_total_item, axis=1)
        edf_details_df['Unit Price'] = edf_details_df['Total Price'] / edf_details_df['Qty'].replace(0, 1)
        mat_sell = float(edf_details_df['Total Price'].sum())
    else:
        mat_sell = 0.0

    daily_labor_cost = float(global_settings.get('daily_labor_cost', 1000.0))
    labor_actual_cost = float(days) * daily_labor_cost

    def calculate_item_base_cost(row):
        qty = float(row.get('Qty', 0))
        base_rate = float(row.get('Base Rate', 0))
        unit_name = row.get('Unit', 'pcs')
        factor = CONVERSIONS.get(unit_name, 1.0)
        return base_rate * qty * factor
    
    total_material_base_cost = float(edf_details_df.apply(calculate_item_base_cost, axis=1).sum()) if not edf_details_df.empty else 0.0
    total_base_cost = total_material_base_cost + labor_actual_cost
    
    # CRITICAL: Calculate grand total and round ONCE (to nearest 100)
    raw_grand_total = mat_sell + labor_actual_cost
    rounded_grand_total = math.ceil(raw_grand_total / 100) * 100
    
    # CRITICAL: Profit must be calculated from ROUNDED grand total for consistency
    total_profit = rounded_grand_total - total_base_cost
    
    # CRITICAL: Advance uses ROUNDED grand total and profit calculation
    advance_amount = math.ceil((total_base_cost + (total_profit * 0.10)) / 100) * 100
    
    # Labor display includes rounding difference
    disp_lt = labor_actual_cost + (rounded_grand_total - raw_grand_total)

    return {
        "mat_sell": mat_sell,
        "labor_actual_cost": labor_actual_cost,
        "rounded_grand_total": rounded_grand_total,
        "total_profit": total_profit,
        "advance_amount": advance_amount,
        "disp_lt": disp_lt,
        "edf_details_df": edf_details_df
    }

def calculate_profit_row(row):
    """Calculates the profit for a single row in an estimate."""
    qty = float(row.get('Qty', 0))
    base_rate = float(row.get('Base Rate', 0))
    unit = row.get('Unit', 'pcs')
    total_sell = float(row.get('Total Sell Price', 0))
    factor = CONVERSIONS.get(unit, 1.0)
    total_cost = base_rate * qty * factor
    return total_sell - total_cost

def create_item_dataframe(items):
    """
    Creates and validates a DataFrame for items.

    Args:
        items (list): A list of item dictionaries.

    Returns:
        pd.DataFrame: A validated DataFrame with the required columns.
    """
    df = pd.DataFrame(items)
    for col in ["Qty", "Item", "Unit", "Base Rate", "Total Price", "Unit Price"]:
        if col not in df.columns:
            df[col] = "" if col in ["Item", "Unit"] else 0.0
    column_order = ['Qty', 'Item', 'Unit', 'Base Rate', 'Unit Price', 'Total Price']
    df = df.reindex(columns=column_order, fill_value="")
    return df
