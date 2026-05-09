"""
Automotive Copilot - Test Data Generator
==========================================
Generates:
  1. Realistic JSON telemetry files (AWS + Azure sources, 200+ records)
  2. Vehicle manual PDFs (5 manuals for Ford, Toyota, BMW, Tesla, GM)

Run:  python data/generate_test_data.py
Deps: pip install fpdf2
"""

import json
import random
import os
from datetime import datetime, timedelta, UTC

# ── Config ─────────────────────────────────────────────────────────────────────
RAW_EVENTS_DIR = os.path.join(os.path.dirname(__file__), "raw_cloud_events")
RAW_MANUALS_DIR = os.path.join(os.path.dirname(__file__), "raw_manuals")
os.makedirs(RAW_EVENTS_DIR, exist_ok=True)
os.makedirs(RAW_MANUALS_DIR, exist_ok=True)

random.seed(42)

# ── Reference Data ─────────────────────────────────────────────────────────────
OBD_CODES = {
    "P0300": "Random/Multiple Cylinder Misfire Detected",
    "P0420": "Catalyst System Efficiency Below Threshold",
    "P0171": "System Too Lean (Bank 1)",
    "P0172": "System Too Rich (Bank 1)",
    "P0455": "Evaporative Emission System Leak Detected (Large)",
    "P0128": "Coolant Thermostat Below Regulating Temperature",
    "P0401": "Exhaust Gas Recirculation Flow Insufficient",
    "P0507": "Idle Control System RPM High",
    "P0340": "Camshaft Position Sensor Circuit Malfunction",
    "P0011": "Camshaft Position Timing Over-Advanced (Bank 1)",
    "P0562": "System Voltage Low",
    "P0700": "Transmission Control System Malfunction",
    "B1234": "ADAS Lane Departure System Fault",
    "U0100": "Lost Communication with ECM/PCM",
    "NONE":  "No fault detected",
}

FAULT_CATEGORIES = ["ENGINE", "ELECTRICAL", "BRAKES", "TRANSMISSION", "ADAS", "EMISSIONS"]

MECHANIC_NOTES = [
    "Customer reports rough idle and hesitation during acceleration. P0300 confirmed on scanner.",
    "Check engine light on. Vehicle running lean. Suspect vacuum leak near intake manifold.",
    "Transmission slipping between 2nd and 3rd gear at highway speeds. Fluid level normal.",
    "ABS warning light active. Left front wheel speed sensor reading intermittently.",
    "Battery draining overnight. Parasitic draw test shows 350mA with all accessories off.",
    "Coolant temperature sensor replaced. Thermostat verified functional at 88 degrees.",
    "Catalytic converter efficiency below threshold. O2 sensor readings within spec.",
    "Customer complains of vibration at 65+ mph. Wheel balance and alignment checked.",
    "Oil pressure warning at idle. Oil level full. Suspect oil pump or pressure switch.",
    "Fuel injector cleaning performed. Fuel trim improved from +18% to +4%.",
    "Lane keep assist disabling randomly. Camera calibration required after windshield replacement.",
    "EGR valve stuck open causing rough idle. Cleaned and tested, flow rate restored.",
    "Brake pads worn to 2mm on front axle. Rotors show heat scoring, replacement recommended.",
    "TPMS sensor failure on right rear. Sensor replaced and system re-initialized.",
    "Intermittent stall at stop lights. Idle air control valve cleaned, carbon buildup removed.",
    "Check engine and traction control lights on simultaneously. Wheel speed sensor faulty.",
    "AC compressor not engaging. Refrigerant pressure low, leak found at condenser fitting.",
    "Power steering assist reduced warning. Electric power steering module requires update.",
    "Spark plugs at 98k miles, worn beyond spec. Full tune-up completed with NGK plugs.",
    "Transmission fluid dark and smells burnt. Service due, filter replaced, fluid flushed.",
]

VEHICLE_MAKES = [
    ("Ford", "F-150", ["VIN_AWS_F150_"]),
    ("Toyota", "Camry", ["VIN_AWS_CAM_"]),
    ("BMW", "X5", ["VIN_AZURE_BMW_"]),
    ("Tesla", "Model 3", ["VIN_AZURE_TES_"]),
    ("GM", "Silverado", ["VIN_AWS_SIL_"]),
    ("Honda", "Accord", ["VIN_AZURE_HON_"]),
    ("Ford", "Explorer", ["VIN_AWS_EXP_"]),
    ("Toyota", "Tacoma", ["VIN_AZURE_TAC_"]),
]


