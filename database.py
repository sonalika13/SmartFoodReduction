import sqlite3


def create_database():

    connection = sqlite3.connect("food_data.db")

    cursor = connection.cursor()


    # =====================================
    # FOOD ENTRIES TABLE
    # =====================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_entries (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            food_name TEXT NOT NULL,

            prepared INTEGER NOT NULL,

            consumed INTEGER NOT NULL,

            surplus INTEGER NOT NULL

        )
    """)


    # =====================================
    # REDISTRIBUTION TABLE
    # =====================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS redistributions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            food_name TEXT NOT NULL,

            quantity INTEGER NOT NULL,

            recipient TEXT NOT NULL

        )
    """)


    connection.commit()

    connection.close()


if __name__ == "__main__":

    create_database()

    print("Database created successfully!")