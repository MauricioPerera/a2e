"""
Tests para operaciones de utilidad en A2E
"""

import pytest
import asyncio
from workflow_executor import WorkflowExecutor


class TestFormatText:
    """Tests para FormatText"""
    
    @pytest.mark.asyncio
    async def test_format_text_upper(self):
        """Test formatear texto a mayúsculas"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "set-text", "operation": {"GetCurrentDateTime": {"format": "custom", "formatString": "hello world", "outputPath": "/workflow/text"}}}, {"id": "format", "operation": {"FormatText": {"inputPath": "/workflow/text", "format": "upper", "outputPath": "/workflow/formatted"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "set-text"}}'
        
        executor = WorkflowExecutor()
        executor._set_data("/workflow/text", "hello world")
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/formatted")
        assert result == "HELLO WORLD"
    
    @pytest.mark.asyncio
    async def test_format_text_template(self):
        """Test formatear texto con plantilla"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "format", "operation": {"FormatText": {"inputPath": "/workflow/data", "format": "template", "template": "Hello {name}, you have {points} points", "outputPath": "/workflow/formatted"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "format"}}'
        
        executor = WorkflowExecutor()
        executor._set_data("/workflow/data", {"name": "Alice", "points": 100})
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/formatted")
        assert result == "Hello Alice, you have 100 points"
    
    @pytest.mark.asyncio
    async def test_format_text_replace(self):
        """Test reemplazar texto"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "format", "operation": {"FormatText": {"inputPath": "/workflow/text", "format": "replace", "replacements": {"old": "new", "test": "example"}, "outputPath": "/workflow/formatted"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "format"}}'
        
        executor = WorkflowExecutor()
        executor._set_data("/workflow/text", "old test string")
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/formatted")
        assert result == "new example string"


class TestExtractText:
    """Tests para ExtractText"""
    
    @pytest.mark.asyncio
    async def test_extract_text_single(self):
        """Test extraer primera coincidencia"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "extract", "operation": {"ExtractText": {"inputPath": "/workflow/text", "pattern": "[0-9]+", "extractAll": false, "outputPath": "/workflow/extracted"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "extract"}}'
        
        executor = WorkflowExecutor()
        executor._set_data("/workflow/text", "The price is 123 dollars")
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/extracted")
        assert result == "123"
    
    @pytest.mark.asyncio
    async def test_extract_text_all(self):
        """Test extraer todas las coincidencias"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "extract", "operation": {"ExtractText": {"inputPath": "/workflow/text", "pattern": "[0-9]+", "extractAll": true, "outputPath": "/workflow/extracted"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "extract"}}'
        
        executor = WorkflowExecutor()
        executor._set_data("/workflow/text", "Prices: 100, 200, 300")
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/extracted")
        assert isinstance(result, list)
        assert "100" in result
        assert "200" in result
        assert "300" in result


class TestValidateData:
    """Tests para ValidateData"""
    
    @pytest.mark.asyncio
    async def test_validate_email(self):
        """Test validar email"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "validate", "operation": {"ValidateData": {"inputPath": "/workflow/email", "validationType": "email", "outputPath": "/workflow/result"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "validate"}}'
        
        executor = WorkflowExecutor()
        executor._set_data("/workflow/email", "user@example.com")
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/result")
        assert result["valid"] is True
        
        # Test email inválido
        executor._set_data("/workflow/email", "invalid-email")
        results = await executor.execute()
        result = executor._get_data("/workflow/result")
        assert result["valid"] is False
    
    @pytest.mark.asyncio
    async def test_validate_url(self):
        """Test validar URL"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "validate", "operation": {"ValidateData": {"inputPath": "/workflow/url", "validationType": "url", "outputPath": "/workflow/result"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "validate"}}'
        
        executor = WorkflowExecutor()
        executor._set_data("/workflow/url", "https://example.com")
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/result")
        assert result["valid"] is True
    
    @pytest.mark.asyncio
    async def test_validate_number(self):
        """Test validar número"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "validate", "operation": {"ValidateData": {"inputPath": "/workflow/number", "validationType": "number", "outputPath": "/workflow/result"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "validate"}}'
        
        executor = WorkflowExecutor()
        executor._set_data("/workflow/number", "123.45")
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/result")
        assert result["valid"] is True


