"""
LocalPulse AI Copilot Agent Tools Schema & Registry.
Declares tools for LLM Function Calling and deterministic parameter parsing.
"""

from typing import List, Dict, Any

# Tool definition catalog in JSON Schema / OpenAI & Gemini compatible structure
COPILOT_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_catalog_products",
        "description": "List all products in the merchant's catalog with current stock levels, retail selling prices, cost prices, and categories. Use when asked 'list down all the products i have', 'show all products', 'what products do i have', 'my catalog', 'inventory list'.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Optional category filter (e.g. 'Dairy', 'Flour & Grains', 'Edible Oils')."
                }
            }
        }
    },
    {
        "name": "analyze_product_performance",
        "description": "Analyze sales velocity, revenue, unit trends, and stock runway for ONE specific product over a period. For rankings across products use get_top_products.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Name or keyword of the product in the catalog (e.g. 'Milk', 'Bread', 'Tea')."
                },
                "auto_select": {
                    "type": "string",
                    "enum": ["top_seller"],
                    "description": "Use 'top_seller' when the merchant refers to their top/best product without naming it."
                },
                "period": {
                    "type": "string",
                    "description": "Time period exactly as the merchant said it, e.g. 'today', 'yesterday', 'last 5 days', 'this week', 'last month'. Omit if none was mentioned."
                },
                "days": {
                    "type": "integer",
                    "description": "Number of past days to analyze (default is 7 or 30).",
                    "default": 7
                }
            }
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
                "auto_select": {
                    "type": "string",
                    "enum": ["most_urgent_restock"],
                    "description": "Use 'most_urgent_restock' when the merchant asks to restock their lowest / most urgent item without naming it."
                },
                "quantity": {
                    "type": "integer",
                    "description": "Number of units to add (restock) or deduct (audit adjustment)."
                },
                "adjustment_type": {
                    "type": "string",
                    "enum": ["RESTOCK", "DAMAGE_LOSS", "AUDIT_CORRECTION"],
                    "description": "Reason for the stock change (default 'RESTOCK').",
                    "default": "RESTOCK"
                },
                "notes": {
                    "type": "string",
                    "description": "Explanation or context for the adjustment movement."
                }
            },
            "required": ["quantity"]
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
                "auto_select": {
                    "type": "string",
                    "enum": ["best_promo_candidate"],
                    "description": "Use 'best_promo_candidate' when no product is named; the product with the most surplus stock that can afford the discount is chosen."
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
        "name": "get_top_products",
        "description": "Rank ALL products by units sold, revenue, or profit over a period. Use for: most sold / best sellers / top products / which product sold the most / least sold / slowest / not selling.",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "Time period exactly as the merchant said it, e.g. 'today', 'yesterday', 'last 5 days', 'this week', 'last month'. Omit if none was mentioned."
                },
                "rank_by": {
                    "type": "string",
                    "enum": ["units", "revenue", "profit"],
                    "description": "What to rank by (default 'units'). Use 'revenue' for money/earnings questions, 'profit' for profit/margin questions."
                },
                "order": {
                    "type": "string",
                    "enum": ["top", "bottom"],
                    "description": "'top' for best/most sold, 'bottom' for least sold / slow / not selling (default 'top')."
                },
                "limit": {
                    "type": "integer",
                    "description": "How many products to list (default 5)."
                }
            }
        }
    },
    {
        "name": "get_sales_summary",
        "description": "Store-wide sales totals for a period: revenue, units, gross profit, daily average, best day, top product, and change vs the previous period. Use for: how much did I sell / revenue yesterday / sales this week / profit last month / how did the store do.",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "Time period exactly as the merchant said it, e.g. 'today', 'yesterday', 'last 5 days', 'this week', 'last month'. Omit if none was mentioned."
                }
            }
        }
    },
    {
        "name": "compare_products",
        "description": "Compare two or more named products side by side (units, revenue, profit, trend, stock) over a period.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Names or keywords of the products to compare (at least two)."
                },
                "period": {
                    "type": "string",
                    "description": "Time period exactly as the merchant said it, e.g. 'today', 'yesterday', 'last 5 days', 'this week', 'last month'. Omit if none was mentioned."
                }
            },
            "required": ["product_names"]
        }
    },
    {
        "name": "get_business_overview",
        "description": "Provide a comprehensive snapshot of overall store revenue, active catalog counts, low stock warnings, and active promotions.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_nearby_merchants",
        "description": "Find and list neighborhood stores and partner shops near the merchant's shop, with real-world distance in km/meters, category synergy, and top catalog items.",
        "parameters": {
            "type": "object",
            "properties": {
                "radius_km": {
                    "type": "number",
                    "description": "Maximum distance radius in kilometers (e.g. 0.5, 1.0, 2.0)."
                },
                "category": {
                    "type": "string",
                    "description": "Optional category filter for nearby stores (e.g. 'Cafe & Bakery', 'Grocery', 'Pharmacy')."
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of nearby stores to return (default 5).",
                    "default": 5
                }
            }
        }
    },
    {
        "name": "get_upcoming_events",
        "description": "Query upcoming All-India occasions, religious festivals (Diwali, Holi, Eid, Pongal, Christmas), and local events from the neighborhood calendar, with proximity and category demand impacts.",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of upcoming days to scan (default 30).",
                    "default": 30
                },
                "category": {
                    "type": "string",
                    "description": "Optional merchant category filter to see events specifically impacting that category (e.g. 'Dairy', 'Sweets', 'Bakery')."
                }
            }
        }
    },
    {
        "name": "get_event_action_plan",
        "description": "Generate an actionable preparation plan for a specific upcoming festival or event, including restock recommendations for high-demand items, festival discount offers, and neighbor bundle ideas.",
        "parameters": {
            "type": "object",
            "properties": {
                "occasion_name": {
                    "type": "string",
                    "description": "Name of the occasion or festival (e.g. 'Diwali', 'Holi', 'Eid', 'Pongal', 'Christmas')."
                }
            },
            "required": ["occasion_name"]
        }
    },
    {
        "name": "discover_collaboration_partners",
        "description": "Discover nearby partner merchants and recommended cross-store combo/bundle ideas ranked by complementary synergy score, buy-together link, and margin safety.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Optional target product from the merchant's catalog to find bundle partners for (e.g. 'Chai', 'Milk')."
                },
                "partner_category": {
                    "type": "string",
                    "description": "Optional partner category filter (e.g. 'Cafe & Bakery', 'Sweets')."
                }
            }
        }
    },
    {
        "name": "create_collaboration_proposal",
        "description": "Draft a collaborative joint bundle proposal with a nearby partner merchant to submit for mutual approval.",
        "parameters": {
            "type": "object",
            "properties": {
                "partner_name": {
                    "type": "string",
                    "description": "Name or keyword of the nearby partner merchant (e.g. 'Krishna Bakery', 'Nilgiri Dairy')."
                },
                "my_product_name": {
                    "type": "string",
                    "description": "Name or keyword of your product for the bundle."
                },
                "partner_product_name": {
                    "type": "string",
                    "description": "Name or keyword of the partner store's product."
                },
                "bundle_name": {
                    "type": "string",
                    "description": "Title or theme for the joint combo bundle (e.g. 'Morning Tea & Rusk Combo')."
                },
                "discount_pct": {
                    "type": "number",
                    "description": "Discount percentage to offer on the bundle (e.g. 10.0, 12.0).",
                    "default": 10.0
                },
                "duration_days": {
                    "type": "integer",
                    "description": "Proposed duration in days (default 14).",
                    "default": 14
                }
            },
            "required": ["partner_name"]
        }
    },
    {
        "name": "get_demand_forecast",
        "description": "Generate forward-looking 7-day or 14-day demand forecast for one or all products using weekday trends and upcoming event multipliers, highlighting projected units, projected revenue, and stockout risks.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Optional product name or keyword to forecast. If omitted or 'all', generates a store-wide batch forecast."
                },
                "days": {
                    "type": "integer",
                    "description": "Forecast horizon in days (default 7, max 14).",
                    "default": 7
                }
            }
        }
    }
]
