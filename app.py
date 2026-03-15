import os
import json
import panel as pn
from dotenv import load_dotenv, find_dotenv
from groq import Groq

# ━━━━━━━━━━━ LOAD ENV ━━━━━━━━━━━
_ = load_dotenv(find_dotenv())
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("❌ GROQ_API_KEY missing! Create .env file with: GROQ_API_KEY=your_key_here")

pn.extension()



# ━━━━━━━━━━━ GROQ HELPER ━━━━━━━━━━━
def get_completion_from_messages(messages, model="llama3-8b-8192", temperature=0):
    client = Groq(api_key=api_key)  # ✅ Initialize client here
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content

# ━━━━━━━━━━━ MENU DATA ━━━━━━━━━━━
MENU = {
    "pizzas": {
        "Margherita":     {"Small": 7,  "Medium": 10, "Large": 13},
        "Pepperoni":      {"Small": 7,  "Medium": 10, "Large": 13},
        "BBQ Chicken":    {"Small": 7,  "Medium": 10, "Large": 13},
        "Veggie Supreme": {"Small": 7,  "Medium": 10, "Large": 13},
        "Four Cheese":    {"Small": 7,  "Medium": 10, "Large": 13},
        "Meat Lovers":    {"Small": 7,  "Medium": 10, "Large": 13},
    },
    "extra_toppings": 1.50,
    "sides": {
        "Garlic Bread":        3.50,
        "Caesar Salad":        6.50,
        "Chicken Wings (6pc)": 8.00,
    },
    "drinks": {
        "Coke":          {"Small": 1.50, "Medium": 2.50, "Large": 3.50},
        "Diet Coke":     {"Small": 1.50, "Medium": 2.50, "Large": 3.50},
        "Sprite":        {"Small": 1.50, "Medium": 2.50, "Large": 3.50},
        "Bottled Water": {"One Size": 2.50},
        "Fresh OJ":      {"One Size": 4.00},
    },
}

# ━━━━━━━━━━━ SYSTEM PROMPT ━━━━━━━━━━━
SYSTEM_PROMPT = """
You are PizzaBot, an automated ordering service for Mario's Pizza Palace.
Your job is ONLY to take pizza orders — do not discuss anything else.

Greet the customer warmly when they arrive.
Take their full order: pizza name, size, any extra toppings, sides, and drinks.
Ask whether they want delivery or pickup.
If delivery, ask for their address.
Ask for payment method (cash or card).
Confirm the complete order with total cost before finishing.

Menu:

Pizzas (all available in Small $7 | Medium $10 | Large $13):
  - Margherita
  - Pepperoni
  - BBQ Chicken
  - Veggie Supreme
  - Four Cheese
  - Meat Lovers
  Extra toppings: $1.50 each

Sides:
  - Garlic Bread         $3.50
  - Caesar Salad         $6.50
  - Chicken Wings (6pc)  $8.00

Drinks:
  - Coke / Diet Coke / Sprite  Small $1.50 | Medium $2.50 | Large $3.50
  - Bottled Water              $2.50
  - Fresh OJ                   $4.00

Always be polite, clear, and concise. Use a warm, conversational tone.
"""

# Hardcoded greeting — shown immediately with zero API calls on load
GREETING = "👋 Welcome to Mario's Pizza Palace! I'm PizzaBot. What can I get for you today? 🍕"



# ━━━━━━━━━━━ PRICE VALIDATOR ━━━━━━━━━━━
def validate_order_prices(order_json):
    total = 0.0
    for pizza in order_json.get("pizzas", []):
        name, size = pizza.get("name"), pizza.get("size")
        toppings = pizza.get("extra_toppings", [])
        if name in MENU["pizzas"] and size in MENU["pizzas"][name]:
            base_price = MENU["pizzas"][name][size]
            topping_price = len(toppings) * MENU["extra_toppings"]
            pizza["price"] = base_price + topping_price
            total += pizza["price"]
    for side in order_json.get("sides", []):
        if side["name"] in MENU["sides"]:
            side["price"] = MENU["sides"][side["name"]]
            total += side["price"]
    for drink in order_json.get("drinks", []):
        name, size = drink.get("name"), drink.get("size")
        if name in MENU["drinks"]:
            if size and size in MENU["drinks"][name]:
                drink["price"] = MENU["drinks"][name][size]
            elif "One Size" in MENU["drinks"][name]:
                drink["price"] = MENU["drinks"][name]["One Size"]
            total += drink.get("price", 0)
    order_json["total_price"] = round(total, 2)
    return order_json

