base = {
    'dashboard': 'Dashboard',
    'sims': 'My SIMs',
    'configuration': 'Configuration',
    'users': 'Users',
    'admin': 'Admin',
    'logout': 'Log out',
    'overlay': 'Processing, please wait...',
    'language': 'Change language',
}

dashboard = {
    'nav': 'Dashboard',
    'data_usage': 'Data usage (MB)',
    'sms_usage': 'SMS usage',
    'data_volume': 'Data volume',
    'sms_volume': 'SMS volume',
    'last_orders': 'Last orders',
    'actual_status': 'Current SIM status',
    'last_update': 'Last updated:',
    'data_usage_txt': 'Data used',
    'volume_label': ['Enough', 'Low', 'No volume'],
    'sms_usage_txt': 'SMS sent',
    'sim_status_txt': 'SIM status',
    'sim_status_label': ['Enabled', 'Disabled   '],
    'order_date': 'Date',
    'order_id': 'ID',
    'order_type': 'Type',
    'order_quant': 'Quantity',
    'order_status_hd': 'Status'
}

get_sims = {
    'nav': 'My SIMs',
    'pagination_txt': 'Page size:',
    'filter_dis': 'Distributor',
    'filter_label': 'Label',
    'filter_reseller': 'Reseller',
    'btn_import': 'Import ICCIDs',
    'btn_export': 'Export SIMs',
    'status_hd': 'Status',
    'session_hd': 'Session',
    'label_hd': 'Label',
    'data_hd': 'Available MB',
    'status_act': 'Enabled',
    'status_des': 'Disabled',
    'session_on': 'Online',
    'session_at': 'Attached',
    'session_off': 'Offline',
    'btn_refresh': 'Refresh',
    'btn_nxt': 'Next',
    'btn_prv': 'Previous',
    'selected_sim': 'Selected SIMs',
    'btn_topup': 'Top up SIMs',
    'btn_assign': 'Assign SIMs',
    'sim_status': 'SIM status',
    'imei_block': 'IMEI block',
    'auto_topup': 'Auto top-up',
    'btn_act': 'Activate',
    'btn_dea': 'Deactivate',
    'select_user': 'Select a user:',
    'btn_cancel': 'Cancel',
    'btn_send': 'Send'
}

users = {
    'nav': 'Users',
    'dis_hd': 'Distributor',
    'reseller_hd': 'Reseller',
    'client_hd': 'Client',
    'filter': 'Search',
    'btn_register': 'Register',
    'name': 'Name',
    'company': 'Company',
    'phone': 'Phone',
    'state': 'State',
    'country': 'Country',
}

register_form = {
    'nav': 'Register',
    'first_name': 'Name*',
    'last_name': 'Surname*',
    'email': 'Email*',
    'rfc': 'RFC*',
    'company': 'Company name*',
    'street': 'Street*',
    'city': 'City*',
    'state': 'State*',
    'zip': 'ZIP*',
    'country': 'Country*',
    'phone_number': 'WhatsApp number*',
    'register_hd': 'Register',
    'data': 'Personal data',
    'required': '*Required field',
    'address': 'Address',
    'btn_cancel': 'Cancel',
    'btn_add': 'Add',
}

configuration = {
    'nav': 'Configuration',
    'limits_hd': 'Monthly limits',
    'limit_alert': 'Affects all SIMs globally',
    'sms_alert': 'A successful change of the SMS limit will be active inmediately.',
    'data_alert': 'A successful change of the Data limit will only affect new data connections, not currently active ones.',
    'data_hd': 'Data',
    'mt_hd': 'SMS MT',
    'mo_hd': 'SMS MO',
    'btn_save': 'Save'
}

sim_details = {
    'nav': 'SIM Details',
    'header': {
        'sim': 'SIM details',
        'network': 'Network Details',
        'assignation': 'Assignation',
        'data': 'Available MB',
        'data_usage': 'Data usage',
        'sms': 'Available SMS',
        'sms_usage': 'SMS usage',
    },
    'details': {
        'label': 'Label:',
        'end_date': 'End date:',
        'btn_location': ['See location', 'Location not available'],
        'state': 'SIM status:',
        'states_opt': ['Enabled', 'Disabled'],
        'session': 'Session:',
        'session_opt': ['Online', 'Attached', 'Offline'],
        'IP': 'IP location:',
        'operator': 'Operator/Country:',
        'access': 'Radio Access Technology:',
        'assign': ['Distributor', 'Reseller', 'Client']
    },
    'charts': {
        'last_update': 'Last update',
        'labels': {
            'use': ['Available  ', 'Used'],
            'data': 'Data used',
            'sms': 'SMS used',
        }
    },
    'sms': {
        'source': 'Source address',
        'commands': 'Commands',
        'btn_send': 'Send',
        'table': {
            'type': 'Type',
            'state': 'State',
            'sent': 'Submitted',
            'end': 'Finalized',
            'source': 'Source',
            'message': 'Message',
            'btn_refresh': 'Refresh',
        }
    }
}

user_details = {
    'nav': 'User details',
    'headers': {
        'details': 'User details',
        'address': 'Address',
        'security': 'Security',
        'reseller': 'Associated resellers',
        'client': 'Associated clients',
        'vehicle': 'Vehicles',
        'sim': 'Associated SIM',
    },
    'details': {
        'name': 'Name:',
        'surname': 'Surname:',
        'company': 'Company:',
        'phone': 'Phone:',
        'street': 'Address:',
        'city': 'City:',
        'zip': 'ZIP:',
        'state': 'State:',
        'country': 'Country:',
        'password': 'Password:',
        'total': 'Total SIM:',
    },
    'alerts': {
        'activate_hd': ['Are you sure you want to deactivate the user?', 'Are you sure you want to activate the user?'],
        'activate_lbl': ['This action will prevent it from logging in.', 'This will allow it to log in again.'],
        'delete_hd': 'Are you sure you want to delete the user?',
        'delete_lbl': 'This action cannot be undone.'
    },
    'buttons': {
        'update': 'Update',
        'activate': ['Activate', 'Deactivate'],
        'delete': 'Delete user',
        'cancel': 'Cancel',
        'confirm': 'Confirm',
        'save': 'Save',
    }
}
