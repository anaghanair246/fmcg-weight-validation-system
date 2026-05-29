# Real-Time FMCG Weight Validation System

## Overview
A real-time quality assurance and product validation system developed for an FMCG meat processing workflow.

The system scans QR codes using a webcam, validates product weights against predefined tolerance ranges, and automatically accepts or rejects products while maintaining product traceability and analytics.

---

## Features

- Real-time QR code scanning using webcam
- Product identification using unique QR codes
- Live weight validation with tolerance checking
- Automatic accept/reject decision system
- Interactive Streamlit dashboard
- Acceptance vs rejection analytics using donut charts
- Individual product history tracking
- Search functionality for product traceability
- Real-time operational monitoring

---

## Tech Stack

- Python
- Streamlit
- OpenCV
- Pandas
- SQLite
- Data Visualization

---

## Project Structure

```bash
app.py
scanner.py
requirements.txt
products.csv
static/
```

---

## How to Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Try the Demo

Use these sample QR codes in the deployed app.

### QR Code 1
![QR 1](sample_qr_codes/qr_1.png)

### QR Code 2
![QR 2](sample_qr_codes/qr_2.png)

### QR Code 3
![QR 3](sample_qr_codes/qr_3.png)

---

## Future Improvements

- Cloud database integration
- Multi-camera support
- Production deployment
- Advanced analytics dashboard
- ERP integration


