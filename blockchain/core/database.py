"""
Database module for the BT2C blockchain.
Provides a unified interface for database operations regardless of the backend.
"""
import os
from typing import Optional, Dict, List, Any, Type, TypeVar
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import DeclarativeMeta
import structlog
from ..models import Base, Block, Transaction, Validator
from .types import NetworkType

logger = structlog.get_logger()

T = TypeVar('T')

class DatabaseManager:
    """Manages database connections and operations for the blockchain."""
    
    def __init__(self, db_url: Optional[str] = None, network_type: NetworkType = NetworkType.MAINNET):
        """Initialize the database manager.
        
        Args:
            db_url: SQLAlchemy database URL. If None, uses the default SQLite database.
            network_type: Network type for the blockchain.
        """
        self.network_type = network_type
        
        if db_url is None:
            # Default to SQLite database in user's home directory
            home_dir = os.path.expanduser("~")
            data_dir = os.path.join(home_dir, ".bt2c", "data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "blockchain.db")
            db_url = f"sqlite:///{db_path}"
            
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        self.metadata = MetaData()
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        logger.info("database_initialized", db_url=db_url, network_type=network_type)
        
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.Session()
        
    def add(self, obj: Any) -> None:
        """Add an object to the database."""
        with self.Session() as session:
            session.add(obj)
            session.commit()
            
    def add_all(self, objects: List[Any]) -> None:
        """Add multiple objects to the database."""
        with self.Session() as session:
            session.add_all(objects)
            session.commit()
            
    def get(self, model: Type[T], **kwargs) -> Optional[T]:
        """Get a single object from the database.
        
        Args:
            model: Model class to query.
            **kwargs: Query filters.
            
        Returns:
            The object if found, None otherwise.
        """
        with self.Session() as session:
            return session.query(model).filter_by(**kwargs).first()
            
    def get_all(self, model: Type[T], **kwargs) -> List[T]:
        """Get all objects matching the filters.
        
        Args:
            model: Model class to query.
            **kwargs: Query filters.
            
        Returns:
            List of matching objects.
        """
        with self.Session() as session:
            return session.query(model).filter_by(**kwargs).all()
            
    def update(self, model: Type[T], filters: Dict[str, Any], values: Dict[str, Any]) -> int:
        """Update objects in the database.
        
        Args:
            model: Model class to update.
            filters: Query filters to select objects.
            values: Values to update.
            
        Returns:
            Number of rows updated.
        """
        with self.Session() as session:
            result = session.query(model).filter_by(**filters).update(values)
            session.commit()
            return result
            
    def delete(self, model: Type[T], **kwargs) -> int:
        """Delete objects from the database.
        
        Args:
            model: Model class to delete from.
            **kwargs: Query filters.
            
        Returns:
            Number of rows deleted.
        """
        with self.Session() as session:
            result = session.query(model).filter_by(**kwargs).delete()
            session.commit()
            return result
            
    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a raw SQL query.
        
        Args:
            query: SQL query string.
            params: Query parameters.
            
        Returns:
            Query result.
        """
        with self.engine.connect() as connection:
            if params:
                return connection.execute(query, params)
            else:
                return connection.execute(query)
                
    # Validator-specific methods
    def register_validator(self, address: str, stake: float) -> bool:
        """Register a new validator or update an existing one.
        
        Args:
            address: Validator address.
            stake: Stake amount.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            with self.Session() as session:
                validator = session.query(Validator).filter_by(
                    address=address,
                    network_type=self.network_type.value
                ).first()
                
                if validator:
                    # Update existing validator
                    validator.stake = stake
                    logger.info("validator_updated", 
                               address=address, 
                               stake=stake,
                               network_type=self.network_type)
                else:
                    # Create new validator
                    validator = Validator(
                        address=address,
                        stake=stake,
                        network_type=self.network_type.value,
                        joined_at=os.environ.get('OVERRIDE_TIME', None) or datetime.utcnow()
                    )
                    session.add(validator)
                    logger.info("validator_registered", 
                               address=address, 
                               stake=stake,
                               network_type=self.network_type)
                
                session.commit()
                return True
        except Exception as e:
            logger.error("validator_registration_error", 
                        address=address, 
                        error=str(e))
            return False
            
    def get_validators(self) -> List[Dict[str, Any]]:
        """Get all validators for the current network.
        
        Returns:
            List of validator dictionaries.
        """
        with self.Session() as session:
            validators = session.query(Validator).filter_by(
                network_type=self.network_type.value
            ).all()
            
            return [
                {
                    "address": v.address,
                    "stake": v.stake,
                    "joined_at": v.joined_at,
                    "last_block": v.last_block,
                    "total_blocks": v.total_blocks or 0,
                    "commission_rate": v.commission_rate or 0.0
                }
                for v in validators
            ]
            
    def get_validator(self, address: str) -> Optional[Dict[str, Any]]:
        """Get a specific validator.
        
        Args:
            address: Validator address.
            
        Returns:
            Validator dictionary if found, None otherwise.
        """
        with self.Session() as session:
            validator = session.query(Validator).filter_by(
                address=address,
                network_type=self.network_type.value
            ).first()
            
            if not validator:
                return None
                
            return {
                "address": validator.address,
                "stake": validator.stake,
                "joined_at": validator.joined_at,
                "last_block": validator.last_block,
                "total_blocks": validator.total_blocks or 0,
                "commission_rate": validator.commission_rate or 0.0
            }
