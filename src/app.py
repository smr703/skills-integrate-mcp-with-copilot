"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
import sqlite3
from contextlib import contextmanager

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

DB_PATH = current_dir / "activities.db"

SEED_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                name TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS registrations (
                activity_name TEXT NOT NULL,
                email TEXT NOT NULL,
                registered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (activity_name, email),
                FOREIGN KEY (activity_name) REFERENCES activities(name) ON DELETE CASCADE
            )
            """
        )

        activity_count = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
        if activity_count == 0:
            for name, data in SEED_ACTIVITIES.items():
                conn.execute(
                    """
                    INSERT INTO activities (name, description, schedule, max_participants)
                    VALUES (?, ?, ?, ?)
                    """,
                    (name, data["description"], data["schedule"], data["max_participants"]),
                )
                for email in data["participants"]:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO registrations (activity_name, email)
                        VALUES (?, ?)
                        """,
                        (name, email),
                    )
        conn.commit()


def get_activities_with_participants():
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT a.name, a.description, a.schedule, a.max_participants, r.email
            FROM activities a
            LEFT JOIN registrations r ON r.activity_name = a.name
            ORDER BY a.name, r.email
            """
        ).fetchall()

    activities = {}
    for row in rows:
        name = row["name"]
        if name not in activities:
            activities[name] = {
                "description": row["description"],
                "schedule": row["schedule"],
                "max_participants": row["max_participants"],
                "participants": [],
            }
        if row["email"]:
            activities[name]["participants"].append(row["email"])
    return activities


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return get_activities_with_participants()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    email = email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    with get_db_connection() as conn:
        activity = conn.execute(
            """
            SELECT name, max_participants FROM activities WHERE name = ?
            """,
            (activity_name,),
        ).fetchone()

        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        existing = conn.execute(
            """
            SELECT 1 FROM registrations WHERE activity_name = ? AND email = ?
            """,
            (activity_name, email),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Student is already signed up")

        registration_count = conn.execute(
            """
            SELECT COUNT(*) FROM registrations WHERE activity_name = ?
            """,
            (activity_name,),
        ).fetchone()[0]

        if registration_count >= activity["max_participants"]:
            raise HTTPException(status_code=400, detail="Activity is full")

        conn.execute(
            """
            INSERT INTO registrations (activity_name, email)
            VALUES (?, ?)
            """,
            (activity_name, email),
        )
        conn.commit()

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    email = email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    with get_db_connection() as conn:
        activity = conn.execute(
            """
            SELECT 1 FROM activities WHERE name = ?
            """,
            (activity_name,),
        ).fetchone()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        registration = conn.execute(
            """
            SELECT 1 FROM registrations WHERE activity_name = ? AND email = ?
            """,
            (activity_name, email),
        ).fetchone()
        if not registration:
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity"
            )

        conn.execute(
            """
            DELETE FROM registrations WHERE activity_name = ? AND email = ?
            """,
            (activity_name, email),
        )
        conn.commit()

    return {"message": f"Unregistered {email} from {activity_name}"}


init_db()
