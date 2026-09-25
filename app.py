from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)


def get_database():
    connection = sqlite3.connect("food_data.db")
    connection.row_factory = sqlite3.Row
    return connection


@app.route("/")
def home():

    connection = get_database()

    entries = connection.execute(
        "SELECT * FROM food_entries ORDER BY id DESC"
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

    connection.close()

    return render_template(
        "index.html",
        entries=entries,
        total_prepared=total_prepared,
        total_consumed=total_consumed,
        total_surplus=total_surplus
    )


@app.route("/add-food", methods=["POST"])
def add_food():

    food_name = request.form["food_name"]
    prepared = int(request.form["prepared"])
    consumed = int(request.form["consumed"])

    surplus = max(prepared - consumed, 0)

    connection = get_database()

    connection.execute(
        """
        INSERT INTO food_entries
        (food_name, prepared, consumed, surplus)
        VALUES (?, ?, ?, ?)
        """,
        (food_name, prepared, consumed, surplus)
    )

    connection.commit()
    connection.close()

    return render_template(
        "result.html",
        food_name=food_name,
        prepared=prepared,
        consumed=consumed,
        surplus=surplus
    )


@app.route("/predict", methods=["POST"])
def predict():

    food_name = request.form["food_name"]

    connection = get_database()

    result = connection.execute(
        """
        SELECT AVG(consumed)
        FROM food_entries
        WHERE LOWER(food_name) = LOWER(?)
        """,
        (food_name,)
    ).fetchone()

    connection.close()

    average_consumption = result[0]

    if average_consumption is None:
        prediction = None
    else:
        prediction = round(average_consumption)

    return render_template(
        "prediction.html",
        food_name=food_name,
        prediction=prediction
    )


# Smart Recipient Matching
@app.route("/match", methods=["POST"])
def match():

    food_name = request.form["food_name"]
    surplus = int(request.form["surplus"])

    if surplus <= 0:

        message = "No surplus food available for matching."
        recipients = []

    else:

        recipients = [
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

        message = "Suitable recipients found for the surplus food."

    return render_template(
        "matching.html",
        food_name=food_name,
        surplus=surplus,
        recipients=recipients,
        message=message
    )


if __name__ == "__main__":
    app.run(debug=True)