def random_timestamp(days_back: int = 90) -> str:
    base = datetime.now(UTC)
    delta = timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59)
    )
    return (base - delta).isoformat()


def make_vin(prefix: str, idx: int) -> str:
    return f"{prefix}{idx:03d}"


def make_gen1_record(vin: str, source: str) -> dict:
    """Original 3-field sensor payload."""
    code = random.choice(list(OBD_CODES.keys()))
    temp = round(random.uniform(72, 135), 1)
    if random.random() < 0.05:
        temp = "ERROR"
    return {
        "vin": vin,
        "engine_temp_c": temp,
        "error_code": code,
        "log_text": random.choice(MECHANIC_NOTES),
        "recorded_at": random_timestamp(),
        "cloud_source": source,
    }


def make_gen2_record(vin: str, source: str) -> dict:
    """Gen-2: adds tire pressure and battery voltage."""
    base = make_gen1_record(vin, source)
    base.update({
        "tire_pressure_psi": {
            "FL": round(random.uniform(29, 36), 1),
            "FR": round(random.uniform(29, 36), 1),
            "RL": round(random.uniform(29, 36), 1),
            "RR": round(random.uniform(29, 36), 1),
        },
        "battery_voltage_v": round(random.uniform(11.8, 14.6), 2),
        "fuel_level_pct": random.randint(5, 100),
    })
    return base


def make_gen3_record(vin: str, source: str) -> dict:
    """Gen-3: adds ADAS events and GPS."""
    base = make_gen2_record(vin, source)
    if random.random() < 0.4:
        base["adas_event"] = {
            "type": random.choice(["LANE_DEPARTURE", "FORWARD_COLLISION_WARNING", "BLIND_SPOT_ALERT", "AUTO_BRAKE"]),
            "severity": random.choice(["LOW", "MEDIUM", "HIGH"]),
            "timestamp_ms": int(datetime.now(UTC).timestamp() * 1000),
            "speed_kmh": random.randint(0, 130),
        }
    base["odometer_km"] = random.randint(5000, 200000)
    base["gps"] = {
        "lat": round(random.uniform(25.0, 49.0), 6),
        "lon": round(random.uniform(-125.0, -65.0), 6),
    }
    return base


# ── Generate JSON Telemetry Files ──────────────────────────────────────────────

def generate_aws_files():
    print("Generating AWS telemetry files...")

    # AWS Batch 1: Gen-1 Ford F-150 + Toyota Camry (50 records)
    records = []
    for i in range(1, 26):
        records.append(make_gen1_record(make_vin("VIN_AWS_F150_", i), "AWS_S3"))
    for i in range(1, 26):
        records.append(make_gen1_record(make_vin("VIN_AWS_CAM_", i), "AWS_S3"))
    random.shuffle(records)
    with open(os.path.join(RAW_EVENTS_DIR, "aws_gen1_ford_toyota.json"), "w") as f:
        json.dump(records, f, indent=2)
    print(f"  ✅ aws_gen1_ford_toyota.json - {len(records)} records")

    # AWS Batch 2: Gen-2 GM Silverado + Ford Explorer (60 records)
    records = []
    for i in range(1, 31):
        records.append(make_gen2_record(make_vin("VIN_AWS_SIL_", i), "AWS_S3"))
    for i in range(1, 31):
        records.append(make_gen2_record(make_vin("VIN_AWS_EXP_", i), "AWS_S3"))
    with open(os.path.join(RAW_EVENTS_DIR, "aws_gen2_gm_ford.json"), "w") as f:
        json.dump(records, f, indent=2)
    print(f"  ✅ aws_gen2_gm_ford.json - {len(records)} records")

    # AWS Batch 3: High-criticality vehicles (deliberately bad data for alert testing)
    critical = []
    for i in range(1, 11):
        r = make_gen2_record(make_vin("VIN_AWS_CRIT_", i), "AWS_S3")
        r["engine_temp_c"] = round(random.uniform(128, 145), 1)   # dangerously hot
        r["error_code"] = random.choice(["P0300", "P0700", "U0100"])
        r["battery_voltage_v"] = round(random.uniform(9.5, 11.2), 2)  # low voltage
        critical.append(r)
    with open(os.path.join(RAW_EVENTS_DIR, "aws_critical_alerts.json"), "w") as f:
        json.dump(critical, f, indent=2)
    print(f"  ✅ aws_critical_alerts.json - {len(critical)} records (for alert Story 1)")


