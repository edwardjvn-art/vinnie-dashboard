Property Portfolio Management Dashboard

A full-stack Flask web application built for a private client to manage a 21-property residential and commercial portfolio across Suffolk, UK. The application consolidates property management, fleet operations, container rental, financial tracking, and compliance into a single password-protected dashboard.

Live deployment: Private (client application — not publicly accessible)


Overview

Built independently from brief to deployment, this application replaced a manual spreadsheet-based workflow for a portfolio generating over £500,000 in estimated annual rental income across properties, lorries, and container rental. The client had no technical background — requirements were scoped directly through client conversations and the interface designed for non-technical daily use.


Features

Property Management


Full property register across 21 properties with rent status tracking (Paid / Due / Overdue / Vacant)
Per-property detail view with tenant information, tenancy end dates, and maintenance history
Mortgage tracking — lender, balance, monthly payment, type (Fixed/Tracker), expiry alerts
Net worth calculator across total portfolio value vs outstanding mortgage balances
Interactive property map (Suffolk coordinates, Leaflet.js)
Performance ranking — properties sorted by net monthly cashflow


Financial Tracking


Monthly cashflow overview — rental income vs mortgage outgoings, net cashflow
Bank account balances aggregated across multiple accounts
Combined income view — rental income + container revenue + lorry invoices
VAT invoice management with status tracking and Google Drive integration


Fleet & Logistics


Lorry fleet management — MOT expiry alerts, fuel cost tracking with VAT extraction
Per-lorry fuel and invoice breakdown
Outstanding invoice tracker with automated alert generation


Container Rental


Container inventory — size, type, hire status, hirer contact details, monthly rate
Occupancy rate and vacant income loss calculation
Hire start/end date tracking


Compliance & Legal


Document tracker — Gas Safety, EPC, EICR, HMO licence with expiry alerts
Tenancy renewal pipeline — properties with leases expiring within 6 months
Deposit protection register — scheme, certificate reference, protection status
Problem occupant case management — legal stage, solicitor, estimated monthly loss


Alerts & Activity


Automated alert system — overdue rent, upcoming MOT expiry, tracker mortgages, vacant properties, unpaid invoices
Activity log — last 50 actions with timestamp, category and icon
Failed login alerting via email notification


Authentication


bcrypt password hashing
Session-based authentication with login/logout
Email alert on failed login attempt (via environment variable credentials)



Tech Stack

ToolUseFlaskWeb framework, routing, session managementpandasCSV data loading and manipulationbcryptPassword hashingsmtplibEmail alertingJinja2HTML templatingLeaflet.jsInteractive property mapChart.jsCashflow and performance charts


Project Structure

├── app.py                  # Main Flask application — routes and data logic
├── templates/              # Jinja2 HTML templates
│   ├── overview.html
│   ├── properties.html
│   ├── finance.html
│   ├── lorries.html
│   ├── containers.html
│   ├── compliance.html
│   └── ...
├── data/                   # CSV data files (not committed)
│   ├── properties.csv
│   ├── tenants.csv
│   ├── cashflow.csv
│   └── ...
├── requirements.txt
└── README.md


Installation

bashgit clone https://github.com/edwardjvn-art/vinnie-dashboard.git
cd vinnie-dashboard
pip install -r requirements.txt

Set environment variables:

SECRET_KEY=your_secret_key
PASSWORD_HASH=your_bcrypt_hash
GMAIL_USER=your_email@gmail.com
GMAIL_PASS=your_app_password

Run:

bashpython app.py


Notes

Data files are not included in this repository — the application is live and in active use by the client. The dashboard is accessed via a private URL and is not publicly deployed.
