import os
import re
from apps.db.script_jobs import SQLServerService
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
from apps.jobs.api.serializers.jobs_serializers import JobSqlServerSerializer
from apps.base.reports.excel.download_jobs_exce import download_jobs_excel

class JobsViewSet(viewsets.GenericViewSet):
    model = None
    serializer_class = JobSqlServerSerializer
    queryset = None


    @action(methods=['POST'], detail=False, url_path="send-jobs-folder")
    def send_jobs_folder(self, request, *args, **kwargs):
        try:
            service = SQLServerService()
            data = service.get_jobs()
            return download_jobs_excel(data)
            # return FormatResponse.successful("Validación exitosa", data)
        except Exception as e:
            return FormatResponse.failed(e)