class CustomException():

    def throw(message):
        """
        * Funcion que permite lanazar una excepcion personalizada, siempre y cuando se utlize el bloque try catch
        * @param $error , hace referencia a el error capturado por un catch, dentro de un bloque try catch.
        * @return  $custom_message , hace referencia a el mensaje personalalizado que devolvera el api o endpoint.
        """
        raise Exception(message)


