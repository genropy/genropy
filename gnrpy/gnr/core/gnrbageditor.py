"""
BagEditor class for manipulating XML files using Genropy Bag.
Provides methods to add, set, update, and delete entities in Bag structures.
"""
from pathlib import Path

from gnr.core.gnrbag import Bag

class BagEditor:
    """Editor for XML files using Genropy Bag."""

    def __init__(self, file_path=None):
        """
        Initialize BagEditor.

        Args:
            file_path: Path to XML file. If provided, loads the file.
        """
        self.file_path = file_path
        self.bag = None

        if file_path:
            self.load(file_path)

    def load(self, file_path):
        """
        Load an XML file as a Bag.

        Args:
            file_path: Path to the XML file to load.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            Exception: If the file cannot be parsed as XML/Bag.
        """
        xml_file = Path(file_path)
        if not xml_file.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            self.bag = Bag(file_path)
            self.file_path = file_path
        except Exception as e:
            raise Exception(f"Failed to load XML file as Bag: {e}")

    def save(self, file_path=None):
        """
        Save the Bag to an XML file.

        Args:
            file_path: Path to save the file. If None, uses the loaded file path.

        Raises:
            ValueError: If no file path is provided and none was loaded.
            Exception: If the file cannot be written.
        """
        if file_path is None:
            file_path = self.file_path

        if file_path is None:
            raise ValueError("No file path specified for saving")

        if self.bag is None:
            raise ValueError("No Bag loaded to save")

        try:
            self.bag.toXml(file_path, autocreate=True, encoding='UTF-8')
        except Exception as e:
            raise Exception(f"Failed to write XML file: {e}")

    def add_entity(self, entity_path, attributes=None):
        """
        Add an entity in the Bag.

        Args:
            entity_path: Dot-separated path to the entity (e.g., "projects.pippo.pluto").
            attributes: Dictionary of attributes to set on the entity.

        Raises:
            ValueError: If entity_path is empty or Bag is not loaded.
        """
        if self.bag is None:
            raise ValueError("No Bag loaded")

        if not entity_path:
            raise ValueError("Empty entity path")

        if attributes is None:
            attributes = {}

        # Add the node with attributes
        # If the path doesn't exist, Bag will create it
        self.bag.addItem(entity_path, None, attributes)
        
    def set_entity(self, entity_path, attributes=None):
        """
        Set an entity in the Bag.

        Args:
            entity_path: Dot-separated path to the entity (e.g., "projects.pippo.pluto").
            attributes: Dictionary of attributes to set on the entity.

        Raises:
            ValueError: If entity_path is empty or Bag is not loaded.
        """
        if self.bag is None:
            raise ValueError("No Bag loaded")

        if not entity_path:
            raise ValueError("Empty entity path")

        if attributes is None:
            attributes = {}

        # Set or update the node with attributes
        # If the path doesn't exist, Bag will create it
        self.bag.setItem(entity_path, None, attributes)

    def update_entity(self, entity_path, attributes=None):
        """
        Update an existing entity (error if it doesn't exist).

        Args:
            entity_path: Dot-separated path to the entity.
            attributes: Dictionary of attributes to update on the entity.

        Raises:
            ValueError: If entity_path is empty, Bag is not loaded, or entity not found.
        """
        if self.bag is None:
            raise ValueError("No Bag loaded")

        if not entity_path:
            raise ValueError("Empty entity path")

        if attributes is None:
            attributes = {}

        # Check if the node exists
        node = self.bag.getNode(entity_path)
        if node is None:
            raise ValueError(f"Element not found: {entity_path}")

        # Update attributes while preserving the node value
        self.bag.setItem(entity_path, node.value, attributes)

    def delete_entity(self, entity_path):
        """
        Delete an entity from the Bag.

        Args:
            entity_path: Dot-separated path to the entity.

        Raises:
            ValueError: If entity_path is empty, Bag is not loaded, or entity not found.
        """
        if self.bag is None:
            raise ValueError("No Bag loaded")

        if not entity_path:
            raise ValueError("Empty entity path")

        # Check if the node exists
        if self.bag.getNode(entity_path) is None:
            raise ValueError(f"Element not found: {entity_path}")

        # Delete the node
        self.bag.delItem(entity_path)

    def entity_exists(self, entity_path):
        """
        Check if an entity exists in the Bag.

        Args:
            entity_path: Dot-separated path to the entity.

        Returns:
            bool: True if the entity exists, False otherwise.
        """
        if self.bag is None:
            return False

        return self.bag.getNode(entity_path) is not None

    def get_entity_attributes(self, entity_path):
        """
        Get the attributes of an entity.

        Args:
            entity_path: Dot-separated path to the entity.

        Returns:
            dict: Dictionary of attributes, or None if entity not found.
        """
        if self.bag is None:
            return None

        node = self.bag.getNode(entity_path)
        if node is None:
            return None

        return dict(node.attr) if node.attr else {}

    def get_entity(self, entity_path):
        """
        Get the complete entity information (value and attributes).

        Args:
            entity_path: Dot-separated path to the entity.

        Returns:
            dict: Dictionary with 'value' and 'attributes' keys, or None if entity not found.
                  Example: {'value': 'some_value', 'attributes': {'name': 'test', 'path': '/foo'}}
        """
        if self.bag is None:
            return None

        node = self.bag.getNode(entity_path)
        if node is None:
            return None

        return {
            'value': node.value,
            'attributes': dict(node.attr) if node.attr else {}
        }
