from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil import parser
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Invoice(BaseModel):
    invoice_text: str


def extract_amount(pattern, text):
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return None

    value = m.group(1)
    value = value.replace(",", "")
    return float(value)


@app.post("/extract")
def extract(data: Invoice):

    text = data.invoice_text

    invoice_no = None
    date = None
    vendor = None
    amount = None
    tax = None
    currency = "INR"

    m = re.search(r"Invoice\s*No[:#]?\s*(.+)", text, re.IGNORECASE)
    if m:
        invoice_no = m.group(1).strip()

    m = re.search(r"Date[:#]?\s*(.+)", text, re.IGNORECASE)
    if m:
        try:
            date = parser.parse(m.group(1).strip()).date().isoformat()
        except:
            pass

    m = re.search(r"Vendor[:#]?\s*(.+)", text, re.IGNORECASE)
    if m:
        vendor = m.group(1).strip()

    amount = extract_amount(
        r"Subtotal[: ]*Rs\.?\s*([\d,]+\.\d+)",
        text
    )

    tax = extract_amount(
        r"(?:GST|Tax).*?Rs\.?\s*([\d,]+\.\d+)",
        text
    )

    return {
        "invoice_no": invoice_no,
        "date": date,
        "vendor": vendor,
        "amount": amount,
        "tax": tax,
        "currency": currency
    }