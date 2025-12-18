"""
Tests para operaciones de fecha y hora en A2E
"""

import pytest
import asyncio
from datetime import datetime
import pytz
from workflow_executor import WorkflowExecutor


class TestGetCurrentDateTime:
    """Tests para GetCurrentDateTime"""
    
    @pytest.mark.asyncio
    async def test_get_current_datetime_iso8601(self):
        """Test obtener fecha/hora actual en formato ISO 8601"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "get-now", "operation": {"GetCurrentDateTime": {"timezone": "UTC", "format": "iso8601", "outputPath": "/workflow/current_time"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "get-now"}}'
        
        executor = WorkflowExecutor()
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        assert "get-now" in results
        result = executor._get_data("/workflow/current_time")
        assert result is not None
        assert isinstance(result, str)
        # Verificar que es formato ISO 8601 válido
        datetime.fromisoformat(result.replace('Z', '+00:00'))
    
    @pytest.mark.asyncio
    async def test_get_current_datetime_timestamp(self):
        """Test obtener fecha/hora actual como timestamp"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "get-now", "operation": {"GetCurrentDateTime": {"format": "timestamp", "outputPath": "/workflow/current_timestamp"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "get-now"}}'
        
        executor = WorkflowExecutor()
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/current_timestamp")
        assert result is not None
        assert isinstance(result, (int, float))
        # Verificar que es un timestamp razonable (cerca de ahora)
        now = datetime.now().timestamp()
        assert abs(result - now) < 10  # Diferencia menor a 10 segundos
    
    @pytest.mark.asyncio
    async def test_get_current_datetime_custom_format(self):
        """Test obtener fecha/hora actual con formato personalizado"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "get-now", "operation": {"GetCurrentDateTime": {"format": "custom", "formatString": "%Y-%m-%d %H:%M:%S", "outputPath": "/workflow/current_time_formatted"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "get-now"}}'
        
        executor = WorkflowExecutor()
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/current_time_formatted")
        assert result is not None
        assert isinstance(result, str)
        # Verificar formato YYYY-MM-DD HH:MM:SS
        datetime.strptime(result, "%Y-%m-%d %H:%M:%S")
    
    @pytest.mark.asyncio
    async def test_get_current_datetime_timezone(self):
        """Test obtener fecha/hora actual en zona horaria específica"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "get-now", "operation": {"GetCurrentDateTime": {"timezone": "Europe/Madrid", "format": "iso8601", "outputPath": "/workflow/current_time"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "get-now"}}'
        
        executor = WorkflowExecutor()
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/current_time")
        assert result is not None
        # Verificar que contiene información de timezone
        dt = datetime.fromisoformat(result.replace('Z', '+00:00'))
        assert dt.tzinfo is not None


class TestConvertTimezone:
    """Tests para ConvertTimezone"""
    
    @pytest.mark.asyncio
    async def test_convert_timezone_iso8601(self):
        """Test convertir zona horaria desde ISO 8601"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "set-utc", "operation": {"GetCurrentDateTime": {"timezone": "UTC", "format": "iso8601", "outputPath": "/workflow/utc_time"}}}, {"id": "convert", "operation": {"ConvertTimezone": {"inputPath": "/workflow/utc_time", "fromTimezone": "UTC", "toTimezone": "Europe/Madrid", "format": "iso8601", "outputPath": "/workflow/madrid_time"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "set-utc"}}'
        
        executor = WorkflowExecutor()
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        utc_time = executor._get_data("/workflow/utc_time")
        madrid_time = executor._get_data("/workflow/madrid_time")
        
        assert utc_time is not None
        assert madrid_time is not None
        
        # Verificar que son diferentes (Madrid está adelantado respecto a UTC)
        utc_dt = datetime.fromisoformat(utc_time.replace('Z', '+00:00'))
        madrid_dt = datetime.fromisoformat(madrid_time.replace('Z', '+00:00'))
        
        # Madrid debería estar adelantado (o igual en verano)
        assert madrid_dt >= utc_dt
    
    @pytest.mark.asyncio
    async def test_convert_timezone_timestamp(self):
        """Test convertir zona horaria desde timestamp"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "set-timestamp", "operation": {"GetCurrentDateTime": {"format": "timestamp", "outputPath": "/workflow/timestamp"}}}, {"id": "convert", "operation": {"ConvertTimezone": {"inputPath": "/workflow/timestamp", "toTimezone": "America/New_York", "format": "iso8601", "outputPath": "/workflow/ny_time"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "set-timestamp"}}'
        
        executor = WorkflowExecutor()
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/ny_time")
        assert result is not None
        assert isinstance(result, str)
        # Verificar que es formato ISO 8601 válido
        datetime.fromisoformat(result.replace('Z', '+00:00'))


