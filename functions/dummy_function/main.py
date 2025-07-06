def dummy_function(request):
    """Simple dummy function for CI testing"""
    return {"status": "ok", "message": "Dummy function executed successfully"}

if __name__ == "__main__":
    from functions_framework import create_app
    app = create_app(dummy_function)
    app.run(debug=True, host="0.0.0.0", port=8080) # Updated Sun Jul  6 14:14:07 +07 2025
