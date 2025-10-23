from rest_framework import viewsets
from rest_framework.decorators import action
from apps.scripts.api.serializers.scripts_serializers import ScriptSqlServerSerializer
from apps.base.extensions.custom_pagination.custom_pagination import BasicPagination
from apps.base.extensions.helpers.format_response import FormatResponse
from apps.base.extensions.utils import formatErrors

#GenericViewSet de web service
class ScriptsViewSet(viewsets.GenericViewSet):
    #llamamos a nuestro modelo
    model = None
    #Paginacion 
    pagination_class = BasicPagination
    #pasamos nuestro serilizador
    serializer_class = ScriptSqlServerSerializer
    # Personalizamos nuestro list_serializer_class segun nuestro serlizador
    list_serializer_class = ScriptSqlServerSerializer
    #imponemos caracteriticas sobre nuestros queryset
    queryset = None
    
    # Web service a Sql Server
    @action(methods=['POST'], detail=False, url_path="read-rpt")
    def read_rpt_in_sql_server(self, request, *args, **kwargs):
        """
        - Funcion que realiza una conexion a Sql Server 
        para validar si una factura existe en el
        reporte vs en ld DB de Sql Server
        """
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                print("holaaaaaaaa pase por aca")
            else:
                raise Exception(formatErrors(serializer.errors))
           
            return FormatResponse.successful(message="Conexión realizda con éxito", data=serializer.data)
        except Exception as e:
            return FormatResponse.failed(e)
       

