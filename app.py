from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)


def get_database():
    connection = sqlite3.connect("food_data.db")
    connection.row_factory = sqlite3.Row
    return connection


# =====================================
# HOME PAGE
# =====================================

@app.route("/")
def home():

    connection = get_database()

    entries = connection.execute(
        "SELECT * FROM food_entries ORDER BY id DESC"
    ).fetchall()

    redistributions = connection.execute(
        "SELECT * FROM redistributions ORDER BY id DESC"
    ).fetchall()

    total_prepared = connection.execute(
        "SELECT COALESCE(SUM(prepared), 0) FROM food_entries"
    ).fetchone()[0]

    total_consumed = connection.execute(
        "SELECT COALESCE(SUM(consumed), 0) FROM food_entries"
    ).fetchone()[0]

    total_surplus = connection.execute(
        "SELECT COALESCE(SUM(surplus), 0) FROM food_entries"
    ).fetchone()[0]

    total_redistributed = connection.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM redistributions"
    ).fetchone()[0]

    connection.close()


    # =====================================
    # CALCULATE RATES
    # =====================================

    if total_prepared > 0:

        surplus_rate = round(
            (total_surplus / total_prepared) * 100,
            1
        )

        consumption_rate = round(
            (total_consumed / total_prepared) * 100,
            1
        )

    else:

        surplus_rate = 0
        consumption_rate = 0


    # =====================================
    # IMPACT CALCULATIONS
    # =====================================

    if total_surplus > 0:

        redistribution_rate = round(
            (total_redistributed / total_surplus) * 100,
            1
        )

    else:

        redistribution_rate = 0


    meals_saved = total_redistributed

    waste_avoided = total_redistributed


    # =====================================
    # FOOD WASTE ALERT
    # =====================================

    if total_prepared == 0:

        waste_alert = "No food data available yet."
        waste_alert_class = "normal"

    elif surplus_rate > 40:

        waste_alert = (
            "🚨 High surplus detected! "
            "Consider reducing future preparation."
        )

        waste_alert_class = "danger"

    elif surplus_rate > 20:

        waste_alert = (
            "⚠️ Surplus is higher than expected. "
            "Review food demand."
        )

        waste_alert_class = "warning"

    else:

        waste_alert = (
            "✅ Surplus level is currently within "
            "the normal range."
        )

        waste_alert_class = "normal"


    # =====================================
    # SMART RECOMMENDATION
    # =====================================

    if total_prepared == 0:

        recommendation = (
            "Start adding food records to receive "
            "smart recommendations."
        )

    elif surplus_rate > 40:

        recommendation = (
            "Reduce future preparation and use "
            "recipient matching for surplus food."
        )

    elif surplus_rate > 20:

        recommendation = (
            "Review previous consumption data and "
            "adjust the quantity prepared."
        )

    else:

        recommendation = (
            "Food utilization is currently good. "
            "Continue monitoring consumption patterns."
        )


    return render_template(
        "index.html",

        entries=entries,
        redistributions=redistributions,

        total_prepared=total_prepared,
        total_consumed=total_consumed,
        total_surplus=total_surplus,
        total_redistributed=total_redistributed,

        reduction_rate=surplus_rate,
        consumption_rate=consumption_rate,

        redistribution_rate=redistribution_rate,

        meals_saved=meals_saved,
        waste_avoided=waste_avoided,

        waste_alert=waste_alert,
        waste_alert_class=waste_alert_class,

        recommendation=recommendation
    )


# =====================================
# ADD FOOD
# =====================================

@app.route("/add-food", methods=["POST"])
def add_food():

    food_name = request.form["food_name"].strip()

    prepared = int(request.form["prepared"])

    consumed = int(request.form["consumed"])


    if not food_name:

        return render_template(
            "result.html",
            food_name=food_name,
            prepared=prepared,
            consumed=consumed,
            surplus=0,
            error="Food name cannot be empty."
        )


    if prepared < 0 or consumed < 0:

        return render_template(
            "result.html",
            food_name=food_name,
            prepared=prepared,
            consumed=consumed,
            surplus=0,
            error="Quantity cannot be negative."
        )


    if consumed > prepared:

        return render_template(
            "result.html",
            food_name=food_name,
            prepared=prepared,
            consumed=consumed,
            surplus=0,
            error=(
                "Consumed quantity cannot be greater "
                "than prepared quantity."
            )
        )


    surplus = prepared - consumed


    connection = get_database()

    connection.execute(
        """
        INSERT INTO food_entries
        (food_name, prepared, consumed, surplus)
        VALUES (?, ?, ?, ?)
        """,
        (
            food_name,
            prepared,
            consumed,
            surplus
        )
    )

    connection.commit()

    connection.close()


    return render_template(
        "result.html",
        food_name=food_name,
        prepared=prepared,
        consumed=consumed,
        surplus=surplus,
        error=None
    )


# =====================================
# SMART DEMAND PREDICTION
# =====================================

