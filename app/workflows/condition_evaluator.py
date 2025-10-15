# app/workflows/condition_evaluator.py

import re
from typing import Dict, Any, Union, List
import logging

logger = logging.getLogger(__name__)

class ConditionEvaluator:
    """
    Evaluador SEGURO de condiciones para workflows.
    
    ⚠️ NO USA eval() - Implementa su propio parser
    ✅ Solo permite operadores seguros
    ✅ Previene inyección de código
    ✅ Valida sintaxis antes de evaluar
    
    Sintaxis soportada:
    - Comparaciones: ==, !=, >, <, >=, <=
    - Pertenencia: in, not in
    - Strings: contains, startswith, endswith
    - Lógicos: and, or, not
    - Variables: {{variable_name}}
    - Literals: strings, números, booleans, null, arrays
    
    Ejemplos:
    - "{{interest}} == true"
    - "{{age}} >= 18"
    - "{{status}} in ['active', 'pending']"
    - "{{name}} contains 'John' and {{age}} > 21"
    """
    
    # Operadores permitidos (en orden de precedencia)
    COMPARISON_OPERATORS = {
        '==': lambda a, b: a == b,
        '!=': lambda a, b: a != b,
        '>=': lambda a, b: a >= b,
        '<=': lambda a, b: a <= b,
        '>': lambda a, b: a > b,
        '<': lambda a, b: a < b,
    }
    
    STRING_OPERATORS = {
        'contains': lambda a, b: b in str(a),
        'startswith': lambda a, b: str(a).startswith(str(b)),
        'endswith': lambda a, b: str(a).endswith(str(b)),
        'matches': lambda a, b: bool(re.match(str(b), str(a)))
    }
    
    MEMBERSHIP_OPERATORS = {
        'in': lambda a, b: a in b,
        'not in': lambda a, b: a not in b
    }
    
    LOGICAL_OPERATORS = ['and', 'or', 'not']
    
    def __init__(self):
        # Combinar todos los operadores
        self.all_operators = {
            **self.COMPARISON_OPERATORS,
            **self.STRING_OPERATORS,
            **self.MEMBERSHIP_OPERATORS
        }
    
    def evaluate(self, condition: str, context: Dict[str, Any]) -> bool:
        """
        Evaluar condición de forma segura.
        
        Args:
            condition: Expresión condicional (ej: "{{age}} >= 18")
            context: Contexto con variables disponibles
            
        Returns:
            Resultado booleano de la evaluación
            
        Raises:
            ValueError: Si la sintaxis es inválida
            
        Examples:
            >>> evaluator = ConditionEvaluator()
            >>> evaluator.evaluate("{{age}} >= 18", {"age": 25})
            True
            >>> evaluator.evaluate("{{status}} in ['active', 'pending']", {"status": "active"})
            True
        """
        try:
            # Normalizar espacios
            condition = condition.strip()
            
            if not condition:
                raise ValueError("Empty condition")
            
            # Log para debugging
            logger.debug(f"Evaluating condition: {condition}")
            logger.debug(f"Context: {context}")
            
            # Evaluar condición (con soporte para lógicos)
            result = self._evaluate_expression(condition, context)
            
            # Forzar a boolean
            if not isinstance(result, bool):
                result = bool(result)
            
            logger.debug(f"Condition result: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {e}")
            raise ValueError(f"Invalid condition: {str(e)}")
    
    def _evaluate_expression(self, expression: str, context: Dict[str, Any]) -> bool:
        """
        Evaluar expresión completa (puede contener and/or).
        """
        expression = expression.strip()
        
        # Manejar operadores lógicos (precedencia: not > and > or)
        
        # Paso 1: Dividir por 'or' (menor precedencia)
        if ' or ' in expression:
            parts = self._split_by_operator(expression, ' or ')
            results = [self._evaluate_expression(part, context) for part in parts]
            return any(results)
        
        # Paso 2: Dividir por 'and'
        if ' and ' in expression:
            parts = self._split_by_operator(expression, ' and ')
            results = [self._evaluate_expression(part, context) for part in parts]
            return all(results)
        
        # Paso 3: Manejar 'not'
        if expression.startswith('not '):
            inner = expression[4:].strip()
            return not self._evaluate_expression(inner, context)
        
        # Paso 4: Evaluar comparación simple
        return self._evaluate_comparison(expression, context)
    
    def _split_by_operator(self, expression: str, operator: str) -> List[str]:
        """
        Dividir expresión por operador, respetando paréntesis y strings.
        """
        parts = []
        current = []
        paren_depth = 0
        in_string = False
        string_char = None
        i = 0
        
        while i < len(expression):
            char = expression[i]
            
            # Manejar strings
            if char in ['"', "'"]:
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None
                current.append(char)
                i += 1
                continue
            
            # Manejar paréntesis
            if not in_string:
                if char == '(':
                    paren_depth += 1
                elif char == ')':
                    paren_depth -= 1
            
            # Verificar si encontramos el operador
            if not in_string and paren_depth == 0:
                if expression[i:i+len(operator)] == operator:
                    # Encontrado operador, guardar parte actual
                    parts.append(''.join(current).strip())
                    current = []
                    i += len(operator)
                    continue
            
            current.append(char)
            i += 1
        
        # Agregar última parte
        if current:
            parts.append(''.join(current).strip())
        
        return parts
    
    def _evaluate_comparison(self, comparison: str, context: Dict[str, Any]) -> bool:
        """
        Evaluar comparación simple (sin and/or).
        """
        comparison = comparison.strip()
        
        # Remover paréntesis externos si existen
        if comparison.startswith('(') and comparison.endswith(')'):
            comparison = comparison[1:-1].strip()
        
        # Buscar operador (probar en orden de longitud para evitar conflictos)
        for op in sorted(self.all_operators.keys(), key=len, reverse=True):
            if f' {op} ' in comparison:
                parts = comparison.split(f' {op} ', 1)
                if len(parts) == 2:
                    left = self._resolve_value(parts[0].strip(), context)
                    right = self._resolve_value(parts[1].strip(), context)
                    
                    # Ejecutar operador
                    op_func = self.all_operators[op]
                    
                    try:
                        result = op_func(left, right)
                        logger.debug(f"  {left} {op} {right} = {result}")
                        return result
                    except Exception as e:
                        logger.error(f"Error applying operator '{op}': {e}")
                        raise ValueError(f"Cannot apply '{op}' to {type(left).__name__} and {type(right).__name__}")
        
        # Si no hay operador, evaluar como valor único (debe ser boolean)
        value = self._resolve_value(comparison, context)
        
        if not isinstance(value, bool):
            raise ValueError(f"Expression '{comparison}' must be a boolean or comparison")
        
        return value
    
    def _resolve_value(self, value_str: str, context: Dict[str, Any]) -> Any:
        """
        Resolver valor (variable o literal).
        
        Soporta:
        - Variables: {{variable_name}}
        - Strings: "text" o 'text'
        - Numbers: 42, 3.14
        - Booleans: true, false
        - Null: null, none
        - Arrays: [1, 2, 3], ["a", "b"]
        """
        value_str = value_str.strip()
        
        # === VARIABLES === #
        if value_str.startswith('{{') and value_str.endswith('}}'):
            var_name = value_str[2:-2].strip()
            
            # Soportar navegación de objetos: {{user.age}}
            if '.' in var_name:
                return self._resolve_nested_variable(var_name, context)
            
            # Variable simple
            if var_name in context:
                return context[var_name]
            else:
                logger.warning(f"Variable '{var_name}' not found in context, defaulting to None")
                return None
        
        # === STRINGS === #
        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            return value_str[1:-1]
        
        # === BOOLEANS === #
        if value_str.lower() == 'true':
            return True
        elif value_str.lower() == 'false':
            return False
        
        # === NULL === #
        if value_str.lower() in ['null', 'none']:
            return None
        
        # === NUMBERS === #
        try:
            if '.' in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except ValueError:
            pass
        
        # === ARRAYS === #
        if value_str.startswith('[') and value_str.endswith(']'):
            return self._parse_array(value_str, context)
        
        # === DEFAULT: String literal sin comillas === #
        # Esto permite escribir: {{status}} == active (sin comillas en active)
        return value_str
    
    def _resolve_nested_variable(self, var_path: str, context: Dict[str, Any]) -> Any:
        """
        Resolver variable anidada (ej: user.profile.age).
        """
        parts = var_path.split('.')
        value = context
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                logger.warning(f"Cannot resolve '{part}' in path '{var_path}'")
                return None
            
            if value is None:
                return None
        
        return value
    
    def _parse_array(self, array_str: str, context: Dict[str, Any]) -> List[Any]:
        """
        Parsear array literal: [1, 2, 3] o ["a", "b", "c"].
        """
        # Remover corchetes
        content = array_str[1:-1].strip()
        
        if not content:
            return []
        
        # Dividir por comas (respetando strings)
        items = []
        current = []
        in_string = False
        string_char = None
        
        for char in content:
            if char in ['"', "'"]:
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None
            
            if char == ',' and not in_string:
                items.append(''.join(current).strip())
                current = []
            else:
                current.append(char)
        
        # Agregar último item
        if current:
            items.append(''.join(current).strip())
        
        # Resolver cada item
        return [self._resolve_value(item, context) for item in items]
    
    def validate_syntax(self, condition: str) -> Dict[str, Any]:
        """
        Validar sintaxis de una condición sin evaluarla.
        
        Returns:
            Dict con {valid: bool, errors: List[str], warnings: List[str]}
        """
        errors = []
        warnings = []
        
        try:
            # Verificar que no esté vacía
            if not condition or not condition.strip():
                errors.append("Condition is empty")
                return {"valid": False, "errors": errors, "warnings": warnings}
            
            # Verificar balance de paréntesis
            if condition.count('(') != condition.count(')'):
                errors.append("Unbalanced parentheses")
            
            # Verificar balance de comillas
            if condition.count('"') % 2 != 0:
                errors.append("Unbalanced double quotes")
            if condition.count("'") % 2 != 0:
                errors.append("Unbalanced single quotes")
            
            # Verificar que tenga al menos un operador (a menos que sea variable booleana sola)
            has_operator = any(op in condition for op in self.all_operators.keys())
            has_logical = any(op in condition for op in self.LOGICAL_OPERATORS)
            
            if not has_operator and not has_logical:
                # Debe ser variable booleana
                if not (condition.strip().startswith('{{') and condition.strip().endswith('}}')):
                    warnings.append("Condition has no operator, assuming boolean variable")
            
            # Verificar sintaxis de variables
            var_pattern = r'\{\{([^}]+)\}\}'
            variables = re.findall(var_pattern, condition)
            
            for var in variables:
                if not var.strip():
                    errors.append("Empty variable name: {{}}")
                elif not re.match(r'^[a-zA-Z_][a-zA-Z0-9_\.]*$', var.strip()):
                    errors.append(f"Invalid variable name: {var}")
            
            # Si no hay errores, intentar parsear
            if not errors:
                try:
                    # Dry-run con contexto vacío
                    self.evaluate(condition, {})
                except Exception as e:
                    # Es esperado que falle si faltan variables
                    # Solo capturamos errores de sintaxis
                    error_msg = str(e).lower()
                    if 'syntax' in error_msg or 'invalid' in error_msg:
                        errors.append(str(e))
            
        except Exception as e:
            errors.append(f"Unexpected validation error: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def get_variables_used(self, condition: str) -> List[str]:
        """
        Extraer todas las variables usadas en una condición.
        
        Returns:
            Lista de nombres de variables (sin {{}})
        """
        var_pattern = r'\{\{([^}]+)\}\}'
        variables = re.findall(var_pattern, condition)
        return [var.strip() for var in variables]


# === HELPER FUNCTIONS === #

def evaluate_condition(condition: str, context: Dict[str, Any]) -> bool:
    """
    Función de conveniencia para evaluar condición.
    
    Args:
        condition: Expresión condicional
        context: Contexto con variables
        
    Returns:
        Resultado booleano
    """
    evaluator = ConditionEvaluator()
    return evaluator.evaluate(condition, context)


def validate_condition(condition: str) -> Dict[str, Any]:
    """
    Función de conveniencia para validar sintaxis.
    
    Args:
        condition: Expresión condicional
        
    Returns:
        Dict con resultado de validación
    """
    evaluator = ConditionEvaluator()
    return evaluator.validate_syntax(condition)


# === TESTS (para verificar funcionalidad) === #

if __name__ == "__main__":
    # Tests básicos
    evaluator = ConditionEvaluator()
    
    test_cases = [
        # Comparaciones simples
        ("{{age}} >= 18", {"age": 25}, True),
        ("{{age}} >= 18", {"age": 15}, False),
        ("{{status}} == 'active'", {"status": "active"}, True),
        ("{{status}} != 'inactive'", {"status": "active"}, True),
        
        # Membership
        ("{{role}} in ['admin', 'moderator']", {"role": "admin"}, True),
        ("{{role}} not in ['admin', 'moderator']", {"role": "user"}, True),
        
        # String operations
        ("{{name}} contains 'John'", {"name": "John Doe"}, True),
        ("{{email}} endswith '@gmail.com'", {"email": "user@gmail.com"}, True),
        
        # Logical operators
        ("{{age}} >= 18 and {{verified}} == true", {"age": 25, "verified": True}, True),
        ("{{age}} < 18 or {{parent_consent}} == true", {"age": 15, "parent_consent": True}, True),
        ("not {{banned}} == true", {"banned": False}, True),
        
        # Complex expressions
        ("({{age}} >= 18 and {{country}} == 'US') or {{verified}} == true", 
         {"age": 25, "country": "US", "verified": False}, True),
        
        # Nested variables
        ("{{user.age}} >= 18", {"user": {"age": 25}}, True),
    ]
    
    print("Running tests...")
    passed = 0
    failed = 0
    
    for condition, context, expected in test_cases:
        try:
            result = evaluator.evaluate(condition, context)
            if result == expected:
                print(f"✅ PASS: {condition}")
                passed += 1
            else:
                print(f"❌ FAIL: {condition} (expected {expected}, got {result})")
                failed += 1
        except Exception as e:
            print(f"❌ ERROR: {condition} - {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
