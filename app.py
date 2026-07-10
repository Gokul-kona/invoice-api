from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil import parser
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Invoice(BaseModel):
    invoice_text: str


def extract_amount(pattern, text):
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None

    value = m.group(1)
    value = value.replace(",", "").replace(" ", "")

    try:
        return float(value)
    except:
        return None


@app.post("/extract")
def extract(data: Invoice):

    text = data.invoice_text

    invoice_no = None
    date = None
    vendor = None
    amount = None
    tax = None
    currency = None

    # ---------------- Invoice Number ----------------

    invoice_patterns = [
        r"Invoice\s*No\.?\s*[:#]?\s*([^\n\r]+)",
        r"Invoice\s*#\s*[:#]?\s*([^\n\r]+)",
        r"Invoice\s*Number\s*[:#]?\s*([^\n\r]+)",
        r"Ref(?:erence)?\s*[:#]?\s*([^\n\r]+)",
    ]

    for p in invoice_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            invoice_no = m.group(1).strip()
            break

    # ---------------- Date ----------------

    date_patterns = [
        r"Date\s*[:#]?\s*([^\n\r]+)",
        r"Issued\s*[:#]?\s*([^\n\r]+)",
        r"Invoice\s*Date\s*[:#]?\s*([^\n\r]+)",
    ]

    for p in date_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            try:
                date = parser.parse(
                    m.group(1).strip(),
                    dayfirst=True
                ).date().isoformat()
            except:
                pass
            break

    # ---------------- Vendor ----------------

    vendor_patterns = [
        r"Vendor\s*[:#]?\s*([^\n\r]+)",
        r"Supplier\s*[:#]?\s*([^\n\r]+)",
        r"Seller\s*[:#]?\s*([^\n\r]+)",
        r"Sold\s*By\s*[:#]?\s*([^\n\r]+)",
        r"Merchant\s*[:#]?\s*([^\n\r]+)",
        r"Company\s*[:#]?\s*([^\n\r]+)",
        r"From\s*[:#]?\s*([^\n\r]+)",
    ]

    for p in vendor_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            vendor = m.group(1).strip()
            break

    # ---------------- Amount ----------------

    amount_patterns = [
        r"Subtotal.*?Rs\.?\s*([\d,]+(?:\.\d+)?)",
        r"Sub\s*Total.*?Rs\.?\s*([\d,]+(?:\.\d+)?)",
        r"Amount\s*Before\s*Tax.*?Rs\.?\s*([\d,]+(?:\.\d+)?)",
        r"Net\s*Amount.*?Rs\.?\s*([\d,]+(?:\.\d+)?)",
        r"Subtotal.*?\$([\d,]+(?:\.\d+)?)",
        r"Subtotal.*?₹\s*([\d,]+(?:\.\d+)?)",
    ]

    for p in amount_patterns:
        amount = extract_amount(p, text)
        if amount is not None:
            break

    # ---------------- Tax ----------------

    tax_patterns = [
        r"GST.*?Rs\.?\s*([\d,]+(?:\.\d+)?)",
        r"IGST.*?Rs\.?\s*([\d,]+(?:\.\d+)?)",
        r"CGST.*?Rs\.?\s*([\d,]+(?:\.\d+)?)",
        r"SGST.*?Rs\.?\s*([\d,]+(?:\.\d+)?)",
        r"VAT.*?Rs\.?\s*([\d,]+(?:\.\d+)?)",
        r"Tax.*?Rs\.?\s*([\d,]+(?:\.\d+)?)",
        r"GST.*?\$([\d,]+(?:\.\d+)?)",
        r"Tax.*?\$([\d,]+(?:\.\d+)?)",
    ]

    for p in tax_patterns:
        tax = extract_amount(p, text)
        if tax is not None:
            break

    # ---------------- Currency ----------------

    m = re.search(
        r"Currency\s*[:#]?\s*([A-Za-z]{3})",
        text,
        re.IGNORECASE
    )

    if m:
        currency = m.group(1).upper()

    elif "₹" in text or "Rs." in text or "Rs " in text:
        currency = "INR"

    elif "$" in text:
        currency = "USD"

    elif "€" in text:
        currency = "EUR"

    elif "£" in text:
        currency = "GBP"

    return {
        "invoice_no": invoice_no,
        "date": date,
        "vendor": vendor,
        "amount": amount,
        "tax": tax,
        "currency": currency
    }