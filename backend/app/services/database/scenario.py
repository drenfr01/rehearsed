"""Scenario database repository."""

from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.logging import logger
from app.models.scenario import Scenario


class ScenarioRepository:
    """Repository for Scenario model database operations."""
    
    def __init__(self, engine: Engine):
        """Initialize scenario repository with database engine.
        
        Args:
            engine: The SQLModel Engine instance
        """
        self._engine = engine
        # TODO: potentially move this to a separate service
        self.current_scenario: Scenario | None = None
    
    @property
    def engine(self) -> Engine:
        """Get the database engine."""
        return self._engine
    
    def get_current_scenario(self) -> Scenario:
        """Return the scenario data for the currently set scenario.

        Returns:
            The scenario data for the current scenario.
        """
        return self.current_scenario

    def set_scenario(self, scenario_id: int) -> None:
        """Set the scenario data for the currently set scenario.

        Args:
            scenario_id: The ID of the scenario to set.
        """
        with Session(self.engine) as session:
            statement = select(Scenario).where(Scenario.id == scenario_id)
            scenario = session.exec(statement).one()
            self.current_scenario = scenario
            return scenario

    async def get_all_scenarios(self) -> list[Scenario]:
        """Get all scenarios in the system.

        Returns:
            List[Scenario]: List of all scenarios
        """
        with Session(self.engine) as session:
            statement = select(Scenario)
            scenarios = session.exec(statement).all()
            return scenarios

    async def create_scenario(
        self,
        name: str,
        description: str,
        overview: str,
        system_instructions: str,
        initial_prompt: str,
        teaching_objectives: str,
    ) -> Scenario:
        """Create a new scenario.

        Args:
            name: Name of the scenario
            description: Description of the scenario
            overview: Overview of the scenario
            system_instructions: System instructions for the scenario
            initial_prompt: Initial prompt for the scenario
            teaching_objectives: Teaching objectives for the scenario

        Returns:
            Scenario: The created scenario
        """
        with Session(self.engine) as session:
            scenario = Scenario(
                name=name,
                description=description,
                overview=overview,
                system_instructions=system_instructions,
                initial_prompt=initial_prompt,
                teaching_objectives=teaching_objectives,
            )
            session.add(scenario)
            session.commit()
            session.refresh(scenario)
            logger.info("scenario_created", scenario_id=scenario.id, name=name)
            return scenario

    async def get_scenario(self, scenario_id: int) -> Optional[Scenario]:
        """Get a scenario by ID.

        Args:
            scenario_id: The ID of the scenario to retrieve

        Returns:
            Optional[Scenario]: The scenario if found, None otherwise
        """
        with Session(self.engine) as session:
            scenario = session.get(Scenario, scenario_id)
            return scenario

    async def update_scenario(
        self,
        scenario_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        overview: Optional[str] = None,
        system_instructions: Optional[str] = None,
        initial_prompt: Optional[str] = None,
        teaching_objectives: Optional[str] = None,
    ) -> Scenario:
        """Update a scenario's attributes.

        Args:
            scenario_id: The ID of the scenario to update
            name: Optional new name
            description: Optional new description
            overview: Optional new overview
            system_instructions: Optional new system instructions
            initial_prompt: Optional new initial prompt
            teaching_objectives: Optional new teaching objectives

        Returns:
            Scenario: The updated scenario

        Raises:
            HTTPException: If scenario is not found
        """
        with Session(self.engine) as session:
            scenario = session.get(Scenario, scenario_id)
            if not scenario:
                raise HTTPException(status_code=404, detail="Scenario not found")

            if name is not None:
                scenario.name = name
            if description is not None:
                scenario.description = description
            if overview is not None:
                scenario.overview = overview
            if system_instructions is not None:
                scenario.system_instructions = system_instructions
            if initial_prompt is not None:
                scenario.initial_prompt = initial_prompt
            if teaching_objectives is not None:
                scenario.teaching_objectives = teaching_objectives

            session.add(scenario)
            session.commit()
            session.refresh(scenario)
            logger.info("scenario_updated", scenario_id=scenario_id)
            return scenario

    async def delete_scenario(self, scenario_id: int) -> bool:
        """Delete a scenario by ID.

        Args:
            scenario_id: The ID of the scenario to delete

        Returns:
            bool: True if deletion was successful, False if scenario not found
        """
        with Session(self.engine) as session:
            scenario = session.get(Scenario, scenario_id)
            if not scenario:
                return False

            session.delete(scenario)
            session.commit()
            logger.info("scenario_deleted", scenario_id=scenario_id)
            return True

    async def get_scenarios_for_user(self, user_id: int) -> List[Scenario]:
        """Get all scenarios available to a user (global + user's local).

        Args:
            user_id: The ID of the user

        Returns:
            List[Scenario]: List of global scenarios and user's local scenarios
        """
        with Session(self.engine) as session:
            statement = select(Scenario).where(
                or_(Scenario.owner_id.is_(None), Scenario.owner_id == user_id)
            ).order_by(Scenario.created_at)
            scenarios = session.exec(statement).all()
            return list(scenarios)

    async def get_user_local_scenarios(self, user_id: int) -> List[Scenario]:
        """Get only user's local scenarios (not global).

        Args:
            user_id: The ID of the user

        Returns:
            List[Scenario]: List of user's local scenarios only
        """
        with Session(self.engine) as session:
            statement = select(Scenario).where(
                Scenario.owner_id == user_id
            ).order_by(Scenario.created_at)
            scenarios = session.exec(statement).all()
            return list(scenarios)

    async def copy_scenario_to_user(self, scenario_id: int, user_id: int, copy_agents: bool = True, copy_feedback: bool = True) -> Scenario:
        """Copy a global scenario to a user's local scenarios.

        Args:
            scenario_id: The ID of the scenario to copy
            user_id: The ID of the user to copy to
            copy_agents: Whether to also copy agents belonging to this scenario
            copy_feedback: Whether to also copy feedback belonging to this scenario

        Returns:
            Scenario: The new local copy of the scenario

        Raises:
            HTTPException: If scenario is not found
        """
        with Session(self.engine) as session:
            original = session.get(Scenario, scenario_id)
            if not original:
                raise HTTPException(status_code=404, detail="Scenario not found")

            # Create the copy with user's owner_id
            new_scenario = Scenario(
                name=f"{original.name} (Copy)",
                description=original.description,
                overview=original.overview,
                system_instructions=original.system_instructions,
                initial_prompt=original.initial_prompt,
                owner_id=user_id,
            )
            session.add(new_scenario)
            session.commit()
            session.refresh(new_scenario)

            logger.info("scenario_copied_to_user", 
                       original_id=scenario_id, 
                       new_id=new_scenario.id, 
                       user_id=user_id)

            # Optionally copy agents as well
            if copy_agents:
                from app.models.agent import Agent
                agents_statement = select(Agent).where(Agent.scenario_id == scenario_id)
                original_agents = session.exec(agents_statement).all()
                
                for agent in original_agents:
                    import uuid
                    new_agent = Agent(
                        id=str(uuid.uuid4()),
                        name=agent.name,
                        scenario_id=new_scenario.id,
                        agent_personality_id=agent.agent_personality_id,
                        voice_id=agent.voice_id,
                        display_text_color=agent.display_text_color,
                        objective=agent.objective,
                        instructions=agent.instructions,
                        constraints=agent.constraints,
                        context=agent.context,
                        owner_id=user_id,
                    )
                    session.add(new_agent)
                
                session.commit()
                logger.info("agents_copied_with_scenario", 
                           scenario_id=new_scenario.id, 
                           agent_count=len(original_agents))

            # Optionally copy feedback as well
            if copy_feedback:
                from app.models.feedback import Feedback
                feedback_statement = select(Feedback).where(Feedback.scenario_id == scenario_id)
                original_feedbacks = session.exec(feedback_statement).all()
                
                for feedback in original_feedbacks:
                    new_feedback = Feedback(
                        feedback_type=feedback.feedback_type,
                        scenario_id=new_scenario.id,
                        objective=feedback.objective,
                        instructions=feedback.instructions,
                        constraints=feedback.constraints,
                        context=feedback.context,
                        output_format=feedback.output_format,
                        owner_id=user_id,
                    )
                    session.add(new_feedback)
                
                session.commit()
                logger.info("feedback_copied_with_scenario", 
                           scenario_id=new_scenario.id, 
                           feedback_count=len(original_feedbacks))

            return new_scenario

    async def create_user_scenario(
        self,
        user_id: int,
        name: str,
        description: str,
        overview: str,
        system_instructions: str,
        initial_prompt: str,
        teaching_objectives: str,
    ) -> Scenario:
        """Create a new user-local scenario.

        Args:
            user_id: The owner user's ID
            name: Name of the scenario
            description: Description of the scenario
            overview: Overview of the scenario
            system_instructions: System instructions for the scenario
            initial_prompt: Initial prompt for the scenario
            teaching_objectives: Teaching objectives for the scenario

        Returns:
            Scenario: The created scenario
        """
        with Session(self.engine) as session:
            scenario = Scenario(
                name=name,
                description=description,
                overview=overview,
                system_instructions=system_instructions,
                initial_prompt=initial_prompt,
                teaching_objectives=teaching_objectives,
                owner_id=user_id,
            )
            session.add(scenario)
            session.commit()
            session.refresh(scenario)
            logger.info("user_scenario_created", scenario_id=scenario.id, name=name, user_id=user_id)
            return scenario

    async def update_user_scenario(
        self,
        scenario_id: int,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        overview: Optional[str] = None,
        system_instructions: Optional[str] = None,
        initial_prompt: Optional[str] = None,
        teaching_objectives: Optional[str] = None,
    ) -> Scenario:
        """Update a user's local scenario (with ownership check).

        Args:
            scenario_id: The ID of the scenario to update
            user_id: The ID of the user (for ownership verification)
            name: Optional new name
            description: Optional new description
            overview: Optional new overview
            system_instructions: Optional new system instructions
            initial_prompt: Optional new initial prompt
            teaching_objectives: Optional new teaching objectives

        Returns:
            Scenario: The updated scenario

        Raises:
            HTTPException: If scenario is not found or user doesn't own it
        """
        with Session(self.engine) as session:
            scenario = session.get(Scenario, scenario_id)
            if not scenario:
                raise HTTPException(status_code=404, detail="Scenario not found")
            if scenario.owner_id != user_id:
                raise HTTPException(status_code=403, detail="You don't have permission to edit this scenario")

            if name is not None:
                scenario.name = name
            if description is not None:
                scenario.description = description
            if overview is not None:
                scenario.overview = overview
            if system_instructions is not None:
                scenario.system_instructions = system_instructions
            if initial_prompt is not None:
                scenario.initial_prompt = initial_prompt
            if teaching_objectives is not None:
                scenario.teaching_objectives = teaching_objectives

            session.add(scenario)
            session.commit()
            session.refresh(scenario)
            logger.info("user_scenario_updated", scenario_id=scenario_id, user_id=user_id)
            return scenario

    async def delete_user_scenario(self, scenario_id: int, user_id: int) -> bool:
        """Delete a user's local scenario (with ownership check).

        Args:
            scenario_id: The ID of the scenario to delete
            user_id: The ID of the user (for ownership verification)

        Returns:
            bool: True if deletion was successful

        Raises:
            HTTPException: If scenario is not found or user doesn't own it
        """
        with Session(self.engine) as session:
            scenario = session.get(Scenario, scenario_id)
            if not scenario:
                raise HTTPException(status_code=404, detail="Scenario not found")
            if scenario.owner_id != user_id:
                raise HTTPException(status_code=403, detail="You don't have permission to delete this scenario")

            session.delete(scenario)
            session.commit()
            logger.info("user_scenario_deleted", scenario_id=scenario_id, user_id=user_id)
            return True