class TestCalculate:
    """Tests para Calculate"""
    
    @pytest.mark.asyncio
    async def test_calculate_add(self):
        """Test sumar números"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "calc", "operation": {"Calculate": {"inputPath": "/workflow/number", "operation": "add", "operand": 10, "outputPath": "/workflow/result"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "calc"}}'
        
        executor = WorkflowExecutor()
        executor._set_data("/workflow/number", 5)
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/result")
        assert result == 15
    
    @pytest.mark.asyncio
    async def test_calculate_multiply(self):
        """Test multiplicar números"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "calc", "operation": {"Calculate": {"inputPath": "/workflow/number", "operation": "multiply", "operand": 3, "outputPath": "/workflow/result"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "calc"}}'
        
        executor = WorkflowExecutor()
        executor._set_data("/workflow/number", 5)
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/result")
        assert result == 15
    
    @pytest.mark.asyncio
    async def test_calculate_round(self):
        """Test redondear número"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "calc", "operation": {"Calculate": {"inputPath": "/workflow/number", "operation": "round", "precision": 2, "outputPath": "/workflow/result"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "calc"}}'
        
        executor = WorkflowExecutor()
        executor._set_data("/workflow/number", 3.14159)
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/result")
        assert result == 3.14
    
    @pytest.mark.asyncio
    async def test_calculate_sum(self):
        """Test sumar lista de números"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "calc", "operation": {"Calculate": {"inputPath": "/workflow/numbers", "operation": "sum", "outputPath": "/workflow/result"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "calc"}}'
        
        executor = WorkflowExecutor()
        executor._set_data("/workflow/numbers", [1, 2, 3, 4, 5])
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/result")
        assert result == 15
    
    @pytest.mark.asyncio
    async def test_calculate_average(self):
        """Test calcular promedio"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "calc", "operation": {"Calculate": {"inputPath": "/workflow/numbers", "operation": "average", "outputPath": "/workflow/result"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "calc"}}'
        
        executor = WorkflowExecutor()
        executor._set_data("/workflow/numbers", [10, 20, 30])
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/result")
        assert result == 20.0


class TestEncodeDecode:
    """Tests para EncodeDecode"""
    
    @pytest.mark.asyncio
    async def test_encode_base64(self):
        """Test codificar Base64"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "encode", "operation": {"EncodeDecode": {"inputPath": "/workflow/text", "operation": "encode", "encoding": "base64", "outputPath": "/workflow/encoded"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "encode"}}'
        
        executor = WorkflowExecutor()
        executor._set_data("/workflow/text", "Hello World")
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/encoded")
        assert result == "SGVsbG8gV29ybGQ="
    
    @pytest.mark.asyncio
    async def test_decode_base64(self):
        """Test decodificar Base64"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "decode", "operation": {"EncodeDecode": {"inputPath": "/workflow/encoded", "operation": "decode", "encoding": "base64", "outputPath": "/workflow/decoded"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "decode"}}'
        
        executor = WorkflowExecutor()
        executor._set_data("/workflow/encoded", "SGVsbG8gV29ybGQ=")
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/decoded")
        assert result == "Hello World"
    
    @pytest.mark.asyncio
    async def test_encode_url(self):
        """Test codificar URL"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "encode", "operation": {"EncodeDecode": {"inputPath": "/workflow/text", "operation": "encode", "encoding": "url", "outputPath": "/workflow/encoded"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "encode"}}'
        
        executor = WorkflowExecutor()
        executor._set_data("/workflow/text", "hello world")
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/encoded")
        assert result == "hello%20world"
    
    @pytest.mark.asyncio
    async def test_encode_html(self):
        """Test codificar HTML"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "encode", "operation": {"EncodeDecode": {"inputPath": "/workflow/text", "operation": "encode", "encoding": "html", "outputPath": "/workflow/encoded"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "encode"}}'
        
        executor = WorkflowExecutor()
        executor._set_data("/workflow/text", "<script>alert('test')</script>")
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        result = executor._get_data("/workflow/encoded")
        assert "&lt;" in result
        assert "&gt;" in result


class TestUtilityIntegration:
    """Tests de integración para operaciones de utilidad"""
    
    @pytest.mark.asyncio
    async def test_combined_workflow(self):
        """Test workflow combinado con múltiples operaciones de utilidad"""
        workflow_jsonl = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "set-data", "operation": {"GetCurrentDateTime": {"format": "custom", "formatString": "user@example.com", "outputPath": "/workflow/email"}}}, {"id": "validate", "operation": {"ValidateData": {"inputPath": "/workflow/email", "validationType": "email", "outputPath": "/workflow/validated"}}}, {"id": "format", "operation": {"FormatText": {"inputPath": "/workflow/email", "format": "upper", "outputPath": "/workflow/formatted"}}}, {"id": "extract", "operation": {"ExtractText": {"inputPath": "/workflow/email", "pattern": "@([a-zA-Z0-9.]+)", "extractAll": false, "outputPath": "/workflow/domain"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "set-data"}}'
        
        executor = WorkflowExecutor()
        executor._set_data("/workflow/email", "user@example.com")
        executor.load_workflow(workflow_jsonl)
        results = await executor.execute()
        
        validated = executor._get_data("/workflow/validated")
        formatted = executor._get_data("/workflow/formatted")
        domain = executor._get_data("/workflow/domain")
        
        assert validated["valid"] is True
        assert formatted == "USER@EXAMPLE.COM"
        assert domain is not None