def generate_azure_files():
    print("Generating Azure telemetry files...")

    # Azure Batch 1: Gen-2 BMW X5 + Honda Accord (60 records)
    records = []
    for i in range(1, 31):
        records.append(make_gen2_record(make_vin("VIN_AZURE_BMW_", i), "AZURE_BLOB"))
    for i in range(1, 31):
        records.append(make_gen2_record(make_vin("VIN_AZURE_HON_", i), "AZURE_BLOB"))
    with open(os.path.join(RAW_EVENTS_DIR, "azure_gen2_bmw_honda.json"), "w") as f:
        json.dump(records, f, indent=2)
    print(f"  ✅ azure_gen2_bmw_honda.json - {len(records)} records")

    # Azure Batch 2: Gen-3 Tesla + Toyota Tacoma with ADAS (70 records)
    records = []
    for i in range(1, 36):
        records.append(make_gen3_record(make_vin("VIN_AZURE_TES_", i), "AZURE_BLOB"))
    for i in range(1, 36):
        records.append(make_gen3_record(make_vin("VIN_AZURE_TAC_", i), "AZURE_BLOB"))
    with open(os.path.join(RAW_EVENTS_DIR, "azure_gen3_tesla_tacoma.json"), "w") as f:
        json.dump(records, f, indent=2)
    print(f"  ✅ azure_gen3_tesla_tacoma.json - {len(records)} ADAS-enabled records")


# ── Generate Vehicle Manual PDFs ───────────────────────────────────────────────

