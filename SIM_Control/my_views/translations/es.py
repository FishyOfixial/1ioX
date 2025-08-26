base = {
    'dashboard': 'Panel',
    'sims': 'Mis SIMs',
    'configuration': 'Configuración',
    'users': 'Usuarios',
    'admin': 'Administracion',
    'logout': 'Cerrar sesión',
    'overlay': 'Procesando, por favor espera...',
    'language': 'Cambiar idioma',
}

dashboard = {
    'nav': 'Panel',
    'data_usage': 'Uso de datos (MB)',
    'sms_usage': 'Uso de SMS',
    'data_volume': 'Volumen de datos',
    'sms_volume': 'Volumen de SMS',
    'last_orders': 'Últimos pedidos',
    'actual_status': 'Estado actual de la SIM',
    'last_update': 'Última actualización:',
    'data_usage_txt': 'Datos utilizados',
    'volume_label': ['Suficiente', 'Bajo', 'Sin volumen'],
    'sms_usage_txt': 'SMS utilizados',
    'sim_status_txt': 'Estado de SIMs',
    'sim_status_label': ['Habilitado', 'Deshabilitado'],
    'order_date': 'Fecha',
    'order_id': 'ID',
    'order_type': 'Tipo',
    'order_quant': 'Cantidad',
    'order_status_hd': 'Estado'
}

get_sims = {
    'nav': 'Mis SIMs',
    'pagination_txt': 'Tamaño de página:',
    'filter_dis': 'Distribuidor',
    'filter_label': 'Etiqueta',
    'filter_reseller': 'Revendedor',
    'btn_import': 'Importar ICCIDs',
    'btn_export': 'Exportar SIMs',
    'status_hd': 'Estado',
    'session_hd': 'Sesión',
    'label_hd': 'Etiqueta',
    'data_hd': 'MB disponibles',
    'status_act': 'Activado',
    'status_des': 'Desactivado',
    'session_on': 'En línea',
    'session_at': 'Conectada',
    'session_off': 'Fuera de línea',
    'btn_refresh': 'Refrescar',
    'btn_nxt': 'Siguiente',
    'btn_prv': 'Anterior',
    'selected_sim': 'SIM(s) seleccionadas',
    'btn_topup': 'Recargar SIMs',
    'btn_assign': 'Asignar SIMs',
    'sim_status': 'Estado',
    'imei_block': 'Bloquear IMEI',
    'auto_topup': 'Recarga automática',
    'btn_act': 'Activar',
    'btn_dea': 'Desactivar',
    'select_user': 'Selecciona un usuario:',
    'btn_cancel': 'Cancelar',
    'btn_send': 'Enviar'
}

users = {
    'nav': 'Usuarios',
    'dis_hd': 'Distribuidor',
    'reseller_hd': 'Revendedor',
    'client_hd': 'Cliente',
    'filter': 'Buscar',
    'btn_register': 'Registrar',
    'name': 'Nombre',
    'company': 'Empresa',
    'phone': 'Teléfono',
    'state': 'Estado',
    'country': 'País',
}

register_form = {
    'nav': 'Registrar',
    'first_name': 'Nombre*',
    'last_name': 'Apellido*',
    'email': 'Correo electrónico*',
    'rfc': 'RFC*',
    'company': 'Empresa*',
    'street': 'Dirección*',
    'city': 'Ciudad*',
    'state': 'Estado/Provincia*',
    'zip': 'Código postal*',
    'country': 'País*',
    'phone_number': 'Número de Whatsapp*',
    'register_hd': 'Registrar',
    'data': 'Datos personales',
    'required': '*Campo obligatorio',
    'address': 'Dirección',
    'btn_cancel': 'Cancelar',
    'btn_add': 'Agregar',
}

configuration = {
    'nav': 'Configuración',
    'limits_hd': 'Limite mensual',
    'limit_alert': 'Afecta todas las SIMs globalmente',
    'sms_alert': 'Un cambio exitoso en los limites de SMS se activará inmediatamente.',
    'data_alert': 'Un cambio exitoso en los limites de datos solamente afectará nuevas conexion, no las activas actualmente.',
    'data_hd': 'Datos',
    'mt_hd': 'Envío de SMS',
    'mo_hd': 'Recepción de SMS',
    'btn_save': 'Guardar'
}

sim_details = {
    'nav': 'Detalles de SIM',
    'header': {
        'sim': 'Detalles de la SIM',
        'network': 'Detalles de red',
        'assignation': 'Asignación',
        'data': 'MB disponibles',
        'data_usage': 'Uso de MB mensual',
        'sms': 'SMS disponibles',
        'sms_usage': 'Uso de SMS mensual',
    },
    'details': {
        'label': 'Etiqueta:',
        'end_date': 'Fecha de finalización:',
        'btn_location': ['Ver ubicación', 'Ubicación no disponible'],
        'state': 'Estado de la SIM:',
        'states_opt': ['Activado', 'Desactivado'],
        'session': 'Sesión:',
        'session_opt': ['En línea', 'Conectada', 'Fuera de línea'],
        'IP': 'Dirección IP:',
        'operator': 'Operador/País:',
        'access': 'Tecnología de acceso:',
        'assign': ['Distribuidor', 'Revendedor', 'Cliente']
    },
    'charts': {
        'last_update': 'Ultima actualización',
        'labels': {
            'use': ['Disponibles', 'Usados'],
            'data': 'Datos usados',
            'sms': 'SMS usados',
        }
    },
    'sms': {
        'source': 'Dirección de origen',
        'commands': 'Comandos',
        'btn_send': 'Envíar',
        'table': {
            'type': 'Tipo',
            'state': 'Estado',
            'sent': 'Enviado',
            'end': 'Finalizado',
            'source': 'Origen',
            'message': 'Mensaje',
            'btn_refresh': 'Refrescar',
        }
    }
}

user_details = {
    'nav': 'Detalles usuario',
    'headers': {
        'details': 'Detalles de usuario',
        'address': 'Dirección',
        'security': 'Seguridad',
        'reseller': 'Revendedores asociados',
        'client': 'Clientes asociados',
        'vehicle': 'Vehiculos',
        'sim': 'SIMs asociadas',
    },
    'details': {
        'name': 'Nombre:',
        'surname': 'Apellido:',
        'company': 'Empresa:',
        'phone': 'Teléfono:',
        'street': 'Calle:',
        'city': 'Ciudad:',
        'zip': 'C.P:',
        'state': 'Estado/Provincia:',
        'country': 'País:',
        'password': 'Contraseña:',
        'total': 'Total de SIMs:',
    },
    'alerts': {
        'activate_hd': ['¿Está seguro de que desea desactivar el usuario?', '¿Está seguro que desea activar al usuario?'],
        'activate_lbl': ['Esta acción impedirá que pueda iniciar sesión.', 'Esto permitirá que pueda iniciar sesión nuevamente.'],
        'delete_hd': '¿Está seguro que desea eliminar al usuario?',
        'delete_lbl': 'Esta acción no se puede deshacer.'
    },
    'buttons': {
        'update': 'Editar',
        'activate': ['Activar', 'Desactivar'],
        'delete': 'Eliminar usuario',
        'cancel': 'Cancelar',
        'confirm': 'Confirmar',
        'save': 'Guardar',
    }
}
