import os
import re
import pyodbc 
import pythoncom
import win32com.client
import calendar as cal 
from django.conf import settings
from datetime import date, datetime
import pywintypes
from rest_framework import viewsets
from rest_framework.decorators import action
from apps.base.utils import formatErrors
from apps.base.helpers.format_response import FormatResponse
from apps.base.helpers.custom_exception import CustomException
from apps.scripts.api.serializers.scripts_serializers import ScriptSqlServerSerializer
from apps.base.extensions.custom_pagination.custom_pagination import BasicPagination
from apps.base.reports.excel.download_extract_sql_server_template import download_extract_sql_server_template
import calendar

class ScriptsViewSet(viewsets.GenericViewSet):
    model = None
    pagination_class = BasicPagination
    serializer_class = ScriptSqlServerSerializer
    list_serializer_class = ScriptSqlServerSerializer
    queryset = None

        
    # Configura tu conexión a SQL Server
    def normalize_param_name(self, name: str):
        try:
            name = name.lower()
            name = name.replace("@", "")
            name = name.replace("ñ", "n") 
            name = name.replace("-", "")
            name = re.sub(r'[^a-z0-9]', '', name)
            return name
        except Exception as e:
            raise e



    def extract_tables_from_sql(self, sql: str):
        try:
            matches = re.findall(r'([A-Za-z0-9_]+\.[A-Za-z0-9_"]+)', sql)

            tables = set()

            for match in matches:
                table = match.split('.')[0]
                tables.add(table.strip())

            return sorted(tables) 
        except Exception as e:
            raise e
        
    def apply_parameters(self, report, params, start_date, end_date, year, month, day):
        """
            Reutilizamos tu lógica para principal y subreportes
        """
        report.EnableParameterPrompting = False

        for param_field in report.ParameterFields:
            raw_name = param_field.ParameterFieldName
            name = self.normalize_param_name(raw_name)

            print(f"PARAM: {raw_name}")

            try:
                param_field.ClearCurrentValueAndRange()

                default_values = {
                    'ano': year, 'year': year, 'anio': year,
                    'mes': month, 'month': month,
                    'dia': day, 'day': day,
                    'fecini': start_date,
                    'fecfin': end_date,
                    'division': '1',
                    'periodo': f"{year}{month:02d}",
                }

                assigned = False
                for key, value in default_values.items():
                    if key in name:
                        param_field.AddCurrentValue(value)
                        assigned = True
                        print(f"Asignado: {key} = {value}")
                        break

                if not assigned:
                    value_type = param_field.ValueType
                    if value_type == 7:
                        param_field.AddCurrentValue(start_date)
                    elif value_type == 12:
                        param_field.AddCurrentValue("")
                    else:
                        param_field.AddCurrentValue(0)

            except Exception as e:
                print(f"⚠ Error (ignorado): {e}")
                continue
            
    def extract_sql_from_rpt(self, rpt_path: str, params: dict = None):
        try:
            pythoncom.CoInitialize()
            cr_app = win32com.client.Dispatch("CrystalRuntime.Application")
            rpt = cr_app.OpenReport(rpt_path)

            # DB
            db_name = None
            for table in rpt.Database.Tables:
                location = table.Location.strip()
                db_name = location.split('.')[0]

            # Params seguros
            today = date.today()
            params = params or {}

            year = int(params.get("year", today.year))
            month = int(params.get("month", today.month))
            day = int(params.get("day", today.day))

            _, last_day = cal.monthrange(year, month)

            start_date = pywintypes.Time(datetime(year, month, day, 0, 0, 0))
            end_date = pywintypes.Time(datetime(year, month, last_day, 23, 59, 59))

            print(year, month, day, start_date, end_date)

            queries = []

            # 1. APLICAR PARAMETROS AL PRINCIPAL
            self.apply_parameters(rpt, params, start_date, end_date, year, month, day)

            main_sql = rpt.SQLQueryString
            if main_sql:
                queries.append({
                    "sql": main_sql,
                    "is_main": True,
                    "subreport_name": "No aplica"
                })

            #  2. SUBREPORTES (CON PARAMETROS TAMBIÉN)
            for section in rpt.Sections:
                for obj in section.ReportObjects:
                    if obj.Kind == 5:  # Subreport

                        subreport_name = obj.SubreportName  

                        sub = obj.OpenSubreport()

                        self.apply_parameters(sub, params, start_date, end_date, year, month, day)

                        sub_sql = sub.SQLQueryString

                        print("Subreporte:", subreport_name)

                        if sub_sql:
                            queries.append({
                                "sql": sub_sql,
                                "is_main": False,
                                "subreport_name": subreport_name  
                            })

            if not queries:
                raise Exception(f"No se encontraron consultas en {rpt_path}")

            return {
                "queries": queries,
                "db_name": db_name
            }

        except Exception as e:
            print(f"Error en extract_sql_from_rpt: {e}")
            raise

    def execute_sql(self, sql: str, db_name:  str = None):
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
            conn_str = settings.DB_CONN_STRING
            if db_name:
            # Reemplaza el valor de DATABASE en la cadena de conexión
                conn_str = re.sub(r"(DATABASE\s*=\s*)([^;]+)", fr"\1{db_name}", conn_str, flags=re.IGNORECASE)

            # Ejecutar la consulta modificada
            with pyodbc.connect(conn_str) as connection:
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
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)

            folder_path = serializer.validated_data.get("path")

            rpt_files = [
                os.path.join(dirpath, fname)
                for dirpath, _, filenames in os.walk(folder_path)
                for fname in filenames
                if fname.lower().endswith(".rpt")
            ]

            all_sql_results = {}

            for rpt_file in rpt_files:
                try:
                    result = self.extract_sql_from_rpt(rpt_file, serializer.validated_data)

                    queries = result.get("queries")
                    db_name = result.get("db_name")

                    records = []

                    for q in queries:
                        sql_query = q["sql"]
                        is_main = q["is_main"]
                        subreport_name = q["subreport_name"]
                        print("sql_query: ",sql_query)
                        tables = self.extract_tables_from_sql(sql_query)

                        if tables:
                            for table in tables:
                                records.append({
                                    "file_route": str(rpt_file),
                                    "db_name": str(db_name),
                                    "sql": str(sql_query),
                                    "file_name": os.path.basename(rpt_file),
                                    "tables": table,
                                    "es_principal": "SI" if is_main else "NO",
                                    "subreport_name": subreport_name,
                                    "descripcion_query": "Consulta extraída con éxito."
                                })
                        else:
                            records.append({
                                "file_route": str(rpt_file),
                                "db_name": str(db_name),
                                "sql": str(sql_query),
                                "file_name": os.path.basename(rpt_file),
                                "tables": "",
                                "es_principal": "SI" if is_main else "NO",
                                "subreport_name": "",
                                "descripcion_query": "Consulta extraída con éxito."
                            })
                    all_sql_results[rpt_file] = records
                except Exception as e:
                    # guardar error y continuar
                    all_sql_results[rpt_file] = [{
                        "file_route": str(rpt_file),
                        "db_name": "",
                        "sql": "",
                        "file_name": os.path.basename(rpt_file),
                        "tables": "",
                        "es_principal": "",
                        "subreport_name":"",
                        "descripcion_query": f"ERROR: {str(e)}",
                    }]
                    continue  
            result = download_extract_sql_server_template(all_sql_results)
            return result
        except Exception as e:
            return FormatResponse.failed(e)