MANUAL_CONTENT = {
    "ford_f150_2023_manual.pdf": {
        "title": "Ford F-150 2023 Owner's Manual",
        "make": "Ford", "model": "F-150", "year": 2023,
        "sections": [
            ("Engine Maintenance", """
The 3.5L EcoBoost V6 engine requires synthetic 5W-30 oil. Oil change intervals are every 7,500 miles
under normal driving conditions. The engine temperature should remain between 195degF and 220degF (90degC-104degC)
during normal operation. If the temperature gauge exceeds the midpoint, pull over safely immediately.

Diagnostic Code P0300 indicates a random or multiple cylinder misfire. Common causes include worn spark
plugs, faulty ignition coils, or low fuel pressure. The F-150 uses COP (Coil-On-Plug) ignition.
Replace spark plugs every 60,000 miles with Motorcraft SP-515 plugs.
"""),
            ("Transmission", """
The 10-speed SelectShift automatic transmission fluid should be checked at 150,000 miles under normal
conditions. Use only Motorcraft MERCON ULV fluid. Code P0700 indicates a Transmission Control System
malfunction - schedule service immediately as continued driving may cause irreversible damage.

Towing capacity: 13,200 lbs with Max Trailer Tow Package. Ensure trailer brakes are functional when
towing over 5,000 lbs.
"""),
            ("ADAS Safety Systems", """
The Ford Co-Pilot360 system includes Pre-Collision Assist with Automatic Emergency Braking (AEB),
Lane-Keeping System, Auto High-Beam Headlamps, and Reverse Sensing System.

If the FORWARD_COLLISION_WARNING alert triggers repeatedly, check for obstruction on the front radar
sensor (located behind the Ford logo). Clean the sensor with a soft damp cloth. Recalibration may be
required after windshield replacement - visit a certified Ford service center.
"""),
            ("Fault Codes Reference", """
P0300 - Random/Multiple Cylinder Misfire: Check spark plugs, ignition coils, fuel injectors.
P0420 - Catalyst Efficiency Below Threshold: Catalytic converter may require replacement.
P0171 - System Too Lean Bank 1: Check for vacuum leaks, faulty MAF sensor, or low fuel pressure.
P0455 - EVAP System Large Leak: Inspect gas cap seal, EVAP canister, and purge valve.
U0100 - Lost Communication with ECM: Check battery voltage and CAN bus connections.
"""),
        ]
    },
    "toyota_camry_2024_manual.pdf": {
        "title": "Toyota Camry 2024 Service Manual",
        "make": "Toyota", "model": "Camry", "year": 2024,
        "sections": [
            ("Engine - 2.5L Dynamic Force", """
The Camry's 2.5L Dynamic Force 4-cylinder engine (A25A-FXS hybrid variant) achieves 44 mpg combined.
Oil specification: 0W-16 synthetic. Oil life monitor alerts at 5,000-mile intervals.

Engine temperature operating range: 80degC-90degC (176degF-194degF). The thermostat opens at 80degC.
If coolant temperature exceeds 110degC, the system enters limp mode - stop safely and call Toyota Roadside.
"""),
            ("Hybrid Battery System", """
The nickel-metal hydride (NiMH) high-voltage battery is rated for 150,000 miles or 10 years.
Battery voltage should read 230-270V DC under normal operation.
Code P0A0F (Drive Motor "A" Performance) indicates hybrid battery degradation.

Warning: The hybrid system operates at lethal voltages. Only Toyota-certified technicians should
service the orange high-voltage cables.
"""),
            ("Brake System - Regenerative", """
The Camry Hybrid uses regenerative braking to recover kinetic energy. The brake pedal feel may
differ from conventional vehicles - this is normal. Hydraulic brakes engage at harder pedal pressure.

TPMS sensors require re-initialization after any tire rotation or replacement. Use Toyota Techstream
software to reset TPMS IDs.
"""),
        ]
    },
    "bmw_x5_2023_manual.pdf": {
        "title": "BMW X5 xDrive40i 2023 Owner's Handbook",
        "make": "BMW", "model": "X5", "year": 2023,
        "sections": [
            ("Engine - B58 3.0L Turbocharged", """
The B58 inline-6 requires BMW Longlife-04 approved 0W-30 or 5W-30 synthetic oil. BMW Condition Based
Service (CBS) monitors oil quality and alerts when a change is required (typically 10,000-15,000 miles).

Boost pressure nominal: 18.1 psi. Fault P0299 (Turbocharger Underboost) indicates a boost leak -
common failure points are the charge pipe between the turbo and intercooler.
"""),
            ("iDrive & Digital Systems", """
The BMW Live Cockpit Professional runs BMW OS 7.0. System updates are delivered OTA (Over The Air).
If the iDrive system freezes, hold the volume knob for 30 seconds to perform a hard reset.

U-codes (U0001, U0100) indicate CAN bus communication failures. These often accompany a dead 12V
auxiliary battery - replace with a BMW-approved AGM battery (92Ah, Group H8).
"""),
            ("xDrive AWD System", """
The xDrive all-wheel drive system continuously varies torque split between front and rear axles.
Normal rear bias is 40% front / 60% rear. Under wheelspin the system can send 100% torque to either axle.

Fault B2AAA indicates xDrive transfer case motor failure. Do not engage Sport+ mode if this fault is active.
"""),
        ]
    },
    "tesla_model3_2024_manual.pdf": {
        "title": "Tesla Model 3 2024 Owner's Manual",
        "make": "Tesla", "model": "Model 3", "year": 2024,
        "sections": [
            ("Battery & Charging", """
The Long Range Model 3 features an 82 kWh lithium iron phosphate (LFP) battery pack.
Optimal daily charge level: 80% for longevity. Charge to 100% only before long trips.

DC Fast Charging (Supercharger V3): up to 250 kW peak. Charging speed reduces above 80% SOC to protect cells.
Battery temperature is actively managed - pre-condition the battery in cold weather before driving.

Fault: BMS_a066 - Cell imbalance detected. Schedule a service appointment via the Tesla app.
"""),
            ("Autopilot & Full Self-Driving", """
Tesla Autopilot uses 8 external cameras, ultrasonic sensors, and a forward-facing radar (2023 models).
FSD Beta requires a driver attention score above 85% - repeated disengagements due to inattention
will disable FSD for the session.

LANE_DEPARTURE alerts trigger when the vehicle crosses lane markings without turn signal activation.
AUTO_BRAKE engages when forward collision risk exceeds the configured sensitivity threshold.

Note: Autopilot is a driver assistance system. The driver must remain alert and in control at all times.
"""),
            ("Maintenance Schedule", """
Tesla vehicles have no oil changes, no spark plugs, and no transmission fluid.
Recommended annual checks:
- Brake fluid: Test for moisture content every 2 years.
- Cabin air filter: Replace every 2 years (HEPA filter every 3 years).
- Tire rotation: Every 6,250 miles.
- AC desiccant bag: Replace every 6 years.

The 12V lithium-ion auxiliary battery requires replacement approximately every 4 years.
"""),
        ]
    },
    "gm_silverado_2024_manual.pdf": {
        "title": "GM Chevrolet Silverado 2024 Service Manual",
        "make": "GM", "model": "Silverado 1500", "year": 2024,
        "sections": [
            ("Engine - 6.2L V8 EcoTec3", """
The 6.2L EcoTec3 V8 uses Dynamic Fuel Management (DFM) to deactivate up to 7 cylinders under
light load. A slight vibration or drone at 1,400-1,800 RPM is normal DFM operation.

Oil: Dexos1 Gen3 full synthetic 0W-20. Oil life monitor tracks engine load, temperature, and idle time.
Code P0521 (Oil Pressure Sensor Performance) - verify oil level before condemning the sensor.
"""),
            ("Trailering & Towing", """
Maximum tow rating: 13,300 lbs (with Duramax diesel and Max Trailering Package).
Trailer Sway Control automatically applies individual wheel brakes if trailer oscillation is detected.

Integrated Trailer Brake Controller supports electric trailer brakes up to 4 axles.
Fault P0878 (Transmission Fluid Pressure Sensor B Circuit High) may appear when towing near max capacity
in high ambient temperatures - allow transmission to cool before resuming.
"""),
            ("Safety Systems", """
Super Cruise hands-free driver assistance works on 200,000+ miles of compatible divided highways.
The driver attention camera monitors eye gaze and head position. Green light = hands-free mode active.

Forward Collision Alert and Automatic Emergency Braking are standard on all 2024 Silverado trims.
Calibration is required if the front bumper, grille, or windshield is replaced.
"""),
        ]
    },
}