@app.route("/predict", methods=["POST"])
def predict():

    food_name = request.form["food_name"].strip()


    connection = get_database()


    records = connection.execute(
        """
        SELECT consumed
        FROM food_entries
        WHERE LOWER(food_name) = LOWER(?)
        ORDER BY id ASC
        """,
        (food_name,)
    ).fetchall()


    connection.close()


    if not records:

        prediction = None

        prediction_type = "No Previous Data"

        explanation = (
            "There are no previous consumption "
            "records for this food. Add food records "
            "to generate a demand prediction."
        )


    elif len(records) == 1:

        prediction = records[0]["consumed"]

        prediction_type = "Based on Previous Record"

        explanation = (
            "The prediction is based on the "
            "previous consumption record."
        )


    else:

        values = [
            record["consumed"]
            for record in records
        ]


        weights = list(
            range(1, len(values) + 1)
        )


        weighted_total = sum(
            value * weight
            for value, weight in zip(
                values,
                weights
            )
        )


        total_weight = sum(weights)


        prediction = round(
            weighted_total / total_weight
        )


        prediction_type = "Recent Trend Prediction"

        explanation = (
            "Recent consumption records are given "
            "greater importance to estimate future "
            "food demand."
        )


    return render_template(
        "prediction.html",
        food_name=food_name,
        prediction=prediction,
        prediction_type=prediction_type,
        explanation=explanation
    )


# =====================================
# SMART RECIPIENT MATCHING
# =====================================

@app.route("/match", methods=["POST"])
def match():

    food_name = request.form["food_name"].strip()

    surplus = int(request.form["surplus"])


    if surplus <= 0:

        return render_template(
            "matching.html",
            food_name=food_name,
            surplus=0,
            recipients=[],
            message=(
                "No surplus food is available "
                "for matching."
            )
        )


    # =====================================
    # RECIPIENT DATA
    # =====================================

    all_recipients = [

        {
            "name": "Local Food Bank",
            "type": "Food Donation Center",
            "capacity": 100
        },

        {
            "name": "Community Shelter",
            "type": "Shelter",
            "capacity": 75
        },

        {
            "name": "Nearby NGO",
            "type": "NGO",
            "capacity": 50
        }

    ]


    recipients = []


    # =====================================
    # CALCULATE MATCHING
    # =====================================

    for recipient in all_recipients:

        capacity = recipient["capacity"]


        # Maximum quantity this recipient
        # can currently accept.

        accepted_quantity = min(
            surplus,
            capacity
        )


        # Calculate percentage of surplus
        # that can be handled.

        match_percentage = round(
            (accepted_quantity / surplus) * 100
        )


        if surplus <= capacity:

            status = "Highly Suitable"

            status_class = "suitable"

            recommendation = (
                "Can handle the complete surplus."
            )


        elif surplus <= capacity + 25:

            status = "Partially Suitable"

            status_class = "limited"

            recommendation = (
                "Can accept part of the surplus."
            )


        else:

            status = "Limited Capacity"

            status_class = "not-suitable"

            recommendation = (
                "Capacity is too low for this surplus."
            )


        recipients.append({

            "name": recipient["name"],

            "type": recipient["type"],

            "capacity": capacity,

            "accepted_quantity": accepted_quantity,

            "match_percentage": match_percentage,

            "status": status,

            "status_class": status_class,

            "recommendation": recommendation

        })


    message = (
        "Recipients were evaluated based on "
        "their available capacity."
    )


    return render_template(
        "matching.html",

        food_name=food_name,

        surplus=surplus,

        recipients=recipients,

        message=message
    )


# =====================================
# RECORD REDISTRIBUTION
# =====================================

@app.route("/redistribute", methods=["POST"])
def redistribute():

    food_name = request.form["food_name"].strip()

    quantity_text = request.form.get(
        "quantity",
        ""
    ).strip()

    recipient = request.form["recipient"].strip()


    try:

        quantity = int(quantity_text)

    except ValueError:

        return render_template(
            "matching.html",

            food_name=food_name,

            surplus=0,

            recipients=[],

            message=(
                "Please enter a valid "
                "redistribution quantity."
            )
        )


    if quantity <= 0:

        return render_template(
            "matching.html",

            food_name=food_name,

            surplus=quantity,

            recipients=[],

            message=(
                "Redistribution quantity must be "
                "greater than zero."
            )
        )


    # =====================================
    # FIND AVAILABLE SURPLUS
    # =====================================

    connection = get_database()


    food_result = connection.execute(
        """
        SELECT COALESCE(SUM(surplus), 0)
        FROM food_entries
        WHERE LOWER(food_name) = LOWER(?)
        """,
        (food_name,)
    ).fetchone()


    total_food_surplus = food_result[0]


    redistributed_result = connection.execute(
        """
        SELECT COALESCE(SUM(quantity), 0)
        FROM redistributions
        WHERE LOWER(food_name) = LOWER(?)
        """,
        (food_name,)
    ).fetchone()


    already_redistributed = redistributed_result[0]


    available_surplus = (
        total_food_surplus
        - already_redistributed
    )


    # =====================================
    # SAFETY CHECK
    # =====================================

    if quantity > available_surplus:

        connection.close()

        return render_template(
            "matching.html",

            food_name=food_name,

            surplus=max(
                available_surplus,
                0
            ),

            recipients=[],

            message=(
                f"Only "
                f"{max(available_surplus, 0)} "
                f"meals are currently available "
                f"for redistribution."
            )
        )


    # =====================================
    # SAVE REDISTRIBUTION
    # =====================================

    connection.execute(
        """
        INSERT INTO redistributions
        (food_name, quantity, recipient)
        VALUES (?, ?, ?)
        """,
        (
            food_name,
            quantity,
            recipient
        )
    )


    connection.commit()

    connection.close()


    return redirect(url_for("home"))


# =====================================
# START APPLICATION
# =====================================

if __name__ == "__main__":

    app.run(debug=True)