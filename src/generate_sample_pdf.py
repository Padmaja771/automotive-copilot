"""
generate_sample_pdf.py
----------------------
Generates a realistic synthetic Vehicle Manual PDF
for testing the Cortex PARSE_DOCUMENT pipeline.

Creates: data/raw_manuals/VIN123_engine_manual.pdf

Usage:
    python3 src/generate_sample_pdf.py
"""

import os

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def generate_vin123_manual():
    output_folder = os.path.join(os.path.dirname(__file__), "..", "data", "raw_manuals")
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, "VIN123_engine_manual.pdf")
    
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Vehicle Service Manual — Engine Systems", styles["Title"]))
    story.append(Spacer(1, 20))

    story.append(Paragraph("Chapter 1: Ignition System", styles["Heading1"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "The ignition system is responsible for initiating combustion in each engine cylinder. "
        "If Error Code P0300 (Random/Multiple Cylinder Misfire) is detected, the service technician "
        "must inspect all spark plugs and ignition coils before proceeding to more advanced diagnostics.",
        styles["BodyText"]
    ))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Torque Specifications for Ignition Coil Mounting Bolts: 15-20 lb-ft. "
        "Failure to follow this specification may result in coil bracket fatigue and recurrent misfire conditions.",
        styles["BodyText"]
    ))

    story.append(Spacer(1, 20))
    story.append(Paragraph("Chapter 2: Fuel System", styles["Heading1"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Normal fuel rail pressure at idle should read between 45-55 PSI. If fuel pressure is confirmed normal "
        "but P0300 persists, the root cause is most likely within the ignition subsystem, not the fuel delivery.",
        styles["BodyText"]
    ))

    story.append(Spacer(1, 20))
    story.append(Paragraph("Chapter 3: Emission Standards", styles["Heading1"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "An active P0300 code will cause the vehicle to fail emissions testing in most jurisdictions. "
        "The misfire must be resolved and the ECU's freeze frame data cleared prior to re-inspection. "
        "Required: Complete 2 warm-up drive cycles with no recurrence before clearing.",
        styles["BodyText"]
    ))

    doc.build(story)
    print(f"✅ Sample PDF created: {output_path}")


def generate_vin456_manual():
    output_folder = os.path.join(os.path.dirname(__file__), "..", "data", "raw_manuals")
    output_path = os.path.join(output_folder, "VIN456_brake_manual.pdf")
    
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Vehicle Service Manual — Brake Systems", styles["Title"]))
    story.append(Spacer(1, 20))

    story.append(Paragraph("Chapter 1: Brake Pad Inspection", styles["Heading1"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Brake pads should be inspected at every 12,000-mile service interval. "
        "The minimum acceptable pad thickness is 2mm. Below this threshold, the acoustic wear indicator "
        "will engage, producing an audible high-pitched squealing sound during braking.",
        styles["BodyText"]
    ))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Brake Pad Replacement Torque for Caliper Bolts: 35-40 lb-ft. "
        "After replacement, perform 5 moderate brake applications from 30 mph to bed in new pads.",
        styles["BodyText"]
    ))

    story.append(Spacer(1, 20))
    story.append(Paragraph("Chapter 2: Rotor Inspection", styles["Heading1"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "If squealing persists after pad replacement, inspect the rotor surface for glazing or scoring. "
        "Rotor minimum thickness: 22mm (front) and 10mm (rear). Rotors below minimum thickness must be replaced, not resurfaced.",
        styles["BodyText"]
    ))

    doc.build(story)
    print(f"✅ Sample PDF created: {output_path}")


if __name__ == "__main__":
    print("🏎️  Generating Synthetic Vehicle Manual PDFs...")
    generate_vin123_manual()
    generate_vin456_manual()
    print("\n✅ PDFs are ready in /data/raw_manuals/")
    print("   Now run: python3 src/ingest_pdfs.py")