def generate_pdfs():
    """Generate realistic vehicle manual PDFs using fpdf2."""
    try:
        from fpdf import FPDF
    except ImportError:
        print("\n⚠️  fpdf2 not installed. Installing now...")
        os.system("pip install fpdf2 -q")
        from fpdf import FPDF

    print("\nGenerating vehicle manual PDFs...")

    for filename, content in MANUAL_CONTENT.items():
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Cover page
        pdf.set_font("Helvetica", "B", 24)
        pdf.set_fill_color(20, 40, 80)
        pdf.rect(0, 0, 210, 60, "F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(15, 15)
        pdf.multi_cell(180, 10, content["title"], align="C")

        pdf.set_font("Helvetica", "", 12)
        pdf.set_xy(15, 45)
        pdf.cell(0, 8, f"Model Year: {content['year']}  |  Make: {content['make']}  |  Model: {content['model']}", align="C")

        # Reset colour
        pdf.set_text_color(0, 0, 0)
        pdf.ln(20)

        # Table of contents header
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_fill_color(230, 235, 245)
        pdf.cell(0, 10, "Table of Contents", fill=True)
        pdf.ln(4)
        pdf.set_font("Helvetica", "", 11)
        for i, (section_title, _) in enumerate(content["sections"], 1):
            pdf.cell(0, 7, f"  {i}. {section_title}")
            pdf.ln()

        # Sections
        for section_title, section_body in content["sections"]:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 16)
            pdf.set_fill_color(20, 40, 80)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 12, f"  {section_title}", fill=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(6)
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 6, section_body.strip())

        out_path = os.path.join(RAW_MANUALS_DIR, filename)
        pdf.output(out_path)
        size_kb = os.path.getsize(out_path) // 1024
        print(f"  ✅ {filename} - {size_kb} KB, {len(content['sections'])} sections")


# ── Summary ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    generate_aws_files()
    generate_azure_files()
    generate_pdfs()

    # Count totals
    json_files = [f for f in os.listdir(RAW_EVENTS_DIR) if f.endswith(".json")]
    pdf_files  = [f for f in os.listdir(RAW_MANUALS_DIR) if f.endswith(".pdf")]
    total_records = 0
    for jf in json_files:
        with open(os.path.join(RAW_EVENTS_DIR, jf)) as f:
            total_records += len(json.load(f))

    print(f"""
╔══════════════════════════════════════════════════════╗
║          Test Data Generation Complete ✅            ║
╠══════════════════════════════════════════════════════╣
║  JSON telemetry files : {len(json_files):<5} files                    ║
║  Total telemetry rows : {total_records:<5} records                  ║
║  Vehicle manual PDFs  : {len(pdf_files):<5} PDFs                    ║
║                                                      ║
║  AWS sources  → aws_gen1_ford_toyota.json            ║
║                 aws_gen2_gm_ford.json                ║
║                 aws_critical_alerts.json             ║
║  Azure sources→ azure_gen2_bmw_honda.json            ║
║                 azure_gen3_tesla_tacoma.json         ║
║                                                      ║
║  Manuals cover: Ford F-150, Toyota Camry,            ║
║                 BMW X5, Tesla Model 3, GM Silverado  ║
╚══════════════════════════════════════════════════════╝
""")
