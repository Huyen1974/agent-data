# Usage Documentation

## FAISS to Qdrant Migration CLI

### Purpose
Migrate vectors from FAISS index to Qdrant collection.

### Usage

```bash
python migration_cli.py --faiss-index path/to/index.faiss --collection-name my_collection --batch-size 100
```

### Options

- `--faiss-index`: Path to FAISS index file (required)
- `--collection-name`: Target Qdrant collection name (required)
- `--batch-size`: Number of vectors to process per batch (default: 100)

### Examples

#### Basic Migration
```bash
python migration_cli.py --faiss-index ./data/vectors.faiss --collection-name documents
```

#### Migration with Custom Batch Size
```bash
python migration_cli.py --faiss-index ./data/vectors.faiss --collection-name documents --batch-size 50
```

### Prerequisites

1. Ensure QDRANT_URL and QDRANT_API_KEY environment variables are set
2. Target Qdrant collection will be created automatically if it doesn't exist
3. FAISS index file must be readable and valid

### Output

The CLI returns a JSON result with migration status:

```json
{
  "status": "success",
  "migrated_count": 1000
}
```

Or in case of failure:

```json
{
  "status": "failed",
  "error": "Error message",
  "migrated_count": 0
}
```

### Notes

- Each migrated vector gets a payload with:
  - `source`: "FAISS_migration"
  - `original_index`: Original index position in FAISS
  - `tag`: "migrated"
- Vector IDs start from 1 and increment sequentially
- The migration handles both regular FAISS indices and IndexIDMap types
- Progress is logged during migration process
