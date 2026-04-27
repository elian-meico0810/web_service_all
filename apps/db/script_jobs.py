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
           
    def is_table_validate(self, name: str):
        try:
            if not name:
                return False

            name = name.strip().upper()

            if re.match(r'^\d{1,3}(\.\d{1,3}){3}$', name):
                return False

            if re.match(r'^\[\d{1,3}(\.\d{1,3}){3}\]$', name):
                return False

            invalidas = {"SELECT", "FROM", "WHERE", "SET", "INTO", "EXEC"}
            if name in invalidas:
                return False

            return True
        except Exception as e:
            print(f"Error validando nombre de tabla: {e}")
            return False
        

    def extraer_dml_detalle(self, sql: str):
        try:
            if not sql:
                return []

            # quitar comentarios
            sql = re.sub(r'--.*', '', sql)

            patrones = [
                (r'INSERT\s+(?:INTO\s+)?([a-zA-Z0-9_\.\[\]]+)', 'INSERT'),
                (r'UPDATE\s+[a-zA-Z0-9_\.\[\]]+\s+SET[\s\S]+?FROM\s+([a-zA-Z0-9_\.\[\]]+)', 'UPDATE'),
                (r'TRUNCATE\s+(?:TABLE\s+)?([a-zA-Z0-9_\.\[\]]+)', 'TRUNCATE'),
                (r'DELETE\s+FROM\s+([a-zA-Z0-9_\.\[\]]+)', 'DELETE'),
            ]

            resultados = []
            vistos = set()  # clave para evitar duplicados

            for patron, tipo in patrones:
                matches = re.finditer(patron, sql, re.IGNORECASE)

                for m in matches:

                    tabla = m.group(1).upper().strip()
                    tabla = tabla.replace('[','').replace(']','')

                    if not self.is_table_validate(tabla):
                        continue
                    
                    action = tipo

                    clave = (action, tabla)

                    if clave in vistos:
                        continue

                    vistos.add(clave)

                    resultados.append({
                        "action": action,
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

                        print(f"Procesando Job: {item['NombreJob']} - Paso: {item['NombrePaso']}")
                        print(f"Comando SQL: {item['ComandoSQL']}")

                        # Agrupar por job
                        if job_id not in jobs:
                            jobs[job_id] = {
                                "IdJob": job_id,
                                "NombreJob": item["NombreJob"],
                                "EstadoJob": item["EstadoJob"],
                                "TieneAgendamientoActivo": item["TieneAgendamientoActivo"],
                                "FechaUltimaEjecucion": item["FechaUltimaEjecucion"],
                                "steps_map": {}
                            }

                        comando = item.get("ComandoSQL", "")
                        comando_normalizado = re.sub(r'\s+', ' ', comando).strip().lower()

                        sp_name = self.extraer_sp(comando)

                        if sp_name:
                            codigo_sp = self.get_sp_definition(sp_name)
                            dml_encontrado = self.extraer_dml(codigo_sp)
                            dml_completo = self.extraer_dml_completo(codigo_sp)
                            dml_detalle = self.extraer_dml_detalle(codigo_sp)
                        else:
                            codigo_sp = None
                            dml_encontrado = self.extraer_dml(comando)
                            dml_completo = self.extraer_dml_completo(comando)
                            dml_detalle = self.extraer_dml_detalle(comando)

                        # fallback para SP sin detalle
                        if sp_name and not dml_detalle:
                            dml_detalle = [{
                                "action": "EXEC",
                                "table": sp_name.upper(),
                                "statement": f"EXEC {sp_name}"
                            }]

                        print("dml_encontrado: ", dml_encontrado)
                        print("dml_completo: ", dml_completo)
                        print("dml_detalle: ", dml_detalle)

                        if dml_detalle and dml_detalle[0].get("table"):

                            accion = dml_detalle[0].get("action")
                            tabla = dml_detalle[0].get("table")

                            step_key = f"DML|{accion}|{tabla}"

                        else:
                            continue

                        steps_map = jobs[job_id]["steps_map"]

                        # Crear si no existe
                        if step_key not in steps_map:
                            steps_map[step_key] = {
                                "ComandosSQL": [],
                                "DML": set(),
                                "DML_Completo": set(),
                                "DML_Detalle": [],
                                "DML_Detalle_keys": set(),
                                "StoredProcedure": sp_name,
                                "CodigoSP": codigo_sp,
                                "BaseDatos": item["database_name"],
                            }

                        step = steps_map[step_key]

                        # acumular comandos
                        if comando not in step["ComandosSQL"]:
                            step["ComandosSQL"].append(comando)

                        # acumular DML
                        step["DML"].update(dml_encontrado)
                        step["DML_Completo"].update(dml_completo)

                        # evitar duplicados en DML_Detalle
                        for det in dml_detalle:
                            key_det = (
                                det.get("action"),
                                det.get("table")
                            )

                            if key_det in step["DML_Detalle_keys"]:
                                continue

                            step["DML_Detalle_keys"].add(key_det)
                            step["DML_Detalle"].append(det)

                # convertir a lista final
                for job in jobs.values():
                    steps = []

                    for step in job["steps_map"].values():
                        step["DML"] = list(step["DML"])
                        step["DML_Completo"] = list(step["DML_Completo"])
                        step.pop("DML_Detalle_keys", None)
                        steps.append(step)

                    job["Steps"] = steps
                    job.pop("steps_map", None)

            return list(jobs.values())

        except Exception as e:
            return {"error": str(e)}