class TestDateCalculation:
    """Tests para DateCalculation"""
    
    @pytest.mark.asyncio
    async def test_date_calculation_add_days(self):
        """Test sumar días a una fecha"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "get-now", "operation": {"GetCurrentDateTime": {"timezone": "UTC", "format": "iso8601", "outputPath": "/workflow/now"}}}, {"id": "add-days", "operation": {"DateCalculation": {"inputPath": "/workflow/now", "operation": "add", "days": 7, "format": "iso8601", "outputPath": "/workflow/next_week"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "get-now"}}'
        
        executor = WorkflowExecutor()
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        now = executor._get_data("/workflow/now")
        next_week = executor._get_data("/workflow/next_week")
        
        assert now is not None
        assert next_week is not None
        
        now_dt = datetime.fromisoformat(now.replace('Z', '+00:00'))
        next_week_dt = datetime.fromisoformat(next_week.replace('Z', '+00:00'))
        
        # Verificar que next_week es 7 días después
        diff = (next_week_dt - now_dt).total_seconds()
        assert abs(diff - (7 * 24 * 3600)) < 60  # Tolerancia de 1 minuto
    
    @pytest.mark.asyncio
    async def test_date_calculation_subtract_hours(self):
        """Test restar horas a una fecha"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "get-now", "operation": {"GetCurrentDateTime": {"timezone": "UTC", "format": "iso8601", "outputPath": "/workflow/now"}}}, {"id": "subtract-hours", "operation": {"DateCalculation": {"inputPath": "/workflow/now", "operation": "subtract", "hours": 24, "format": "iso8601", "outputPath": "/workflow/yesterday"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "get-now"}}'
        
        executor = WorkflowExecutor()
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        now = executor._get_data("/workflow/now")
        yesterday = executor._get_data("/workflow/yesterday")
        
        assert now is not None
        assert yesterday is not None
        
        now_dt = datetime.fromisoformat(now.replace('Z', '+00:00'))
        yesterday_dt = datetime.fromisoformat(yesterday.replace('Z', '+00:00'))
        
        # Verificar que yesterday es 24 horas antes
        diff = (now_dt - yesterday_dt).total_seconds()
        assert abs(diff - (24 * 3600)) < 60  # Tolerancia de 1 minuto
    
    @pytest.mark.asyncio
    async def test_date_calculation_complex(self):
        """Test cálculo complejo con múltiples unidades"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "get-now", "operation": {"GetCurrentDateTime": {"timezone": "UTC", "format": "iso8601", "outputPath": "/workflow/now"}}}, {"id": "add-complex", "operation": {"DateCalculation": {"inputPath": "/workflow/now", "operation": "add", "days": 30, "hours": 12, "minutes": 30, "format": "iso8601", "outputPath": "/workflow/future"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "get-now"}}'
        
        executor = WorkflowExecutor()
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        now = executor._get_data("/workflow/now")
        future = executor._get_data("/workflow/future")
        
        assert now is not None
        assert future is not None
        
        now_dt = datetime.fromisoformat(now.replace('Z', '+00:00'))
        future_dt = datetime.fromisoformat(future.replace('Z', '+00:00'))
        
        # Verificar que future es después de now
        assert future_dt > now_dt
        
        # Verificar diferencia aproximada (30 días, 12 horas, 30 minutos)
        expected_diff = (30 * 24 * 3600) + (12 * 3600) + (30 * 60)
        actual_diff = (future_dt - now_dt).total_seconds()
        assert abs(actual_diff - expected_diff) < 60  # Tolerancia de 1 minuto
    
    @pytest.mark.asyncio
    async def test_date_calculation_custom_format(self):
        """Test cálculo con formato personalizado"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "get-now", "operation": {"GetCurrentDateTime": {"timezone": "UTC", "format": "iso8601", "outputPath": "/workflow/now"}}}, {"id": "add-days", "operation": {"DateCalculation": {"inputPath": "/workflow/now", "operation": "add", "days": 1, "format": "custom", "formatString": "%Y-%m-%d", "outputPath": "/workflow/tomorrow"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "get-now"}}'
        
        executor = WorkflowExecutor()
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/tomorrow")
        assert result is not None
        assert isinstance(result, str)
        # Verificar formato YYYY-MM-DD
        datetime.strptime(result, "%Y-%m-%d")


class TestDateTimeIntegration:
    """Tests de integración para operaciones de fecha/hora"""
    
    @pytest.mark.asyncio
    async def test_combined_workflow(self):
        """Test workflow combinado con múltiples operaciones de fecha/hora"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "get-utc", "operation": {"GetCurrentDateTime": {"timezone": "UTC", "format": "iso8601", "outputPath": "/workflow/utc_now"}}}, {"id": "convert", "operation": {"ConvertTimezone": {"inputPath": "/workflow/utc_now", "toTimezone": "Europe/Madrid", "format": "iso8601", "outputPath": "/workflow/madrid_now"}}}, {"id": "calc", "operation": {"DateCalculation": {"inputPath": "/workflow/madrid_now", "operation": "add", "days": 7, "format": "iso8601", "outputPath": "/workflow/madrid_next_week"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "get-utc"}}'
        
        executor = WorkflowExecutor()
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        assert "get-utc" in results
        assert "convert" in results
        assert "calc" in results
        
        utc_now = executor._get_data("/workflow/utc_now")
        madrid_now = executor._get_data("/workflow/madrid_now")
        madrid_next_week = executor._get_data("/workflow/madrid_next_week")
        
        assert utc_now is not None
        assert madrid_now is not None
        assert madrid_next_week is not None
        
        # Verificar que todas son fechas válidas
        datetime.fromisoformat(utc_now.replace('Z', '+00:00'))
        datetime.fromisoformat(madrid_now.replace('Z', '+00:00'))
        datetime.fromisoformat(madrid_next_week.replace('Z', '+00:00'))

