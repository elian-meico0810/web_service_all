import os
import re
import pyodbc  # Asegúrate de tener pyodbc instalado
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

            pythoncom.CoUninitialize()
            print("====================================================================================================")

            return [sql_query] if sql_query else ["No se encontró SQL en el reporte"]
        except Exception as e:
            pythoncom.CoUninitialize()
            raise e



    def execute_sql(self, sql: str):
        """Ejecuta una consulta SQL y devuelve los resultados."""
        try:
            print("Ejecuta la consulta a la DB en Sql Server")
            print("====================================================================================================")
            print("sql: ",sql)
            with pyodbc.connect(settings.DB_CONN_STRING) as conn:
                cursor = conn.cursor()
                cursor.execute(sql)
                columns = [col[0] for col in cursor.description] if cursor.description else []
                results = cursor.fetchall()
                data = [dict(zip(columns, row)) for row in results] if columns else []
            
            print("Retornamos las repuesta las vistas")
            print("====================================================================================================")
            return data
        except Exception as e:
           raise e


    @action(methods=['POST'], detail=False, url_path="extract-sql-folder")
    def extract_sql_from_folder(self, request, *args, **kwargs):
        """
            Itera a través de una carpeta de archivos .rpt, 
            extrae consultas SQL y ejecuta cada consulta para 
            devolver los resultados.
        """
        try:
            folder_path = request.data.get("path")
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                rpt_files = []
                for dirpath, _, filenames in os.walk(folder_path):
                    for fname in filenames:
                        if fname.lower().endswith(".rpt"):
                            rpt_files.append(os.path.join(dirpath, fname))

                all_sql_results = {}
                for rpt_file in rpt_files:
                    sql_queries = self.extract_sql_from_rpt(rpt_file)
                    if sql_queries:
                        sql_execution_results = []
                        for sql in sql_queries:
                            exec_result = self.execute_sql(sql)
                            sql_execution_results.append({
                                "sql": sql,
                                "result": exec_result
                            })
                        all_sql_results[rpt_file] = sql_execution_results
            else:
                raise Exception(formatErrors(serializer.errors))
            
            return FormatResponse.successful(
                message=f"Procesado {len(rpt_files)} .rpt archivo",
                data=all_sql_results
            )
        except Exception as e:
            return FormatResponse.failed(e)
