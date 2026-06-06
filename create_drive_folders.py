import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']

def authenticate():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def create_folder(service, name, parent_id=None):
    metadata = {'name': name, 'mimeType': 'application/vnd.google-apps.folder'}
    if parent_id:
        metadata['parents'] = [parent_id]
    folder = service.files().create(body=metadata, fields='id').execute()
    print(f'Created: {name}')
    return folder['id']

def main():
    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)

    # Main folder
    main_id = create_folder(service, 'Vinnie Business')

    # Top level folders
    props_id    = create_folder(service, 'Properties',          main_id)
    lorries_id  = create_folder(service, 'Lorries',             main_id)
    mortgages_id= create_folder(service, 'Mortgages',           main_id)
    invoices_id = create_folder(service, 'Invoices & VAT',      main_id)
    business_id = create_folder(service, 'Business Documents',  main_id)
    accountant_id= create_folder(service,'Accountant',          main_id)

    # Invoice subfolders
    create_folder(service, 'Fuel Invoices',     invoices_id)
    create_folder(service, 'Property Invoices', invoices_id)

    # Accountant subfolders
    create_folder(service, 'VAT Returns',    accountant_id)
    create_folder(service, 'Annual Accounts',accountant_id)

    # Properties
    properties = [
        '5 Queensway Mildenhall',
        '5 Beeches Road West Row',
        '22 Fleming Avenue Mildenhall',
        '1 Bernards Close Mildenhall',
        '3 Bernards Close Mildenhall',
        '4 Bernards Close Mildenhall',
        '1A Vinrose Lodge Mildenhall',
        '5a Beeches Road West Row',
        '5b Beeches Road West Row',
        'Ponderosa West Row',
        'Ponderosa Annex West Row',
        'St Michaels Thetford',
        'Garrod House Flat 1 Lakenheath',
        'Garrod House Flat 2 Lakenheath',
        'Garrod House Flat 3 Lakenheath',
        'Garrod House Flat B Lakenheath',
        'Sparks Farm Hurdle Drove',
        'Cottage Lakenheath',
        'Airview House West Row',
        'Airview Annex West Row',
        'The Shed West Row',
    ]

    for prop in properties:
        prop_id = create_folder(service, prop, props_id)
        create_folder(service, 'Tenancy Documents',  prop_id)
        create_folder(service, 'Mortgage Documents', prop_id)
        create_folder(service, 'Compliance',         prop_id)

    # Lorries
    for i in range(1, 4):
        lorry_id = create_folder(service, f'Lorry {i}', lorries_id)
        create_folder(service, 'MOT & Service',   lorry_id)
        create_folder(service, 'Insurance',        lorry_id)
        create_folder(service, 'Legal Documents',  lorry_id)

    print('\nAll folders created successfully!')
    print(f'Main folder ID: {main_id}')

if __name__ == '__main__':
    main()
