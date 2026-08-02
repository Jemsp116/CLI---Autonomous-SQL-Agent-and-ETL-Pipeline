from __future__ import annotations

from textwrap import dedent

SCHEMA_DESCRIPTION = dedent(
    """
    Database schema:
    - invoices(id, invoice_number, date_of_issue, seller_name, seller_address, seller_tax_id, seller_gstin, client_name, client_address, client_tax_id)
    - line_items(id, invoice_id, item_no, description, qty, unit, net_price, net_worth, vat_pct, gross_worth)

    Relationships:
    - line_items.invoice_id -> invoices.id

    Query rules:
    - Use SELECT-only SQL.
    - Treat the database as read-only.
    - Prefer joins through invoices.id = line_items.invoice_id.
    - Use gross_worth for sales including VAT and net_worth for sales before VAT.
    - Use SUM(qty), SUM(net_worth), SUM(gross_worth), COUNT(*), GROUP BY, ORDER BY, and LIMIT as needed.
    """
).strip()

FEW_SHOT_EXAMPLES = dedent(
    """
    Example 1:
    Question: How much total quantity we sold for Sony Bravia 55 inch 4K OLED TV?
    Reasoning summary: Sum the quantity for matching line items in line_items.
    SQL:
    SELECT SUM(qty) AS total_qty
    FROM line_items
    WHERE description = 'Sony Bravia 55 inch 4K OLED TV';

    Example 2:
    Question: How much total sales we made for Sony Bravia 55 inch 4K OLED TV without vat added?
    Reasoning summary: Sum the net worth for matching line items.
    SQL:
    SELECT SUM(net_worth) AS total_sales
    FROM line_items
    WHERE description = 'Sony Bravia 55 inch 4K OLED TV';

    Example 3:
    Question: Which product/description is most sold in terms of gross worth?
    Reasoning summary: Aggregate gross worth by description and return the highest total.
    SQL:
    SELECT description, SUM(gross_worth) AS total_gross
    FROM line_items
    GROUP BY description
    ORDER BY total_gross DESC
    LIMIT 1;

    Example 4:
    Question: Which client has the highest total spend?
    Reasoning summary: Join invoices to line_items and sum gross worth by client.
    SQL:
    SELECT i.client_name, SUM(li.gross_worth) AS total_spend
    FROM invoices AS i
    JOIN line_items AS li ON li.invoice_id = i.id
    GROUP BY i.client_name
    ORDER BY total_spend DESC
    LIMIT 1;
    """
).strip()

SYSTEM_PROMPT_TEMPLATE = dedent(
    """
    You are a precise SQL analyst for a read-only invoice database.

    {schema_description}

    {few_shot_examples}

    Response format rules:
    - Return JSON only.
    - Include keys: reasoning_summary, sql_query.
    - reasoning_summary must be short and concrete.
    - sql_query must be a single SELECT statement with no markdown fences.
    - If the question cannot be answered from the schema, explain that in reasoning_summary and produce the best SELECT query you can.
    """
).strip()

FULL_INVOICE_EXTRACTION_PROMPT = dedent(
        """
        Extract structured invoice data from the provided invoice text.

        Return JSON only with this shape:
        {{
            "header": {{
                "invoice_no": "",
                "date_of_issue": "",
                "seller_name": "",
                "seller_address": "",
                "seller_tax_id": "",
                "seller_gstin": "",
                "client_name": "",
                "client_address": "",
                "client_tax_id": ""
            }},
            "line_items": [
                {{
                    "invoice_no": "",
                    "item_no": "",
                    "description": "",
                    "qty": null,
                    "unit": "",
                    "net_price": null,
                    "net_worth": null,
                    "vat_pct": "",
                    "gross_worth": null
                }}
            ],
            "summary": {{
                "invoice_no": "",
                "vat_pct": "",
                "total_net_worth": null,
                "total_vat": null,
                "total_gross_worth": null
            }}
        }}

        Rules:
        - Use empty strings when a text field is missing.
        - Use null when a numeric field is missing.
        - Preserve the invoice number in header, line_items, and summary.
        - Do not add commentary or markdown fences.

        Invoice text:
        {invoice_text}
        """
).strip()


def build_system_prompt(table_info: str) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        schema_description=f"{SCHEMA_DESCRIPTION}\n\nTable info:\n{table_info}",
        few_shot_examples=FEW_SHOT_EXAMPLES,
    )
