# 📄 Proyecto Crystal Reports API (Django + COM)

## 📌 Descripción

Este proyecto es una API desarrollada en **Django REST Framework** que permite ejecutar consultas y generar reportes utilizando **Crystal Reports (SAP)** mediante automatización COM (`win32com`).

 En pocas palabras:
- Recibe solicitudes desde API
- Ejecuta consultas SQL
- Abre reportes `.rpt` de Crystal Reports
- Devuelve resultados o reportes generados

⚠️ Importante:
- Crystal Reports SOLO funciona en Windows
- Requiere Python 3.10 de 32 bits
- No es compatible con Linux ni Docker Linux containers
- Depende de COM (automatización de Windows)

---

## 🧠 Tecnologías utilizadas

- Python 3.10 (32-bit) → Lenguaje base del proyecto
- Django 5.2.13 → Framework principal de backend
- Django REST Framework → Creación de APIs
- Crystal Reports Runtime (SAP) → Motor de reportes
- COM Automation (`win32com.client`) → Permite controlar Crystal Reports desde Python
- SQL Server (ODBC) → Conexión a base de datos

---

## 🧪 Entorno de desarrollo (venv)

El entorno virtual sirve para **aislar dependencias del proyecto** y evitar conflictos con otros proyectos de Python.

---

### 1️⃣ Verificar Python instalado

```bash
python --version

 ¿Qué hace esto?
Verifica que tengas instalado Python y confirma la versión.

⚠️ Debe ser:

Python 3.10.x (32-bit)
2️⃣ Crear entorno virtual
python -m venv venv

 ¿Qué hace esto?

Crea una carpeta llamada venv
Dentro instala un Python aislado para este proyecto
Evita conflictos con otros proyectos
3️⃣ Activar entorno virtual
▶️ Windows CMD
venv\Scripts\activate

 ¿Qué hace esto?

Activa el entorno virtual
Hace que pip install se instale SOLO en este proyecto
▶️ Windows PowerShell
.\venv\Scripts\Activate.ps1

Si da error de permisos:

Set-ExecutionPolicy Unrestricted -Scope Process

 ¿Qué hace esto?
Permite ejecutar scripts temporales en PowerShell.

4️⃣ Confirmar entorno activo
(venv) C:\proyecto>

 ¿Qué significa?

El entorno virtual está activo
Todo lo que instales afecta solo este proyecto
5️⃣ Instalar dependencias
pip install -r requirements.txt

 ¿Qué hace esto?
Instala todas las librerías necesarias:

Django
DRF
pyodbc
win32com
etc.
🚀 Ejecución del proyecto
python manage.py runserver 0.0.0.0:8000

 ¿Qué hace esto?

Inicia el servidor Django
Expone la API en http://localhost:8000