"""
Main Service Runner
==================
Run command: python -m nightlife_services.main.run
"""

from . import create_app

app = create_app()


if __name__ == '__main__':
    print("🚀 Starting Nightlife Main Service on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=True)
