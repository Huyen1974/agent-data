"""
Dummy Cloud Function for CI/CD testing.
This function provides basic health check and agent data integration endpoints.
"""

import functions_framework
from google.cloud import firestore
import json
import os
from datetime import datetime


@functions_framework.http
def hello_world(request):
    """HTTP Cloud Function for basic testing.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        Response: JSON response with health status.
    """
    
    # Handle CORS
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    headers = {'Access-Control-Allow-Origin': '*'}
    
    try:
        # Get request data
        request_json = request.get_json(silent=True)
        request_args = request.args
        
        # Basic health check
        response_data = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'function': 'dummy_function',
            'version': '1.0.0',
            'environment': os.environ.get('FUNCTION_TARGET', 'development')
        }
        
        # If request has data, echo it back
        if request_json:
            response_data['echo'] = request_json
        elif request_args:
            response_data['args'] = dict(request_args)
            
        # Test Firestore connection if project ID is available
        project_id = os.environ.get('GCP_PROJECT') or os.environ.get('GOOGLE_CLOUD_PROJECT')
        if project_id:
            try:
                db = firestore.Client(project=project_id)
                # Simple read test (this will fail gracefully if no collections exist)
                collections = list(db.collections())
                response_data['firestore_status'] = 'connected'
                response_data['collections_count'] = len(collections)
            except Exception as e:
                response_data['firestore_status'] = f'error: {str(e)}'
        else:
            response_data['firestore_status'] = 'no_project_id'
            
        return (json.dumps(response_data), 200, headers)
        
    except Exception as e:
        error_response = {
            'status': 'error',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e),
            'function': 'dummy_function'
        }
        return (json.dumps(error_response), 500, headers)


@functions_framework.http  
def agent_data_test(request):
    """Agent data specific test endpoint.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        Response: JSON response with agent data simulation.
    """
    
    # Handle CORS
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    headers = {'Access-Control-Allow-Origin': '*'}
    
    try:
        # Simulate agent data processing
        response_data = {
            'agent_id': 'dummy_agent_001',
            'status': 'active',
            'capabilities': [
                'document_processing',
                'semantic_search', 
                'vector_storage',
                'knowledge_management'
            ],
            'last_activity': datetime.utcnow().isoformat(),
            'performance_metrics': {
                'queries_processed': 42,
                'avg_response_time_ms': 156,
                'success_rate': 0.98
            },
            'integrations': {
                'langroid': 'connected',
                'qdrant': 'available',
                'gcp': 'authenticated'
            }
        }
        
        return (json.dumps(response_data), 200, headers)
        
    except Exception as e:
        error_response = {
            'status': 'error',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e),
            'function': 'agent_data_test'
        }
        return (json.dumps(error_response), 500, headers) 