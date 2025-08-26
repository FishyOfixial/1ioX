base = {
    'dashboard': 'Painel',
    'sims': 'Meus SIMs',
    'configuration': 'Configuração',
    'users': 'Usuários',
    'admin': 'Admin',
    'logout': 'Sair',
    'overlay': 'Processando, aguarde...',
    'language': 'Alterar idioma',
}

dashboard = {
    'nav': 'Painel',
    'data_usage': 'Uso de dados (MB)',
    'sms_usage': 'Uso de SMS',
    'data_volume': 'Volume de dados',
    'sms_volume': 'Volume de SMS',
    'last_orders': 'Últimos pedidos',
    'actual_status': 'Status atual da SIM',
    'last_update': 'Última atualização:',
    'data_usage_txt': 'Dados utilizados',
    'volume_label': ['Suficiente', 'Baixo', 'Sem volume'],
    'sms_usage_txt': 'SMS utilizados',
    'sim_status_txt': 'Status das SIMs',
    'sim_status_label': ['Ativada', 'Desativada'],
    'order_date': 'Data',
    'order_id': 'ID',
    'order_type': 'Tipo',
    'order_quant': 'Quantidade',
    'order_status_hd': 'Status'
}

get_sims = {
    'nav': 'Meus SIMs',
    'pagination_txt': 'Tamanho da página:',
    'filter_dis': 'Distribuidor',
    'filter_label': 'Etiqueta',
    'filter_reseller': 'Revendedor',
    'btn_import': 'Importar ICCIDs',
    'btn_export': 'Exportar SIMs',
    'status_hd': 'Status',
    'session_hd': 'Sessão',
    'label_hd': 'Etiqueta',
    'data_hd': 'MB disponíveis',
    'status_act': 'Ativada',
    'status_des': 'Desativada',
    'session_on': 'Online',
    'session_at': 'Conectada',
    'session_off': 'Offline',
    'btn_refresh': 'Atualizar',
    'btn_nxt': 'Próxima',
    'btn_prv': 'Anterior',
    'selected_sim': 'SIM(s) selecionadas',
    'btn_topup': 'Recarregar SIMs',
    'btn_assign': 'Atribuir SIMs',
    'sim_status': 'Status da SIM',
    'imei_block': 'Bloqueio por IMEI',
    'auto_topup': 'Recarga automática',
    'btn_act': 'Ativar',
    'btn_dea': 'Desativar',
    'select_user': 'Selecione um usuário:',
    'btn_cancel': 'Cancelar',
    'btn_send': 'Enviar'
}

users = {
    'nav': 'Usuários',
    'dis_hd': 'Distribuidor',
    'reseller_hd': 'Revendedor',
    'client_hd': 'Cliente',
    'filter': 'Pesquisar',
    'btn_register': 'Registrar',
    'name': 'Nome',
    'company': 'Empresa',
    'phone': 'Telefone',
    'state': 'Estado',
    'country': 'País',
}

register_form = {
    'nav': 'Registrar',
    'first_name': 'Nome*',
    'last_name': 'Sobrenome*',
    'email': 'E-mail*',
    'rfc': 'Identificação Fiscal**',
    'company': 'Nome da empresa*',
    'street': 'Endereço*',
    'city': 'Cidade*',
    'state': 'Estado/Província*',
    'zip': 'CEP*',
    'country': 'País*',
    'phone_number': 'Número do WhatsApp*',
    'register_hd': 'Registrar',
    'data': 'Dados pessoais',
    'required': '*Obrigatório',
    'address': 'Endereço',
    'btn_cancel': 'Cancelar',
    'btn_add': 'Adicionar',
}

configuration = {
    'nav': 'Configurações',
    'limits_hd': 'Limite mensal',
    'limit_alert': 'Afeta todos os SIMs globalmente',
    'sms_alert': 'Uma alteração bem-sucedida nos limites de SMS será aplicada imediatamente.',
    'data_alert': 'Uma alteração bem-sucedida nos limites de dados afetará apenas novas conexões, não as que já estão ativas.',
    'data_hd': 'Dados',
    'mt_hd': 'Envio de SMS',
    'mo_hd': 'Recebimento de SMS',
    'btn_save': 'Salvar'
}

sim_details = {
    'nav': 'Detalhes do SIM',
    'header': {
        'sim': 'Detalhes do SIM',
        'network': 'Detalhes da Rede',
        'assignation': 'Atribuição',
        'data': 'MB disponíveis',
        'data_usage': 'Uso de dados',
        'sms': 'SMS disponíveis',
        'sms_usage': 'Uso de SMS',
    },
    'details': {
        'label': 'Rótulo:',
        'end_date': 'Data de término:',
        'btn_location': ['Ver local', 'Local indisponível'],
        'state': 'Status do SIM:',
        'states_opt': ['Habilitado', 'Desabilitado'],
        'session': 'Sessão:',
        'session_opt': ['Online', 'Anexado', 'Offline'],
        'IP': 'Localização do IP:',
        'operator': 'Operadora/País:',
        'access': 'Tecnologia de Acesso por Rádio:',
        'assign': ['Distribuidor', 'Revendedor', 'Cliente']
    },
    'charts': {
        'last_update': 'Última atualização',
        'labels': {
            'use': ['Disponível', 'Usado'],
            'data': 'Dados usados',
            'sms': 'SMS usado',
        }
    },
    'sms': {
        'source': 'Endereço de origem',
        'commands': 'Comandos',
        'btn_send': 'Enviar',
        'table': {
            'type': 'Tipo',
            'state': 'Estado',
            'sent': 'Enviado',
            'end': 'Finalizado',
            'source': 'Fonte',
            'message': 'Mensagem',
            'btn_refresh': 'Atualizar',
        }
    }
}

user_details = {
    'nav': 'Detalhes do usuário',
    'headers': {
        'details': 'Detalhes do usuário',
        'address': 'Endereço',
        'security': 'Segurança',
        'reseller': 'Revendedores associados',
        'client': 'Clientes associados',
        'vehicle': 'Veículos',
        'sim': 'SIMs associados',
    },
    'details': {
        'name': 'Nome:',
        'surname': 'Sobrenome:',
        'company': 'Empresa:',
        'phone': 'Número de telefone:',
        'street': 'Rua:',
        'city': 'Cidade:',
        'zip': 'C.P:',
        'state': 'Estado/Província:',
        'country': 'País:',
        'password': 'Senha:',
        'total': 'Total de SIMs:',
    },
    'alerts': {
        'activate_hd': ['Tem certeza de que deseja desativar o usuário?', 'Tem certeza de que deseja ativar o usuário?'],
        'activate_lbl': ['Essa ação impedirá que ele consiga efetuar login.', 'Isso permitirá que ele faça login novamente.'],
        'delete_hd': 'Tem certeza de que deseja excluir o usuário?',
        'delete_lbl': 'Esta ação não pode ser desfeita.'
    },
    'buttons': {
        'update': 'Editar',
        'activate': ['Ativar', 'Desativar'],
        'delete': 'Excluir usuário',
        'cancel': 'Cancelar',
        'confirm': 'Confirmar',
        'save': 'Salvar',
    }
}
