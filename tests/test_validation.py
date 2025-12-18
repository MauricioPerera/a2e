"""
Tests para Validación de Workflows
"""

import pytest
from validation.workflow_validator import WorkflowValidator, ValidationLevel, ValidationError


@pytest.fixture
def validator():
    """Fixture para crear validador básico"""
    return WorkflowValidator(level=ValidationLevel.MODERATE)


def test_validate_structure_missing_id(validator):
    """Test validación de estructura: operación sin ID"""
    workflow = """
{"operationUpdate": {"workflowId": "test", "operations": [
  {"operation": {"Wait": {"duration": 10}}}
]}}
"""
    
    is_valid, errors = validator.validate_workflow(workflow)
    assert is_valid is False
    assert any("missing required 'id' field" in e.message for e in errors)


def test_validate_structure_duplicate_id(validator):
    """Test validación de estructura: IDs duplicados"""
    workflow = """
{"operationUpdate": {"workflowId": "test", "operations": [
  {"id": "op1", "operation": {"Wait": {"duration": 10}}},
  {"id": "op1", "operation": {"Wait": {"duration": 10}}}
]}}
"""
    
    is_valid, errors = validator.validate_workflow(workflow)
    assert is_valid is False
    assert any("Duplicate operation ID" in e.message for e in errors)


def test_validate_dependencies_nonexistent(validator):
    """Test validación de dependencias: referencia a operación inexistente"""
    workflow = """
{"operationUpdate": {"workflowId": "test", "operations": [
  {"id": "filter", "operation": {
    "FilterData": {
      "inputPath": "/workflow/nonexistent",
      "conditions": [],
      "outputPath": "/workflow/result"
    }
  }}
]}}
"""
    
    is_valid, errors = validator.validate_workflow(workflow)
    assert is_valid is False
    assert any("references non-existent operation" in e.message for e in errors)


def test_validate_data_types_incompatible(validator):
    """Test validación de tipos: operación que requiere array pero recibe otro tipo"""
    workflow = """
{"operationUpdate": {"workflowId": "test", "operations": [
  {"id": "transform", "operation": {
    "TransformData": {
      "inputPath": "/workflow/data",
      "transform": "reduce",
      "outputPath": "/workflow/reduced"
    }
  }},
  {"id": "filter", "operation": {
    "FilterData": {
      "inputPath": "/workflow/reduced",
      "conditions": [],
      "outputPath": "/workflow/result"
    }
  }}
]}}
"""
    
    is_valid, errors = validator.validate_workflow(workflow)
    # FilterData requiere array pero reduce produce value
    assert any("requires array input" in e.message for e in errors)


def test_validate_conditional_references(validator):
    """Test validación de referencias en operaciones condicionales"""
    workflow = """
{"operationUpdate": {"workflowId": "test", "operations": [
  {"id": "check", "operation": {
    "Conditional": {
      "condition": {"path": "/data/value", "operator": ">"},
      "ifTrue": "nonexistent-true",
      "ifFalse": "nonexistent-false"
    }
  }}
]}}
"""
    
    is_valid, errors = validator.validate_workflow(workflow)
    assert is_valid is False
    assert any("references non-existent operation" in e.message for e in errors)


def test_validation_report(validator):
    """Test generación de reporte de validación"""
    workflow = """
{"operationUpdate": {"workflowId": "test", "operations": [
  {"id": "op1", "operation": {"Wait": {"duration": 10}}}
]}}
"""
    
    report = validator.get_validation_report(workflow)
    
    assert "valid" in report
    assert "errors" in report
    assert "warnings" in report
    assert "issues" in report
    assert "summary" in report


def test_validation_levels(validator):
    """Test diferentes niveles de validación"""
    workflow = """
{"operationUpdate": {"workflowId": "test", "operations": [
  {"id": "op1", "operation": {"Wait": {"duration": 10}}}
]}}
"""
    
    # STRICT: Incluye warnings
    validator.level = ValidationLevel.STRICT
    is_valid_strict, errors_strict = validator.validate_workflow(workflow)
    
    # MODERATE: Solo errores críticos
    validator.level = ValidationLevel.MODERATE
    is_valid_moderate, errors_moderate = validator.validate_workflow(workflow)
    
    # LENIENT: Solo errores seguros
    validator.level = ValidationLevel.LENIENT
    is_valid_lenient, errors_lenient = validator.validate_workflow(workflow)
    
    # LENIENT debe tener menos errores que STRICT
    assert len(errors_lenient) <= len(errors_strict)

