import pyodbc
from django.conf import settings
import re


class SQLServerService:

    def __init__(self):
        self.conn_string = settings.DB_CONN_STRING

    def get_connection(self):
        return pyodbc.connect(self.conn_string)

    # corregido: ahora es método de clase
    def extraer_sp(self, comando: str):
        match = re.search(r'EXEC\s+([a-zA-Z0-9_\.\[\]]+)', comando, re.IGNORECASE)
        return match.group(1) if match else None

    #  obtiene código del stored procedure
    def get_sp_definition(self, nombre_sp):
        try:
            query = f"""
                SELECT sm.definition
                FROM sys.sql_modules sm
                JOIN sys.objects o ON sm.object_id = o.object_id
                WHERE o.name = '{nombre_sp.split('.')[-1]}'
            """
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    row = cursor.fetchone()
                    return row[0] if row else None
        except Exception as e:
            print(f"Error al obtener definición del SP: {e}")
            return None
        

    def extraer_dml(self, sql: str):
        try:
            if not sql:
                return []

            # quitar comentarios simples --
            sql = re.sub(r'--.*', '', sql)

            # dividir por ; o saltos de línea
            sentencias = re.split(r';|\n', sql)

            dml = []
            for s in sentencias:
                s_clean = s.strip().upper()

                if (
                    s_clean.startswith("INSERT") or
                    s_clean.startswith("UPDATE") or
                    s_clean.startswith("DELETE") or
                    s_clean.startswith("TRUNCATE")
                ):
                    dml.append(s.strip())

            return dml
        except Exception as e:
            print(f"Error al extraer DML: {e}")
            return []
        
    def extraer_dml_completo(self, sql: str):
        try:
            if not sql:
                return []

            # quitar comentarios simples
            sql = re.sub(r'--.*', '', sql)

            patrones = [
                r'(INSERT\s+INTO[\s\S]+?)(?=INSERT|UPDATE|DELETE|TRUNCATE|$)',
                r'(UPDATE[\s\S]+?)(?=INSERT|UPDATE|DELETE|TRUNCATE|$)',
                r'(DELETE\s+FROM[\s\S]+?)(?=INSERT|UPDATE|DELETE|TRUNCATE|$)',
                r'(TRUNCATE\s+TABLE[\s\S]+?)(?=INSERT|UPDATE|DELETE|TRUNCATE|$)',
            ]

            resultados = []

            for patron in patrones:
                matches = re.findall(patron, sql, re.IGNORECASE)
                resultados.extend([m.strip() for m in matches])

            return resultados

        except Exception as e:
            print(f"Error extrayendo DML completo: {e}")
            return []      
        
    def extraer_dml_detalle(self, sql: str):
        try:
            if not sql:
                return []

            # quitar comentarios
            sql = re.sub(r'--.*', '', sql)

            patrones = [
                (r'INSERT\s+INTO\s+([a-zA-Z0-9_\.\[\]]+)', 'INSERT'),
                (r'UPDATE\s+([a-zA-Z0-9_\.\[\]]+)', 'UPDATE'),
                (r'DELETE\s+FROM\s+([a-zA-Z0-9_\.\[\]]+)', 'DELETE'),
                (r'TRUNCATE\s+TABLE\s+([a-zA-Z0-9_\.\[\]]+)', 'TRUNCATE'),
            ]

            resultados = []
            vistos = set()  # clave para evitar duplicados

            for patron, tipo in patrones:
                matches = re.finditer(patron, sql, re.IGNORECASE)

                for m in matches:
                    tabla = m.group(1).upper().strip()

                    clave = (tipo, tabla)

                    # evita duplicados SOLO si es misma acción + tabla
                    if clave in vistos:
                        continue

                    vistos.add(clave)
                    resultados.append({
                        "action": tipo,
                        "table": tabla,
                        "statement": m.group(0).strip()
                    })

            return resultados

        except Exception as e:
            print(f"Error extrayendo detalle DML: {e}")
            return []
            
    #  MÉTODO PRINCIPAL MEJORADO
    def get_jobs(self):
        query = """
        SELECT
            j.job_id AS IdJob,
            j.name AS NombreJob,
            j.enabled AS EstadoJob,

            CASE 
                WHEN s.enabled = 1 THEN 'SI'
                ELSE 'NO'
            END AS TieneAgendamientoActivo,

            msdb.dbo.agent_datetime(h.run_date, h.run_time) AS FechaUltimaEjecucion,

            js.step_id AS NumeroPaso,
            js.step_name AS NombrePaso,
            js.command AS ComandoSQL,
            js.subsystem,
            js.database_name

        FROM msdb.dbo.sysjobs j

        LEFT JOIN msdb.dbo.sysjobsteps js
            ON j.job_id = js.job_id

        LEFT JOIN msdb.dbo.sysjobschedules jsch
            ON j.job_id = jsch.job_id

        LEFT JOIN msdb.dbo.sysschedules s
            ON jsch.schedule_id = s.schedule_id

        LEFT JOIN (
            SELECT 
                job_id,
                MAX(instance_id) AS last_instance_id
            FROM msdb.dbo.sysjobhistory
            WHERE step_id = 0
            GROUP BY job_id
        ) h_last
            ON j.job_id = h_last.job_id

        LEFT JOIN msdb.dbo.sysjobhistory h
            ON h.instance_id = h_last.last_instance_id

        WHERE j.enabled = 1
        ORDER BY j.name, js.step_id;
        """

        jobs = {}

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)

                    if cursor.description is None:
                        return []

                    columns = [col[0] for col in cursor.description]

                    for row in cursor.fetchall():
                        item = dict(zip(columns, row))
                        job_id = item["IdJob"]
                        print(f"Procesando Job: {item['NombreJob']} - Paso: {item['NombrePaso']}")  # Debug
                        print(f"Comando SQL: {item['ComandoSQL']}")  # Debug
                        print(f"Comando IdJob: {item['IdJob']}")  # Debug
                        # Agrupar por job
                        if job_id not in jobs:
                            jobs[job_id] = {
                                "IdJob": job_id,
                                "NombreJob": item["NombreJob"],
                                "EstadoJob": item["EstadoJob"],
                                "TieneAgendamientoActivo": item["TieneAgendamientoActivo"],
                                "FechaUltimaEjecucion": item["FechaUltimaEjecucion"],
                                "Steps": []
                            }

                        comando = item.get("ComandoSQL", "")
                        sp_name = self.extraer_sp(comando)

                        codigo_sp = None
                        dml_encontrado = []

                        if sp_name:
                            codigo_sp = self.get_sp_definition(sp_name)
                            dml_encontrado = self.extraer_dml(codigo_sp)
                            dml_completo = self.extraer_dml_completo(codigo_sp)
                            dml_detalle = self.extraer_dml_detalle(codigo_sp)
                        else:
                            dml_encontrado = self.extraer_dml(comando)
                            dml_completo = self.extraer_dml_completo(comando)
                            dml_detalle = self.extraer_dml_detalle(comando)

                        print("dml_encontrado: ",dml_encontrado) # Debug
                        print("dml_completo: ",dml_completo) # Debug
                        print("dml_detalle: ",dml_detalle) # Debug

                        jobs[job_id]["Steps"].append({
                            "NumeroPaso": item["NumeroPaso"],
                            "NombrePaso": item["NombrePaso"],
                            "ComandoSQL": comando,
                            "DML": dml_encontrado, 
                            "DML_Completo": dml_completo,
                            "StoredProcedure": sp_name,
                            "DML_Detalle": dml_detalle,
                            "CodigoSP": codigo_sp,
                            "BaseDatos": item["database_name"],
                        })

            return list(jobs.values())
        except Exception as e:
            return {"error": str(e)}