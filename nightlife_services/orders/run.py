"""
Orders Service Runner
===================
Run command: python -m nightlife_services.orders.run
"""

from . import create_app

app = create_app()

if __name__ == '__main__':
    print("🚀 Starting Nightlife Orders Service on port 5004...")
    app.run(host='0.0.0.0', port=5004, debug=True)
