
import sqlite3
from types import SimpleNamespace

from database import (
    get_connection,
    update_experiment_result,
)

# Create a temporary test experiment
connection = get_connection()
cursor = connection.cursor()

cursor.execute("""
    INSERT INTO experiments (
        business_id,
        assumption_id,
        experiment,
        status
    )
    VALUES (?, ?, ?, ?)
""", (4, None, "Temporary status test", "planned"))

test_id = cursor.lastrowid
connection.commit()
connection.close()

try:
    # Simulate recording a result for testing only
    test_result = SimpleNamespace(
        result="TEST ONLY - sample result",
        observations="TEST ONLY - sample observation",
        sample_size=None,
        successes=None,
    )

    update_experiment_result(test_id, test_result)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT result, observations, status
        FROM experiments
        WHERE id = ?
    """, (test_id,))

    print("Test result:", cursor.fetchone())
    connection.close()

finally:
    # Delete only the temporary test record
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM experiments WHERE id = ?", (test_id,))
    connection.commit()
    connection.close()

    print("Temporary test record removed.")