# ━━━━━━━━━━━ RECEIPT GENERATOR ━━━━━━━━━━━
def generate_receipt(order_json):
    lines = ["### 🧾 Order Receipt", ""]
    if order_json.get("pizzas"):
        lines.append("**Pizzas:**")
        for p in order_json["pizzas"]:
            toppings = ", ".join(p.get("extra_toppings", [])) or "No extras"
            lines.append(f"- {p['size']} {p['name']} ({toppings}) — ${p['price']:.2f}")
        lines.append("")
    if order_json.get("sides"):
        lines.append("**Sides:**")
        for s in order_json["sides"]:
            lines.append(f"- {s['name']} — ${s['price']:.2f}")
        lines.append("")
    if order_json.get("drinks"):
        lines.append("**Drinks:**")
        for d in order_json["drinks"]:
            size = d.get("size", "")
            lines.append(f"- {size} {d['name']} — ${d['price']:.2f}")
        lines.append("")
    lines.append(f"**Total: ${order_json.get('total_price', 0):.2f}**")
    return "\n".join(lines)

# ━━━━━━━━━━━ BOT MESSAGE STYLE ━━━━━━━━━━━
def bot_msg(text):
    return pn.Row(
        "🍕 PizzaBot:",
        pn.pane.Markdown(
            text, width=550,
            styles={"background-color": "#FFF8F0", "border-radius": "8px", "padding": "8px"},
        )
    )

def user_msg(text):
    return pn.Row("🧑 You:", pn.pane.Markdown(text, width=550))

# ━━━━━━━━━━━ STATE ━━━━━━━━━━━
# Pre-load context with the hardcoded greeting so the conversation
# history is consistent — no API call needed on load
context = [
    {"role": "system",    "content": SYSTEM_PROMPT},
    {"role": "assistant", "content": GREETING},
]
panels = [bot_msg(GREETING)]  # show greeting immediately on page load
chat_box = pn.Column(*panels, sizing_mode="stretch_width", height=400, scroll=True)

# ━━━━━━━━━━━ UI WIDGETS ━━━━━━━━━━━
inp            = pn.widgets.TextInput(
                    placeholder="Type your order here… (e.g. 'Hi, I'd like a pizza')",
                    sizing_mode="stretch_width",
                 )
button_chat    = pn.widgets.Button(name="Send 💬",              button_type="primary")
button_summary = pn.widgets.Button(name="Get Order Summary 🧾", button_type="success")
summary_panel  = pn.pane.Markdown("*Click 'Get Order Summary' after placing your order.*")

# ━━━━━━━━━━━ CALLBACKS ━━━━━━━━━━━
def collect_messages(_):
    prompt = inp.value.strip()
    if not prompt:
        return
    inp.value = ""
    context.append({"role": "user", "content": prompt})
    try:
        response = get_completion_from_messages(context)
    except Exception as e:
        response = f"⚠️ Sorry, something went wrong: {e}"
    context.append({"role": "assistant", "content": response})
    panels.append(user_msg(prompt))
    panels.append(bot_msg(response))
    chat_box.objects = list(panels)


def get_order_summary(_):
    summary_panel.object = "⏳ *Generating your order summary…*"
    summary_messages = context.copy()
    summary_messages.append({
        "role": "system",
        "content": (
            "Based on the conversation so far, create a JSON summary of the pizza order. "
            "Return ONLY valid JSON with these fields: "
            "1) pizzas (list of {name, size, extra_toppings, price}), "
            "2) sides (list of {name, price}), "
            "3) drinks (list of {name, size, price}), "
            "4) delivery (true/false), "
            "5) address (string or null), "
            "6) payment_method (string or null), "
            "7) total_price (number). "
            "If the order is incomplete, fill what you can and use null for unknowns."
        ),
    })
    try:
        raw = get_completion_from_messages(summary_messages, temperature=0)
        parsed = json.loads(raw)
        validated = validate_order_prices(parsed)
        formatted_json = json.dumps(validated, indent=2)
        receipt = generate_receipt(validated)
        summary_panel.object = f"```json\n{formatted_json}\n```\n\n{receipt}"
    except Exception as e:
        summary_panel.object = f"⚠️ Could not generate summary: {e}"


button_chat.on_click(collect_messages)
button_summary.on_click(get_order_summary)

# ━━━━━━━━━━━ DASHBOARD ━━━━━━━━━━━
dashboard = pn.Column(
    pn.pane.Markdown("# 🍕 Mario's Pizza Palace — PizzaBot"),
    pn.pane.Markdown("*Chat with PizzaBot to place your order, then click 'Get Order Summary' when done.*"),
    pn.Row(inp, button_chat),
    chat_box,
    pn.layout.Divider(),
    pn.Row(button_summary),
    summary_panel,
)

dashboard.servable()
