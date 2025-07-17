"""
from chromadb import PersistentClient
from chromadb.config import Settings

def list_chroma_collections(chromaDB_path):
    # Connect to the ChromaDB instance
    client = PersistentClient(
        path=chromaDB_path,
        settings=Settings()
    )
    
    # List all collections
    collections = client.list_collections()
    if not collections:
        print("No collections found in ChromaDB.")
    else:
        print("Collections in ChromaDB:")
        for collection in collections:
            print(f"- {collection.name}")

if __name__ == "__main__":
    chromaDB_path = "./ChromaDbPersistent"  # Path to your ChromaDB storage
    list_chroma_collections(chromaDB_path)
"""
from chromadb import PersistentClient
from chromadb.config import Settings

def list_collection_items(chromaDB_path, collection_name):
    # Connect to the ChromaDB instance
    client = PersistentClient(
        path=chromaDB_path,
        settings=Settings()
    )
    
    # Access the specified collection
    try:
        collection = client.get_collection(collection_name)
    except Exception as e:
        print(f"Error accessing collection '{collection_name}': {e}")
        return
    
    # Retrieve all items in the collection
    try:
        items = collection.get()
        print(f"Raw items in the collection '{collection_name}': {items}")
        
        if not items:
            print(f"No items found in the collection '{collection_name}'.")
            return
        
        # Check the structure of items and print details
        print(f"Items in the collection '{collection_name}':")
        if isinstance(items, list):
            for item in items:
                print(f"- ID: {item.get('id', 'No ID')}, Metadata: {item.get('metadata', 'No metadata')}, Document: {item.get('document', 'No document')}")
        elif isinstance(items, dict):
            for key, value in items.items():
                print(f"- Key: {key}, Value: {value}")
        else:
            print(f"Unexpected structure: {type(items)}")
    except Exception as e:
        print(f"Error retrieving items from collection '{collection_name}': {e}")

if __name__ == "__main__":
    chromaDB_path = "./ChromaDbPersistent"  # Path to your ChromaDB storage
    collection_name = "rag5"  # The name of the collection you want to inspect
    list_collection_items(chromaDB_path, collection_name)
