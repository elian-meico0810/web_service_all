import os
import re
import pyodbc 
import pythoncom
import win32com.client
from django.conf import settings
from datetime import date
import calendar as cal 
from rest_framework import viewsets
from rest_framework.decorators import action
from apps.base.extensions.helpers.custom_exception import CustomException
from apps.scripts.api.serializers.scripts_serializers import ScriptSqlServerSerializer
from apps.base.extensions.custom_pagination.custom_pagination import BasicPagination
from apps.base.extensions.helpers.format_response import FormatResponse
from apps.base.extensions.utils import formatErrors

class ScriptsViewSet(viewsets.GenericViewSet):
    model = None
    pagination_class = BasicPagination
    serializer_class = ScriptSqlServerSerializer
    list_serializer_class = ScriptSqlServerSerializer
    queryset = None


    # Configura tu conexión a SQL Server
    def extract_sql_from_rpt(self, rpt_path: str):
        """Extrae la consulta SQL de un archivo .rpt de Crystal Reports y asigna automáticamente los parámetros según la fecha actual."""
        try:
            print("Iniciando conexión con CrystalRuntime...")
            pythoncom.CoInitialize()
            cr_app = win32com.client.Dispatch("CrystalRuntime.Application")
            rpt = cr_app.OpenReport(rpt_path)

            # Obtener información de la fecha actual
            today = date.today()
            year = today.year
            month = today.month
            _, last_day = cal.monthrange(year, month)
            start_date = date(2024, 12, 1).strftime("%Y-%m-%d") # year, month, 1
            end_date = date(2024, 12, 31).strftime("%Y-%m-%d") # year, month, last_day

            # Asignar valores automáticos a los parámetros del reporte
            for param_field in rpt.ParameterFields:
                name = param_field.ParameterFieldName.lower()

                # Condiciones según los nombres reales de tus parámetros en español
                if "año" in name or "ano" in name:
                    param_field.AddCurrentValue(2024)
                elif "periodo" in name:
                    param_field.AddCurrentValue(12)
                elif "fecini" in name:
                    param_field.AddCurrentValue(start_date)
                elif "fechfin" in name:
                    param_field.AddCurrentValue(end_date)
                else:
                    # Si aparece algún otro parámetro no esperado, se asigna vacío
                    print(f"⚠ Parámetro '{name}' no reconocido, asignando valor vacío")
                    param_field.AddCurrentValue("")

            # Extraer el SQL del reporte sin mostrar ventanas de parámetros
            sql_query = rpt.SQLQueryString
            if not sql_query:
                CustomException.throw("No se encontró SQL en el reporte.")

            pythoncom.CoUninitialize()
            print("====================================================================================================")
            
            return [sql_query] if sql_query else []
        except Exception as e:
            pythoncom.CoUninitialize()
            raise e


    def execute_sql(self, sql: str):
        """Ejecuta una consulta SQL y devuelve solo el primer registro."""
        try:
            print("Ejecución de una consulta SQL en SQL Server")
            print("====================================================================================================")   

            sql_original = sql.strip()  

            #Si la consulta comienza con SELECT, agregamos TOP 1
            if re.match(r'(?i)^select', sql_original):
                # Evitar duplicar TOP si ya existe
                if not re.search(r'(?i)\btop\s+\d+', sql_original):
                    # Manejar el caso de SELECT DISTINCT
                    if re.match(r'(?i)^select\s+distinct', sql_original):
                        sql_modified = re.sub(r'(?i)^select\s+distinct', 'SELECT DISTINCT TOP 1', sql_original)
                    else:
                        sql_modified = re.sub(r'(?i)^select', 'SELECT TOP 1', sql_original)
                else:
                    sql_modified = sql_original  # Ya tiene TOP definido
            else:
                sql_modified = sql_original  # No es SELECT, no se modifica 

            print(sql_modified)
            # Ejecutar la consulta modificada
            with pyodbc.connect(settings.DB_CONN_STRING) as connection:
                cursor = connection.cursor()
                cursor.execute(sql_modified)
                columns = [column[0] for column in cursor.description] if cursor.description else []
                results = cursor.fetchall()
                data = [dict(zip(columns, row)) for row in results] if columns else []  

            print(f"registros totales devueltos {len(data)}")
            print("====================================================================================================")
            return data 
        except Exception as e:
            raise e


    def list_arslmfil_sql_server(self):
        """
            Ejecuta una consulta SQL en SQL Server 
            para obtener los tipos de contrato.
        """
        try:
            print("Ejecutando consulta SQL para listar tipos de contrato")
            print("====================================================================================================")

            # Consulta SQL a ejecutar
            sql_query = """
                SELECT tc.tipo, tc.descripcion 
                FROM arslmfil_sql ar
                INNER JOIN TIPOCONTRATOMEICO_SQL tc ON ar.phone_ext_2 = tc.tipo
                GROUP BY tc.tipo, tc.descripcion
            """

            # Conectar a la base de datos SQL Server usando cadena desde settings
            with pyodbc.connect(settings.DB_CONN_STRING) as connection:
                cursor = connection.cursor()

                # Ejecutar la consulta
                cursor.execute(sql_query)
                columns = [column[0] for column in cursor.description] if cursor.description else []
                results = cursor.fetchall()

                # Convertir resultados en una lista de diccionarios
                data = [dict(zip(columns, row)) for row in results] if columns else []

            print(f"Registros totales devueltos: {len(data)}")
            print("====================================================================================================")
            return data

        except Exception as e:
            raise e


    @action(methods=['POST'], detail=False, url_path="extract-sql-folder")
    def extract_sql_from_folder(self, request, *args, **kwargs):
        """
            Itera a través de una carpeta de archivos .rpt, 
            extrae consultas SQL y ejecuta cada consulta para 
            devolver los resultados validados.
        """
        try:
            folder_path = request.data.get("path")
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                rpt_files = []

                # Buscamos todos los archivos .rpt en la carpeta indicada
                for dirpath, _, filenames in os.walk(folder_path):
                    for fname in filenames:
                        if fname.lower().endswith(".rpt"):
                            rpt_files.append(os.path.join(dirpath, fname))

                # Obtenemos los tipos válidos desde SQL Server (usando ORM)
                valid_contract_types = self.list_arslmfil_sql_server()
                valid_types = {item["tipo"]: item["descripcion"] for item in valid_contract_types}

                all_sql_results = {}

                for rpt_file in rpt_files:
                    # Extraemos las consultas SQL desde el archivo .rpt
                    sql_queries = self.extract_sql_from_rpt(rpt_file)
                    if sql_queries:
                        sql_execution_results = []

                        for sql in sql_queries:
                            # Ejecutamos la consulta SQL de la vista
                            exec_result = self.execute_sql(sql)

                            # Inicializamos valores por defecto
                            type_rpt_value = None
                            descripcion_value = None
                            exists_flag = False

                            # Validamos que el resultado tenga registros
                            if exec_result and isinstance(exec_result, list):
                                first_row = exec_result[0]

                                # Obtenemos el valor del campo TIPO (mayúsculas o minúsculas)
                                type_rpt_value = first_row.get("TIPO") or first_row.get("tipo")

                                # Validamos si el tipo existe en los tipos válidos
                                if type_rpt_value:
                                    if type_rpt_value in valid_types:
                                        descripcion_value = valid_types[type_rpt_value]
                                        exists_flag = True
                                    else:
                                        descripcion_value = "Tipo no encontrado en base de datos"
                                        exists_flag = False
                                else:
                                    descripcion_value = "Campo 'TIPO' no presente en el resultado"
                                    exists_flag = False
                            else:
                                descripcion_value = "Sin registros devueltos por la consulta"
                                exists_flag = False

                            # Agregamos la información formateada del archivo
                            sql_execution_results.append({
                                "file_route": str(rpt_file),
                                "file_name": os.path.basename(rpt_file),
                                "descripcion_query": descripcion_value,
                                "type": type_rpt_value,
                                "exist": exists_flag
                            })

                        # Guardamos los resultados por cada archivo
                        all_sql_results[rpt_file] = sql_execution_results
                    else:
                        raise Exception(f"No se encontraron consultas SQL en el archivo {rpt_file}")

            else:
                raise Exception(formatErrors(serializer.errors))
            return FormatResponse.successful(
                message=f"Se procesaron {len(rpt_files)} archivos .rpt correctamente",
                data=all_sql_results
            )
        except Exception as e:
            return FormatResponse.failed(e)
