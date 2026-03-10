"""
Vendor Service Runner
===================
Run command: python -m nightlife_services.vendor.run
"""

from . import create_app

app = create_app()

if __name__ == '__main__':
    print("🚀 Starting Nightlife Vendor Service on port 5002...")
    app.run(host='0.0.0.0', port=5002, debug=True)
