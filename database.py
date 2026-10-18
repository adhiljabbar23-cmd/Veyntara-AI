import sqlite3

DB_NAME = "veyntara.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def initialize_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            idea TEXT NOT NULL,
            target_customer TEXT,
            location TEXT,
            price REAL,
            revenue_model TEXT,
            initial_budget REAL,
            variable_cost REAL
        )
    """)
    
    cursor.execute("PRAGMA table_info(businesses)")
    columns = [column[1] for column in cursor.fetchall()]

    if "variable_cost" not in columns:
        cursor.execute(
            "ALTER TABLE businesses ADD COLUMN variable_cost REAL"
        )
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assumptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        business_id INTEGER NOT NULL,
        statement TEXT NOT NULL,
        importance TEXT,
        evidence TEXT,
        risk TEXT,
        confidence TEXT,
        FOREIGN KEY (business_id) REFERENCES businesses(id)
    )
""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS experiments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        business_id INTEGER NOT NULL,
        assumption_id INTEGER,
        experiment TEXT NOT NULL,
        success_metric TEXT,
        estimated_cost REAL,
        duration TEXT,
        planned_sample_size INTEGER,
        result TEXT,
        observations TEXT,
        sample_size INTEGER,
        successes INTEGER,
        status TEXT NOT NULL DEFAULT 'planned',
        FOREIGN KEY (business_id) REFERENCES businesses(id),
        FOREIGN KEY (assumption_id) REFERENCES assumptions(id)
    )
""")
    
    cursor.execute("PRAGMA table_info(experiments)")
    columns = [column[1] for column in cursor.fetchall()]

    if "status" not in columns:
        cursor.execute("""
            ALTER TABLE experiments
            ADD COLUMN status TEXT NOT NULL DEFAULT 'planned'
        """)

    cursor.execute("""
        UPDATE experiments
        SET status = 'completed'
        WHERE result IS NOT NULL
          AND TRIM(result) != ''
        """)
    
    connection.commit()
    connection.close()



def save_business(business):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO businesses (
            name,
            idea,
            target_customer,
            location,
            price,
            variable_cost,
            revenue_model,
            initial_budget
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        business.name,
        business.idea,
        business.target_customer,
        business.location,
        business.price,
        business.variable_cost,
        business.revenue_model,
        business.initial_budget
    ))

    connection.commit()
    business_id = cursor.lastrowid
    connection.close()

    return business_id


def save_assumption(business_id, assumption):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO assumptions (
            business_id,
            statement,
            importance,
            evidence,
            risk,
            confidence
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        business_id,
        assumption.statement,
        assumption.importance,
        assumption.evidence,
        None,
        None
    ))

    connection.commit()
    assumption_id = cursor.lastrowid
    connection.close()

    return assumption_id

def get_assumptions(business_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            statement,
            importance,
            evidence,
            risk,
            confidence
        FROM assumptions
        WHERE business_id = ?
    """, (business_id,))

    assumptions = cursor.fetchall()

    connection.close()

    return assumptions


def save_experiment(business_id, assumption_id, experiment, experiment_result=None):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO experiments (
            business_id,
            assumption_id,
            experiment,
            success_metric,
            estimated_cost,
            duration,
            planned_sample_size,
            result,
            observations,
            sample_size,
            successes,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, ?)
    """, (
        business_id,
        assumption_id,
        experiment.experiment,
        experiment.success_metric,
        experiment.estimated_cost,
        experiment.duration,
        experiment.planned_sample_size,
        "planned"
    ))

    connection.commit()
    experiment_id = cursor.lastrowid
    connection.close()

    return experiment_id


def update_assumption_evaluation(
    assumption_id,
    risk,
    confidence
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE assumptions
        SET
            risk = ?,
            confidence = ?
        WHERE id = ?
    """, (
        risk,
        confidence,
        assumption_id
    ))

    connection.commit()
    connection.close()

def get_experiments(business_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            assumption_id,
            experiment,
            success_metric,
            estimated_cost,
            duration,
            planned_sample_size,
            result,
            observations,
            sample_size,
            successes,
            status
        FROM experiments
        WHERE business_id = ?
    """, (business_id,))

    experiments = cursor.fetchall()

    connection.close()

    return experiments

def get_business(business_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            idea,
            target_customer,
            location,
            price,
            variable_cost,
            revenue_model,
            initial_budget
        FROM businesses
        WHERE id = ?
    """, (business_id,))

    business = cursor.fetchone()

    connection.close()

    return business

def get_all_businesses():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            idea,
            target_customer,
            location,
            price,
            revenue_model,
            initial_budget
        FROM businesses
        ORDER BY id
    """)

    businesses = cursor.fetchall()

    connection.close()

    return businesses

def update_experiment_result(experiment_id, experiment_result):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE experiments
        SET
            result = ?,
            observations = ?,
            sample_size = ?,
            successes = ?,
            status = 'completed'
        WHERE id = ?
    """, (
        experiment_result.result,
        experiment_result.observations,
        experiment_result.sample_size,
        experiment_result.successes,
        experiment_id
    ))

    connection.commit()
    connection.close()
    
    
