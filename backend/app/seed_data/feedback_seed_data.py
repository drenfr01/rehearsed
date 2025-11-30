"""This file contains the feedback seed data for the application."""

import os
from yaml import safe_load
from sqlmodel import Session, select
from app.services.database import database_service
from app.models.feedback import Feedback, FeedbackType
from app.models.scenario import Scenario


def load_feedback_data(session: Session) -> list[Feedback]:
    """Load the feedback data from the file.
    
    Args:
        session: Database session to look up scenario IDs by name
    """
    with open(os.path.join(os.path.dirname(__file__), "feedback_data.yaml"), "r") as f:
        feedback_data_yaml = safe_load(f)
    
    # Build cache of scenario names to IDs
    scenarios = session.exec(select(Scenario)).all()
    scenario_name_to_id = {s.name: s.id for s in scenarios}
    
    feedbacks = []
    for feedback_data in feedback_data_yaml:
        scenario_name = feedback_data["scenario_name"]
        scenario_id = scenario_name_to_id.get(scenario_name)
        if scenario_id is None:
            raise ValueError(f"Scenario '{scenario_name}' not found. Make sure scenarios are seeded first.")
        
        feedback = Feedback(
            feedback_type=FeedbackType(feedback_data["feedback_type"]),
            scenario_id=scenario_id,
            objective=feedback_data["objective"],
            instructions=feedback_data["instructions"],
            constraints=feedback_data["constraints"],
            context=feedback_data["context"],
            output_format=feedback_data.get("output_format", ""),
            owner_id=feedback_data.get("owner_id"),  # None for global feedback
        )
        feedbacks.append(feedback)
    
    return feedbacks


def seed_feedback_data():
    """Seed the feedback data into the database."""
    with Session(database_service.engine) as session:
        # Only check for global feedback (owner_id is None)
        # User-created feedback should not prevent seeding global ones
        global_feedback_exists = session.exec(
            select(Feedback).where(Feedback.owner_id == None)
        ).first()
        if global_feedback_exists:
            return
        for feedback in load_feedback_data(session):
            session.add(feedback)
        session.commit()


def reseed_feedback_data():
    """Delete existing feedback data and re-seed from YAML.
    
    Use this to refresh feedback data after fixing sanitization issues
    or updating the YAML file.
    """
    with Session(database_service.engine) as session:
        # Delete all existing feedback
        existing = session.exec(select(Feedback)).all()
        for feedback in existing:
            session.delete(feedback)
        session.commit()
        
        # Re-insert from YAML
        feedbacks = load_feedback_data(session)
        for feedback in feedbacks:
            session.add(feedback)
        session.commit()
        print(f"Re-seeded {len(feedbacks)} feedback records")

