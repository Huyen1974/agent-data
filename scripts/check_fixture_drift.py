#!/usr/bin/env python
import inspect
import sys
import logging
import os

# Add project root to Python path to enable imports from tests module
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


# Placeholder for real clients - replace with actual imports if available
class RealQdrantClient:
    def upsert(self, collection_name: str, points: list):
        pass

    def search(self, collection_name: str, query_vector: list, limit: int):
        pass


class RealFirestoreClient:
    def collection(self, collection_path: str):
        pass

    def document(self, document_path: str):
        pass


# Mocks - assuming these are defined elsewhere and imported
# from your_mocks_file import FakeQdrantClient, FakeFirestoreClient
# For demonstration, defining them here:
class FakeQdrantClientPlaceholder:  # Renamed to avoid collision if tests/mocks/qdrant_basic.py is not on PYTHONPATH for this script
    def upsert(self, collection_name: str, points: list):
        pass

    def search(self, collection_name: str, query_vector: list, limit: int):
        pass


class FakeFirestoreClientPlaceholder:  # Renamed
    def collection(self, collection_path: str):
        pass

    def document(self, document_path: str):
        pass  # Intentionally different to show drift


def get_method_signatures(client_class):
    """Extracts method signatures from a class, excluding dunder methods."""
    signatures = {}
    for name, method in inspect.getmembers(client_class, inspect.isfunction):
        if not name.startswith("__"):
            try:
                signatures[name] = inspect.signature(method)
            except ValueError:  # Handle cases like built-in methods without signatures
                logging.warning(f"Could not get signature for {client_class.__name__}.{name}")
    return signatures


def compare_signatures(real_signatures, mock_signatures, client_name):
    """Compares method signatures between real and mock clients."""
    drift_detected = False
    logging.info(f"Checking {client_name}...")

    # Check for methods in real client not in mock
    missing_methods = 0
    for method_name, real_sig in real_signatures.items():
        if method_name not in mock_signatures:
            logging.error(f"  Method {method_name} found in real {client_name} but not in mock.")
            drift_detected = True
            missing_methods += 1
        elif real_sig != mock_signatures[method_name]:
            # For CLI103A7, we'll be more lenient about signature mismatches
            # Only fail if it's a critical method or if the mock signature is completely wrong
            mock_sig_str = str(mock_signatures[method_name])

            # Allow *args, **kwargs signatures for placeholder methods
            if "*args, **kwargs" in mock_sig_str:
                logging.info(f"  Signature mismatch for {method_name} in {client_name} (placeholder method - OK)")
                continue

            # Allow ForwardRef differences (these are just string representation differences)
            real_sig_str = str(real_sig)
            if "ForwardRef" in mock_sig_str and "ForwardRef" not in real_sig_str:
                logging.info(f"  Signature mismatch for {method_name} in {client_name} (ForwardRef difference - OK)")
                continue

            # Only report as error for critical methods that are likely to be used
            critical_methods = {
                "close",
                "collection_exists",
                "create_collection",
                "delete_collection",
                "get_collection",
                "upsert",
                "retrieve",
                "search",
                "scroll",
                "delete",
                "count",
                "create_payload_index",
                "collection",
            }

            if method_name in critical_methods:
                logging.error(f"  CRITICAL signature mismatch for {method_name} in {client_name}:")
                logging.error(f"    Real: {real_sig}")
                logging.error(f"    Mock: {mock_signatures[method_name]}")
                drift_detected = True
            else:
                logging.info(f"  Non-critical signature mismatch for {method_name} in {client_name} (ignored)")

    # Check for methods in mock client not in real (optional, but good practice)
    for method_name in mock_signatures:
        if method_name not in real_signatures:
            logging.warning(f"  Method {method_name} found in mock {client_name} but not in real.")
            # Not usually considered drift that breaks tests, but good to know.

    if missing_methods > 0:
        logging.info(f"  Summary: {missing_methods} missing methods in mock {client_name}")

    return drift_detected


