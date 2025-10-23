
from datetime import datetime


def setActorRequest(request_data,user,update=False):
   
    """
    Funcion que setea el objeto request agregando los campos del usuario de creacion y actualizacion
    :params
    :request: request.data
    """
    request_data = request_data.copy()
    if update:
        if 'creation_user' in request_data : request_data.__delitem__('creation_user')
        request_data.__setitem__('user_update', user.id)
        if 'creation_date' in request_data : request_data.__delitem__('creation_date')
        request_data.__setitem__('last_update',str(datetime.now()))
    else :
        request_data.__setitem__('creation_user', user.id)
        request_data.__setitem__('user_update', user.id)
        if 'creation_date' in request_data : request_data.__delitem__('creation_date')
        if 'last_update' in request_data : request_data.__delitem__('last_update')
   
    if 'status' in request_data : request_data.__delitem__('status')
   
    return request_data


def formatErrors(errors):
   
    """
    Funcion que formatea los errores proporcionado por los serializadores
    """
    # Retorno de errores de prueba
    # return str(errors)
    # Codigos de errores
    # blank
    # does_not_exist
    # invalid
    # required
    # null
    # incorrect_type
    # not_a_dict
    # unique
    print("ERRORS", errors)
    first_error_key =next(iter(errors))
    fisrt_error = errors[first_error_key]
   
    if isinstance(fisrt_error,dict) : custom_message_error=fisrt_error[list(fisrt_error.keys())[0]][0]
    else : custom_message_error=fisrt_error[0]
   
    if custom_message_error == 'Este campo es requerido.':
        custom_message_error = f'El campo {first_error_key} es requerido.'
    if custom_message_error == 'Este campo no puede ser nulo.':
        custom_message_error = f'El campo {first_error_key} es requerido.'
    return custom_message_error
