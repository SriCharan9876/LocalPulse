"""
LocalPulse AI Copilot Agent Tools Schema & Registry.
Declares tools for LLM Function Calling and deterministic parameter parsing.
"""

from typing import List, Dict, Any

# Tool definition catalog in JSON Schema / OpenAI & Gemini compatible structure
COPILOT_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "analyze_product_performance",
        "description": "Analyze sales velocity, revenue, unit trends, and stock runway for a specific product over the last X days.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Name or keyword of the product in the catalog (e.g. 'Milk', 'Bread', 'Tea')."
                },
                "days": {
                    "type": "integer",
                    "description": "Number of past days to analyze (default is 7 or 30).",
                    "default": 7
                }
            },
            "required": ["product_name"]
        }
    },
    {
        "name": "get_restock_recommendations",
        "description": "Scan inventory for products below safety reorder threshold or at stockout risk, with projected replenishment units.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Optional category filter (e.g. 'Dairy', 'Bakery', 'Beverages')."
                }
            }
        }
    },
    {
        "name": "get_discount_recommendations",
        "description": "Identify products needing promotional clearance (slow-moving items or excess stock) and recommend optimal discount percentages to preserve profit margin.",
        "parameters": {
            "type": "object",
            "properties": {
                "max_discount_pct": {
                    "type": "number",
                    "description": "Maximum allowed discount percentage (default 15%).",
                    "default": 15.0
                }
            }
        }
    },
    {
        "name": "adjust_inventory_stock",
        "description": "Propose an inventory stock adjustment or replenishment order for a specific product.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Name or keyword of the product to adjust."
                },
                "quantity": {
                    "type": "integer",
                    "description": "Number of units to add (restock) or deduct (audit adjustment)."
                },
                "adjustment_type": {
                    "type": "string",
                    "enum": ["RESTOCK", "DAMAGE_WRITE_OFF", "AUDIT_CORRECTION"],
                    "description": "Reason for the stock change (default 'RESTOCK').",
                    "default": "RESTOCK"
                },
                "notes": {
                    "type": "string",
                    "description": "Explanation or context for the adjustment movement."
                }
            },
            "required": ["product_name", "quantity"]
        }
    },
    {
        "name": "add_catalog_product",
        "description": "Propose adding a brand new product SKU to the merchant catalog.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Product name (e.g. 'Oat Milk 1L')."
                },
                "category": {
                    "type": "string",
                    "description": "Product category (e.g. 'Dairy', 'Beverages', 'Grocery')."
                },
                "cost_price": {
                    "type": "number",
                    "description": "Purchase / wholesale cost price in ₹."
                },
                "selling_price": {
                    "type": "number",
                    "description": "Retail selling price in ₹."
                },
                "initial_stock": {
                    "type": "integer",
                    "description": "Initial stock quantity (default 20).",
                    "default": 20
                },
                "reorder_threshold": {
                    "type": "integer",
                    "description": "Safety threshold count below which restock alerts trigger (default 10).",
                    "default": 10
                },
                "unit": {
                    "type": "string",
                    "description": "Unit of measurement (e.g. 'packs', 'bottles', 'kg', 'units').",
                    "default": "units"
                }
            },
            "required": ["name", "cost_price", "selling_price"]
        }
    },
    {
        "name": "create_promotional_campaign",
        "description": "Draft a promotional discount or marketing campaign for one or more products.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Campaign title (e.g. 'Weekend Chai Special')."
                },
                "product_name": {
                    "type": "string",
                    "description": "Target product name or keyword."
                },
                "discount_pct": {
                    "type": "number",
                    "description": "Discount percentage to offer (e.g. 5, 10, 15)."
                },
                "duration_days": {
                    "type": "integer",
                    "description": "Campaign duration in days (default 7).",
                    "default": 7
                },
                "budget": {
                    "type": "number",
                    "description": "Budget allocated in ₹ (default 1000).",
                    "default": 1000.0
                }
            },
            "required": ["title"]
        }
    },
    {
        "name": "end_promotional_campaign",
        "description": "End or cancel an ongoing active promotional campaign and restore standard product retail prices.",
        "parameters": {
            "type": "object",
            "properties": {
                "campaign_title_or_id": {
                    "type": "string",
                    "description": "Title, keyword, or ID of the active campaign to conclude."
                }
            },
            "required": ["campaign_title_or_id"]
        }
    },
    {
        "name": "get_business_overview",
        "description": "Provide a comprehensive snapshot of overall store revenue, active catalog counts, low stock warnings, and active promotions.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
]
