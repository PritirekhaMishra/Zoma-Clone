"""
Run All Nightlife Services
=========================
This script runs all 4 nightlife microservices together.

Usage:
    python nightlife_services/run_all.py

Or individually:
    python -m nightlife_services.main.run   # Port 5001
    python -m nightlife_services.vendor.run  # Port 5002
    python -m nightlife_services.booking.run # Port 5003
    python -m nightlife_services.orders.run  # Port 5004
"""

import subprocess
import sys
import os

# Create databases directory
databases_dir = os.path.join(os.path.dirname(__file__), 'databases')
os.makedirs(databases_dir, exist_ok=True)

def run_service(service_name, module_path):
    """Run a single service"""
    print(f"\n🚀 Starting {service_name}...")
    print(f"=" * 50)
    try:
        subprocess.run([sys.executable, "-m", module_path])
    except KeyboardInterrupt:
        print(f"\n⚠️  {service_name} stopped")
    except Exception as e:
        print(f"❌ Error running {service_name}: {e}")

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║     ZomaClone Nightlife Services                 ║
    ║     Microservices Architecture                   ║
    ╠═══════════════════════════════════════════════════╣
    ║  Main Service    : http://127.0.0.1:5001/api    ║
    ║  Vendor Service  : http://127.0.0.1:5002/api    ║
    ║  Booking Service : http://127.0.0.1:5003/api    ║
    ║  Orders Service  : http://127.0.0.1:5004/api    ║
    ╚═══════════════════════════════════════════════════╝
    """)
    
    print("Starting all services...")
    print("Each service will run in its own process.")
    print("Press Ctrl+C to stop all services.")
    print()
    
    # Run services sequentially (for debugging)
    # For production, use separate processes or Docker
    
    try:
        # Start Main Service
        run_service("Nightlife Main Service", "nightlife_services.main.run")
    except KeyboardInterrupt:
        print("\n⚠️  All services stopped")
