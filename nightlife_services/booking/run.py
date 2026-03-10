"""
Booking Service Runner
===================
Run command: python -m nightlife_services.booking.run
"""

from . import create_app

app = create_app()

if __name__ == '__main__':
    print("🚀 Starting Nightlife Booking Service on port 5003...")
    app.run(host='0.0.0.0', port=5003, debug=True)
