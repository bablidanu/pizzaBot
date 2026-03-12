import os
import json
import panel as pn  # GUI — must be imported before use
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI

# Load environment variables
_ = load_dotenv(find_dotenv())

# Initialize client with API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

pn.extension()

# ── Core API helpers ──────────────────────────────────────────────────────────

def get_completion(prompt, model="gpt-3.5-turbo"):
    """Single-turn completion (no conversation history)."""
    messages = [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
    )
    return response.choices[0].message.content  # FIX: .content not ["content"]


def get_completion_from_messages(messages, model="gpt-3.5-turbo", temperature=0):
    """Multi-turn completion using a full message history."""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content  # FIX: .content not ["content"]


# ── Pizza-only system prompt ──────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are PizzaBot, an automated ordering service for Mario's Pizza Palace.
Your job is ONLY to take pizza orders — do not discuss anything else.

Greet the customer warmly, then guide them through:
1. Choosing their pizza(s) from the menu below.
2. Selecting size (Small / Medium / Large) for each pizza.
3. Adding any toppings they'd like.
4. Adding drinks or sides if they want.
5. Asking: pickup or delivery? (If delivery, get their address.)
6. Summarising the full order and confirming with the customer.
7. Collecting payment method (cash / card / upi).

Always clarify size and any extras before adding an item to the order.
Be friendly, concise, and emoji-friendly 🍕.
If the customer asks about anything unrelated to pizza ordering, politely redirect them.

━━━━━━━━━━  MENU  ━━━━━━━━━━

PIZZAS (Small $7 / Medium $10 / Large $13):
  • Margherita
  • Pepperoni
  • BBQ Chicken
  • Veggie Supreme
  • Four Cheese
  • Meat Lovers

EXTRA TOPPINGS (+$1.50 each):
  Extra Cheese | Mushrooms | Jalapeños | Olives | Sun-dried Tomatoes | Bacon

SIDES:
  • Garlic Bread   $3.50
  • Caesar Salad   $6.50
  • Chicken Wings (6pc)  $8.00

DRINKS:
  • Coke / Diet Coke / Sprite  (Small $1.50 / Medium $2.50 / Large $3.50)
  • Bottled Water  $2.50
  • Fresh OJ  $4.00

━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# ── Panel UI state ────────────────────────────────────────────────────────────

panels = []

context = [{"role": "system", "content": SYSTEM_PROMPT}]


def collect_messages(_):
    """Called each time the Chat button is clicked."""
    prompt = inp.value_input
    if not prompt.strip():
        return pn.Column(*panels)

    inp.value = ""
    context.append({"role": "user", "content": prompt})  # FIX: removed redundant f-string

    try:
        response = get_completion_from_messages(context)
    except Exception as e:  # FIX: added basic error handling
        response = f"⚠️ Sorry, something went wrong: {e}"

    context.append({"role": "assistant", "content": response})  # FIX: removed redundant f-string

    panels.append(pn.Row("🧑 You:", pn.pane.Markdown(prompt, width=550)))
    panels.append(
        pn.Row(
            "🍕 PizzaBot:",
            pn.pane.Markdown(
                response,
                width=550,
                styles={"background-color": "#FFF8F0", "border-radius": "8px", "padding": "8px"},  # FIX: styles= not style=
            ),
        )
    )
    return pn.Column(*panels)


def get_order_summary(_):
    """Generate a structured JSON summary of the order so far."""
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
        formatted = json.dumps(parsed, indent=2)
    except Exception as e:
        formatted = f"Could not parse order summary: {e}\n\nRaw response:\n{raw}"

    summary_panel.object = f"```json\n{formatted}\n```"


# ── Dashboard layout ──────────────────────────────────────────────────────────

inp = pn.widgets.TextInput(placeholder="Type your order here… (e.g. 'Hi, I'd like a pizza')")
button_chat = pn.widgets.Button(name="Send 💬", button_type="primary")
button_summary = pn.widgets.Button(name="Get Order Summary 🧾", button_type="success")
summary_panel = pn.pane.Markdown("*Click 'Get Order Summary' after placing your order.*")

interactive_conversation = pn.bind(collect_messages, button_chat)
pn.bind(get_order_summary, button_summary, watch=True)

dashboard = pn.Column(
    pn.pane.Markdown("# 🍕 Mario's Pizza Palace — PizzaBot"),
    pn.pane.Markdown("*Chat with PizzaBot to place your order, then click 'Get Order Summary' when done.*"),
    pn.Row(inp, button_chat),
    pn.panel(interactive_conversation, loading_indicator=True, height=400),
    pn.layout.Divider(),
    pn.Row(button_summary),
    summary_panel,
)

dashboard.servable()