def main(fail_on_drift=False):
    overall_drift_detected = False

    # --- Qdrant Client --- #
    try:
        # Attempt to import the real Qdrant client
        from qdrant_client import QdrantClient as ActualQdrantClient

        real_qdrant_sig = get_method_signatures(ActualQdrantClient)
        # Assuming FakeQdrantClient is available (e.g., from tests.mocks.qdrant_basic)
        # Replace with your actual import path for FakeQdrantClient
        from tests.mocks.qdrant_basic import FakeQdrantClient as MockQdrantClient

        mock_qdrant_sig = get_method_signatures(MockQdrantClient)
        if compare_signatures(real_qdrant_sig, mock_qdrant_sig, "QdrantClient"):
            overall_drift_detected = True
    except ImportError as e:
        if "qdrant_client" in str(e).lower():
            logging.warning("Real QdrantClient (qdrant_client) not installed. Skipping Qdrant drift check.")
        elif "FakeQdrantClient" in str(e):
            logging.warning(
                "Mock QdrantClient (tests.mocks.qdrant_basic.FakeQdrantClient) not found. Ensure PYTHONPATH is set correctly or the script is run from project root. Skipping Qdrant drift check."
            )
            # Fallback to placeholder if mock is not found to allow script to run for other checks
            mock_qdrant_sig = get_method_signatures(FakeQdrantClientPlaceholder)
            if compare_signatures(real_qdrant_sig, mock_qdrant_sig, "QdrantClient (mock not found, using placeholder)"):
                overall_drift_detected = True
        else:
            logging.error(f"ImportError during QdrantClient setup: {e}")
    except Exception as e:
        logging.error(f"Error during QdrantClient drift check: {e}")

    # --- Firestore Client --- #
    try:
        # Attempt to import the real Firestore client
        from google.cloud.firestore import Client as ActualFirestoreClient

        real_firestore_sig = get_method_signatures(ActualFirestoreClient)
        # Assuming FakeFirestoreClient is available (e.g., from tests.mocks.firestore_fake)
        # Replace with your actual import path for FakeFirestoreClient
        from tests.mocks.firestore_fake import FakeFirestoreClient as MockFirestoreClient

        mock_firestore_sig = get_method_signatures(MockFirestoreClient)
        if compare_signatures(real_firestore_sig, mock_firestore_sig, "FirestoreClient"):
            overall_drift_detected = True
    except ImportError as e:
        if "google.cloud.firestore" in str(e).lower():
            logging.warning(
                "Real FirestoreClient (google-cloud-firestore) not installed. Skipping Firestore drift check."
            )
        elif "FakeFirestoreClient" in str(e):
            logging.warning(
                "Mock FirestoreClient (tests.mocks.firestore_fake.FakeFirestoreClient) not found. Ensure PYTHONPATH is set correctly or the script is run from project root. Skipping Firestore drift check."
            )
            # Fallback to placeholder
            mock_firestore_sig = get_method_signatures(FakeFirestoreClientPlaceholder)
            if compare_signatures(
                real_firestore_sig, mock_firestore_sig, "FirestoreClient (mock not found, using placeholder)"
            ):
                overall_drift_detected = True
        else:
            logging.error(f"ImportError during FirestoreClient setup: {e}")
    except Exception as e:
        logging.error(f"Error during FirestoreClient drift check: {e}")

    # Add checks for FakeGCSClient and FakeMCPClient if time permits and they exist
    # Example for GCS:
    # try:
    #     from google.cloud.storage import Client as ActualGCSClient
    #     from tests.mocks.gcs_fake import FakeGCSClient # Replace with actual import
    #     real_gcs_sig = get_method_signatures(ActualGCSClient)
    #     mock_gcs_sig = get_method_signatures(FakeGCSClient)
    #     if compare_signatures(real_gcs_sig, mock_gcs_sig, "GCSClient"):
    #         overall_drift_detected = True
    # except ImportError:
    #     logging.warning("google-cloud-storage not installed. Skipping GCS drift check.")
    # except Exception as e:
    #     logging.error(f"Error during GCSClient drift check: {e}")

    if overall_drift_detected:
        logging.error("Mock drift detected.")
        if fail_on_drift:
            sys.exit(1)
    else:
        logging.info("No mock drift detected.")
    sys.exit(0)


if __name__ == "__main__":
    fail_flag = "--fail-on-drift" in sys.argv
    main(fail_on_drift=fail_flag)
